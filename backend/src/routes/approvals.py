"""
Approval routes — Phase 5.

Endpoints:
  POST   /api/approvals/submit        — submit request + create approvals + notify Teams
  GET    /api/approvals/status/{id}    — get approval status for a request
  POST   /api/approvals/action         — approve or reject (called from Teams or UI)
"""

import json
import os
import time
import uuid
from typing import Optional

import requests as http_requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..lib.logger import log
from ..lib.sqlite import get_db

router = APIRouter()

TEAMS_WEBHOOK_URL = os.environ.get("TEAMS_WEBHOOK_URL", "")
BACKEND_PUBLIC_URL = os.environ.get("BACKEND_PUBLIC_URL", "http://localhost:8000")
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "")

# Systems routed to Jira (project access, DB access, collaboration tools)
JIRA_ROUTED_SYSTEMS = {
    "Jira", "GitHub", "Confluence",
    "Database", "Data Warehouse", "Data Platform",
    "Notebook", "BI",
}

# Systems routed to ServiceNow only (security, infra, privileged access)
# Everything NOT in JIRA_ROUTED_SYSTEMS goes to ServiceNow
# Includes: CyberArk, AWS, Cloud, Terraform, VPN, PagerDuty, CI/CD, etc.


def _query(sql: str):
    """Legacy helper using MCP server — kept for dynamic SQL that cannot be parameterized."""
    from mcp_server.sqlite_server import query_db
    result = query_db(sql)
    parsed = json.loads(result)
    if isinstance(parsed, dict) and "error" in parsed:
        raise HTTPException(status_code=400, detail=parsed["error"])
    return parsed


def _execute(sql: str) -> dict:
    """Legacy helper using MCP server — kept for dynamic SQL that cannot be parameterized."""
    from mcp_server.sqlite_server import execute_db
    result = execute_db(sql)
    parsed = json.loads(result)
    if isinstance(parsed, dict) and "error" in parsed:
        raise HTTPException(status_code=400, detail=parsed["error"])
    return parsed


def _safe_query(sql: str, params: tuple = ()):
    """Parameterized SELECT using direct sqlite3 — immune to SQL injection."""
    db = get_db()
    rows = db.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def _safe_execute(sql: str, params: tuple = ()):
    """Parameterized INSERT/UPDATE using direct sqlite3 — immune to SQL injection."""
    db = get_db()
    cursor = db.execute(sql, params)
    db.commit()
    return {"rows_affected": cursor.rowcount, "success": True}


# ── Models ───────────────────────────────────────────────────────────────────

class SubmitRequest(BaseModel):
    acf2_id: str
    designation_id: str
    final_bundle: list[dict]


class ApprovalAction(BaseModel):
    event_id: str
    action: str  # 'approved' or 'rejected'
    approver_name: Optional[str] = None
    comments: Optional[str] = None


# ── Submit Request + Create Approvals + Notify Teams ─────────────────────────

@router.post("/submit")
def submit_request(body: SubmitRequest):
    # Validate user
    user_rows = _safe_query("SELECT * FROM users WHERE acf2_id = ?", (body.acf2_id,))
    if not user_rows:
        raise HTTPException(status_code=404, detail="User not found")

    user = user_rows[0]
    manager = user.get("manager", "Unknown Manager")
    team = user.get("team", "")
    requester_name = user.get("name", body.acf2_id)

    # Get designation title
    designation_rows = _safe_query(
        "SELECT title FROM designations WHERE id = ?", (body.designation_id,)
    )
    role_title = designation_rows[0]["title"] if designation_rows else body.designation_id

    # Create access request
    request_id = str(uuid.uuid4())
    now = int(time.time())
    bundle_ids = json.dumps([item.get("id", "") for item in body.final_bundle])

    _safe_execute(
        "INSERT INTO access_requests (id, acf2_id, designation_id, final_bundle, status, created_at) "
        "VALUES (?, ?, ?, ?, 'pending_approval', ?)",
        (request_id, body.acf2_id, body.designation_id, bundle_ids, now),
    )

    # Create approval events for each item
    events_created = []
    for item in body.final_bundle:
        item_id = item.get("id", "")
        item_name = item.get("name", item_id)

        # Look up routing, fallback to manager
        routing = _safe_query(
            "SELECT * FROM approver_routing WHERE access_item = ?", (item_id,)
        )
        approver = routing[0]["approver_name"] if routing else manager

        event_id = str(uuid.uuid4())
        _safe_execute(
            "INSERT INTO approval_events "
            "(id, access_request_id, acf2_id, role, team, access_item, approver, status, submitted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
            (event_id, request_id, body.acf2_id, role_title, team, item_id, approver, now),
        )
        events_created.append({
            "event_id": event_id,
            "access_item": item_id,
            "display_name": item_name,
            "approver": approver,
        })

    # Audit log
    audit_id = str(uuid.uuid4())
    details = json.dumps({"items": len(events_created), "manager": manager})
    _safe_execute(
        "INSERT INTO audit_log (id, acf2_id, access_request_id, event_type, details, created_at) "
        "VALUES (?, ?, ?, 'request_submitted', ?, ?)",
        (audit_id, body.acf2_id, request_id, details, now),
    )

    # Send Teams notification
    teams_sent = False
    if TEAMS_WEBHOOK_URL:
        teams_sent = _send_teams_notification(
            request_id=request_id,
            requester_name=requester_name,
            acf2_id=body.acf2_id,
            role_title=role_title,
            team=team,
            manager=manager,
            items=events_created,
        )

    # Fire n8n webhook for Jira-routed items (fire-and-forget)
    if N8N_WEBHOOK_URL:
        _fire_n8n_webhook(
            request_id=request_id,
            acf2_id=body.acf2_id,
            requester_name=requester_name,
            role_title=role_title,
            team=team,
            final_bundle=body.final_bundle,
            events_created=events_created,
        )

    # Create Jira tickets for Jira-routed items via MCP server
    jira_tickets_created = _create_jira_tickets(
        request_id=request_id,
        acf2_id=body.acf2_id,
        requester_name=requester_name,
        role_title=role_title,
        events_created=events_created,
        final_bundle=body.final_bundle,
    )

    log("AGENT", f"Request submitted: {request_id} ({len(events_created)} items, teams={teams_sent}, jira={len(jira_tickets_created)})")

    return {
        "request_id": request_id,
        "status": "pending_approval",
        "events": events_created,
        "manager": manager,
        "teams_notified": teams_sent,
        "jira_tickets": jira_tickets_created,
    }


# ── My Requests (all requests for a user) ───────────────────────────────────

@router.get("/my-requests")
def get_my_requests(acf2_id: str):
    requests = _safe_query(
        "SELECT * FROM access_requests WHERE acf2_id = ? ORDER BY created_at DESC",
        (acf2_id,),
    )

    enriched = []
    for req in requests:
        # Designation title
        designation_rows = _safe_query(
            "SELECT title FROM designations WHERE id = ?",
            (req.get("designation_id", ""),),
        )
        role_title = designation_rows[0]["title"] if designation_rows else req.get("designation_id", "Unknown Role")

        # Approval events for this request
        events = _safe_query(
            "SELECT * FROM approval_events WHERE access_request_id = ? ORDER BY submitted_at ASC",
            (req["id"],),
        )

        # Enrich events with display names
        for event in events:
            item_rows = _safe_query(
                "SELECT display_name, system FROM role_access_items "
                "WHERE access_item = ? LIMIT 1",
                (event["access_item"],),
            )
            if item_rows:
                event["display_name"] = item_rows[0].get("display_name", event["access_item"])
                event["system"] = item_rows[0].get("system", "")
            else:
                event["display_name"] = event["access_item"]
                event["system"] = ""

        total = len(events)
        approved = sum(1 for e in events if e["status"] == "approved")
        rejected = sum(1 for e in events if e["status"] == "rejected")
        pending = sum(1 for e in events if e["status"] == "pending")

        if total == 0:
            overall = "pending"
        elif rejected > 0 and pending == 0:
            overall = "partially_rejected"
        elif approved == total:
            overall = "fully_approved"
        else:
            overall = "pending_approval"

        enriched.append({
            **req,
            "role_title": role_title,
            "events": events,
            "summary": {
                "total": total,
                "approved": approved,
                "rejected": rejected,
                "pending": pending,
                "overall": overall,
            },
        })

    return {"requests": enriched}


# ── Get Approval Status ──────────────────────────────────────────────────────

@router.get("/status/{request_id}")
def get_approval_status(request_id: str):
    events = _safe_query(
        "SELECT * FROM approval_events WHERE access_request_id = ? ORDER BY submitted_at ASC",
        (request_id,),
    )

    request_rows = _safe_query("SELECT * FROM access_requests WHERE id = ?", (request_id,))
    request_info = request_rows[0] if request_rows else None

    # Enrich with display names
    for event in events:
        access_item = event["access_item"]
        item_rows = _safe_query(
            "SELECT display_name, system FROM role_access_items "
            "WHERE access_item = ? LIMIT 1",
            (access_item,),
        )
        if item_rows:
            event["display_name"] = item_rows[0].get("display_name", access_item)
            event["system"] = item_rows[0].get("system", "")
        else:
            event["display_name"] = access_item
            event["system"] = ""

    total = len(events)
    approved = sum(1 for e in events if e["status"] == "approved")
    rejected = sum(1 for e in events if e["status"] == "rejected")
    pending = sum(1 for e in events if e["status"] == "pending")

    if total == 0:
        overall = "pending"
    elif rejected > 0:
        overall = "partially_rejected"
    elif approved == total:
        overall = "fully_approved"
    else:
        overall = "pending_approval"

    return {
        "request_id": request_id,
        "request_info": request_info,
        "events": events,
        "summary": {
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "pending": pending,
            "overall": overall,
        },
    }


# ── Approve / Reject Action ─────────────────────────────────────────────────

@router.post("/action")
def approval_action(body: ApprovalAction):
    if body.action not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Action must be 'approved' or 'rejected'")

    # Use a transaction to prevent race conditions in check-then-update
    db = get_db()
    try:
        # BEGIN IMMEDIATE acquires a write lock upfront, preventing concurrent updates
        db.execute("BEGIN IMMEDIATE")

        existing = db.execute(
            "SELECT * FROM approval_events WHERE id = ?", (body.event_id,)
        ).fetchall()
        if not existing:
            db.execute("ROLLBACK")
            raise HTTPException(status_code=404, detail="Approval event not found")

        event = dict(existing[0])
        if event["status"] != "pending":
            db.execute("ROLLBACK")
            raise HTTPException(status_code=400, detail="This approval has already been resolved")

        now = int(time.time())
        approver = body.approver_name or event.get("approver", "Manager")

        db.execute(
            "UPDATE approval_events SET status = ?, approver = ?, resolved_at = ? WHERE id = ?",
            (body.action, approver, now, body.event_id),
        )

        # Check if all events for this request are resolved (inside same transaction)
        request_id = event["access_request_id"]
        all_events = [
            dict(r) for r in db.execute(
                "SELECT status FROM approval_events WHERE access_request_id = ?",
                (request_id,),
            ).fetchall()
        ]
        all_resolved = all(e["status"] != "pending" for e in all_events)
        all_approved = all(e["status"] == "approved" for e in all_events)

        if all_resolved:
            new_status = "approved" if all_approved else "partially_rejected"
            db.execute(
                "UPDATE access_requests SET status = ? WHERE id = ?",
                (new_status, request_id),
            )

        # Audit log (inside transaction)
        audit_id = str(uuid.uuid4())
        action_details = json.dumps({"item": event["access_item"], "by": body.approver_name or "Manager"})
        db.execute(
            "INSERT INTO audit_log (id, acf2_id, access_request_id, event_type, details, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (audit_id, event["acf2_id"], request_id, f"approval_{body.action}", action_details, now),
        )

        db.execute("COMMIT")
    except HTTPException:
        raise
    except Exception:
        db.execute("ROLLBACK")
        raise

    if all_resolved:
        log("AGENT", f"Request {request_id} fully resolved: {new_status}")

        # Notify Teams that the request is fully resolved (outside transaction)
        if TEAMS_WEBHOOK_URL:
            req_rows = _safe_query("SELECT * FROM access_requests WHERE id = ?", (request_id,))
            if req_rows:
                req_info = req_rows[0]
                user_rows = _safe_query("SELECT name FROM users WHERE acf2_id = ?", (req_info["acf2_id"],))
                requester_name = user_rows[0]["name"] if user_rows else req_info["acf2_id"]
                desig_rows = _safe_query(
                    "SELECT title FROM designations WHERE id = ?",
                    (req_info.get("designation_id", ""),),
                )
                role_title = desig_rows[0]["title"] if desig_rows else req_info.get("designation_id", "")
                _send_teams_resolution(
                    requester_name=requester_name,
                    acf2_id=req_info["acf2_id"],
                    role_title=role_title,
                    approver_name=body.approver_name or event.get("approver", "Manager"),
                    all_approved=all_approved,
                    item_count=len(all_events),
                )

    log("AGENT", f"Approval {body.event_id}: {body.action} by {approver}")
    return {
        "event_id": body.event_id,
        "status": body.action,
        "all_resolved": all_resolved,
        "request_status": "approved" if all_approved and all_resolved else (
            "partially_rejected" if all_resolved else "pending_approval"
        ),
    }


# ── n8n Webhook ──────────────────────────────────────────────────────────────

def _fire_n8n_webhook(
    request_id: str,
    acf2_id: str,
    requester_name: str,
    role_title: str,
    team: str,
    final_bundle: list[dict],
    events_created: list[dict] | None = None,
) -> None:
    """Fire-and-forget POST to n8n for Jira-routed access items."""
    # Build event_id lookup from approval events
    event_map: dict[str, str] = {}
    for ev in (events_created or []):
        event_map[ev.get("access_item", "")] = ev.get("event_id", "")

    # Enrich each item with its system tag from the DB
    enriched_items = []
    for item in final_bundle:
        item_id = item.get("id", "")
        item_rows = _safe_query(
            "SELECT display_name, system, servicenow_catalog_item_id "
            "FROM role_access_items WHERE access_item = ? LIMIT 1",
            (item_id,),
        )
        system = item_rows[0].get("system", "") if item_rows else ""
        display_name = item_rows[0].get("display_name", item_id) if item_rows else item_id
        catalog_id = item_rows[0].get("servicenow_catalog_item_id", "") if item_rows else ""
        enriched_items.append({
            "id": item_id,
            "event_id": event_map.get(item_id, ""),
            "display_name": display_name,
            "system": system,
            "catalog_id": catalog_id,
            "jira_routed": system in JIRA_ROUTED_SYSTEMS,
        })

    payload = {
        "request_id": request_id,
        "acf2_id": acf2_id,
        "requester_name": requester_name,
        "role_title": role_title,
        "team": team,
        "items": enriched_items,
        "jira_items": [i for i in enriched_items if i["jira_routed"]],
        "callback_url": f"{BACKEND_PUBLIC_URL}/api/approvals/action",
        "jira_project_key": "HACK",
    }

    try:
        http_requests.post(
            N8N_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5,
            verify=False,
        )
        log("AGENT", f"n8n webhook fired: {len(payload['jira_items'])} Jira-routed items")
    except Exception as exc:
        log("AGENT", f"n8n webhook failed (non-critical): {exc}")


# ── Jira Ticket Creation via MCP ────────────────────────────────────────────

def _create_jira_tickets(
    request_id: str,
    acf2_id: str,
    requester_name: str,
    role_title: str,
    events_created: list[dict],
    final_bundle: list[dict],
) -> list[dict]:
    """Create Jira tickets for Jira-routed items and store mapping in DB."""
    from mcp_server.jira_server import create_jira_ticket, _is_configured

    if not _is_configured():
        return []

    # Build event_id lookup
    event_map: dict[str, str] = {}
    for ev in events_created:
        event_map[ev.get("access_item", "")] = ev.get("event_id", "")

    tickets_created = []
    for item in final_bundle:
        item_id = item.get("id", "")
        item_rows = _safe_query(
            "SELECT display_name, system FROM role_access_items "
            "WHERE access_item = ? LIMIT 1",
            (item_id,),
        )
        system = item_rows[0].get("system", "") if item_rows else ""
        display_name = item_rows[0].get("display_name", item_id) if item_rows else item_id

        if system not in JIRA_ROUTED_SYSTEMS:
            continue

        event_id = event_map.get(item_id, "")
        if not event_id:
            continue

        summary = f"[Access Request] {requester_name} — {display_name}"
        description = (
            f"ACF2: {acf2_id}\n"
            f"Role: {role_title}\n"
            f"System: {system}\n"
            f"Access Item: {display_name}\n"
            f"Event ID: {event_id}\n"
            f"Request ID: {request_id}"
        )
        labels = [
            f"ACF2_{acf2_id}",
            f"event_{event_id}",
            f"req_{request_id[:8]}",
        ]

        result_json = create_jira_ticket(summary, description, labels)
        result = json.loads(result_json)

        if result.get("success"):
            ticket_key = result["key"]
            now = int(time.time())
            # Store mapping in jira_tickets table
            ticket_id = str(uuid.uuid4())
            _safe_execute(
                "INSERT INTO jira_tickets (id, event_id, request_id, ticket_key, acf2_id, access_item, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, 'open', ?)",
                (ticket_id, event_id, request_id, ticket_key, acf2_id, item_id, now),
            )
            tickets_created.append({
                "event_id": event_id,
                "ticket_key": ticket_key,
                "display_name": display_name,
                "url": result.get("url", ""),
            })
            log("AGENT", f"Jira ticket created: {ticket_key} for {display_name} (event={event_id})")
        else:
            log("AGENT", f"Jira ticket creation failed for {display_name}: {result.get('error', 'unknown')}")

    return tickets_created


# ── Teams Webhook ────────────────────────────────────────────────────────────

FRONTEND_PUBLIC_URL = os.environ.get("FRONTEND_PUBLIC_URL", "http://localhost:3000")


def _send_teams_notification(
    request_id: str,
    requester_name: str,
    acf2_id: str,
    role_title: str,
    team: str,
    manager: str,
    items: list[dict],
) -> bool:
    """Send an Adaptive Card to MS Teams via Incoming Webhook with a review link."""

    items_text = "\n\n".join(
        f"- **{item['display_name']}** (approver: {item['approver']})"
        for item in items
    )

    review_url = f"{FRONTEND_PUBLIC_URL}/servicenow?highlight={request_id}"

    card = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "size": "Large",
                            "weight": "Bolder",
                            "text": "Access Request — Approval Needed",
                            "style": "heading",
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {"title": "Requester", "value": f"{requester_name} ({acf2_id})"},
                                {"title": "Role", "value": role_title},
                                {"title": "Team", "value": team},
                                {"title": "Manager", "value": manager},
                                {"title": "Items", "value": f"{len(items)} access items"},
                            ],
                        },
                        {
                            "type": "TextBlock",
                            "text": "**Access Items:**",
                            "wrap": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": items_text,
                            "wrap": True,
                            "size": "Small",
                        },
                        {
                            "type": "TextBlock",
                            "text": "Open the ServiceNow portal to review and approve or reject this request.",
                            "wrap": True,
                            "spacing": "Medium",
                            "color": "Accent",
                        },
                    ],
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": "Review in ServiceNow",
                            "url": review_url,
                            "style": "positive",
                        },
                    ],
                },
            }
        ],
    }

    try:
        resp = http_requests.post(
            TEAMS_WEBHOOK_URL,
            json=card,
            headers={"Content-Type": "application/json"},
            timeout=10,
            verify=False,
        )
        log("TEAMS", f"Webhook sent: status={resp.status_code}, url={review_url}")
        return resp.status_code in (200, 202)
    except Exception as exc:
        log("TEAMS", f"Webhook failed: {exc}")
        return False


def _send_teams_resolution(
    requester_name: str,
    acf2_id: str,
    role_title: str,
    approver_name: str,
    all_approved: bool,
    item_count: int,
) -> None:
    """Send a Teams card when a request is fully approved or rejected."""
    status_text = "✓ Access Request Approved" if all_approved else "✗ Access Request Partially Rejected"
    status_color = "Good" if all_approved else "Warning"
    outcome = f"All {item_count} access items approved" if all_approved else f"Some items were rejected"

    card = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "size": "Large",
                            "weight": "Bolder",
                            "text": status_text,
                            "color": status_color,
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {"title": "Requester", "value": f"{requester_name} ({acf2_id})"},
                                {"title": "Role", "value": role_title},
                                {"title": "Outcome", "value": outcome},
                                {"title": "Approved by", "value": approver_name},
                            ],
                        },
                        {
                            "type": "TextBlock",
                            "text": "Access will be provisioned shortly." if all_approved else "Please contact IT for rejected items.",
                            "wrap": True,
                            "isSubtle": True,
                        },
                    ],
                },
            }
        ],
    }

    try:
        resp = http_requests.post(
            TEAMS_WEBHOOK_URL,
            json=card,
            headers={"Content-Type": "application/json"},
            timeout=10,
            verify=False,
        )
        log("TEAMS", f"Resolution card sent: status={resp.status_code}")
    except Exception as exc:
        log("TEAMS", f"Resolution card failed: {exc}")
