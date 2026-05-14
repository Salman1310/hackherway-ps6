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

router = APIRouter()

TEAMS_WEBHOOK_URL = os.environ.get("TEAMS_WEBHOOK_URL", "")
BACKEND_PUBLIC_URL = os.environ.get("BACKEND_PUBLIC_URL", "http://localhost:8000")


def _query(sql: str):
    from mcp_server.sqlite_server import query_db
    result = query_db(sql)
    parsed = json.loads(result)
    if isinstance(parsed, dict) and "error" in parsed:
        raise HTTPException(status_code=400, detail=parsed["error"])
    return parsed


def _execute(sql: str) -> dict:
    from mcp_server.sqlite_server import execute_db
    result = execute_db(sql)
    parsed = json.loads(result)
    if isinstance(parsed, dict) and "error" in parsed:
        raise HTTPException(status_code=400, detail=parsed["error"])
    return parsed


def _esc(value: str) -> str:
    return str(value).replace("'", "''")


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
    user_rows = _query(f"SELECT * FROM users WHERE acf2_id = '{_esc(body.acf2_id)}'")
    if not user_rows:
        raise HTTPException(status_code=404, detail="User not found")

    user = user_rows[0]
    manager = user.get("manager", "Unknown Manager")
    team = user.get("team", "")
    requester_name = user.get("name", body.acf2_id)

    # Get designation title
    designation_rows = _query(
        f"SELECT title FROM designations WHERE id = '{_esc(body.designation_id)}'"
    )
    role_title = designation_rows[0]["title"] if designation_rows else body.designation_id

    # Create access request
    request_id = str(uuid.uuid4())
    now = int(time.time())
    bundle_ids = json.dumps([item.get("id", "") for item in body.final_bundle])

    _execute(
        f"INSERT INTO access_requests (id, acf2_id, designation_id, final_bundle, status, created_at) "
        f"VALUES ('{request_id}', '{_esc(body.acf2_id)}', '{_esc(body.designation_id)}', "
        f"'{_esc(bundle_ids)}', 'pending_approval', {now})"
    )

    # Create approval events for each item
    events_created = []
    for item in body.final_bundle:
        item_id = item.get("id", "")
        item_name = item.get("name", item_id)

        # Look up routing, fallback to manager
        routing = _query(
            f"SELECT * FROM approver_routing WHERE access_item = '{_esc(item_id)}'"
        )
        approver = routing[0]["approver_name"] if routing else manager

        event_id = str(uuid.uuid4())
        _execute(
            f"INSERT INTO approval_events "
            f"(id, access_request_id, acf2_id, role, team, access_item, approver, status, submitted_at) "
            f"VALUES ('{event_id}', '{request_id}', '{_esc(body.acf2_id)}', "
            f"'{_esc(role_title)}', '{_esc(team)}', '{_esc(item_id)}', "
            f"'{_esc(approver)}', 'pending', {now})"
        )
        events_created.append({
            "event_id": event_id,
            "access_item": item_id,
            "display_name": item_name,
            "approver": approver,
        })

    # Audit log
    audit_id = str(uuid.uuid4())
    details = _esc(json.dumps({"items": len(events_created), "manager": manager}))
    _execute(
        f"INSERT INTO audit_log (id, acf2_id, access_request_id, event_type, details, created_at) "
        f"VALUES ('{audit_id}', '{_esc(body.acf2_id)}', '{request_id}', "
        f"'request_submitted', '{details}', {now})"
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

    log("AGENT", f"Request submitted: {request_id} ({len(events_created)} items, teams={teams_sent})")

    return {
        "request_id": request_id,
        "status": "pending_approval",
        "events": events_created,
        "manager": manager,
        "teams_notified": teams_sent,
    }


# ── My Requests (all requests for a user) ───────────────────────────────────

@router.get("/my-requests")
def get_my_requests(acf2_id: str):
    requests = _query(
        f"SELECT * FROM access_requests WHERE acf2_id = '{_esc(acf2_id)}' "
        f"ORDER BY created_at DESC"
    )

    enriched = []
    for req in requests:
        # Designation title
        designation_rows = _query(
            f"SELECT title FROM designations WHERE id = '{_esc(req.get('designation_id', ''))}'"
        )
        role_title = designation_rows[0]["title"] if designation_rows else req.get("designation_id", "Unknown Role")

        # Approval events for this request
        events = _query(
            f"SELECT * FROM approval_events WHERE access_request_id = '{_esc(req['id'])}' "
            f"ORDER BY submitted_at ASC"
        )

        # Enrich events with display names
        for event in events:
            item_rows = _query(
                f"SELECT display_name, system FROM role_access_items "
                f"WHERE access_item = '{_esc(event['access_item'])}' LIMIT 1"
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
    events = _query(
        f"SELECT * FROM approval_events WHERE access_request_id = '{_esc(request_id)}' "
        f"ORDER BY submitted_at ASC"
    )

    request_rows = _query(f"SELECT * FROM access_requests WHERE id = '{_esc(request_id)}'")
    request_info = request_rows[0] if request_rows else None

    # Enrich with display names
    for event in events:
        access_item = event["access_item"]
        item_rows = _query(
            f"SELECT display_name, system FROM role_access_items "
            f"WHERE access_item = '{_esc(access_item)}' LIMIT 1"
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

    existing = _query(f"SELECT * FROM approval_events WHERE id = '{_esc(body.event_id)}'")
    if not existing:
        raise HTTPException(status_code=404, detail="Approval event not found")

    event = existing[0]
    if event["status"] != "pending":
        raise HTTPException(status_code=400, detail="This approval has already been resolved")

    now = int(time.time())
    approver = _esc(body.approver_name or event.get("approver", "Manager"))

    _execute(
        f"UPDATE approval_events SET status = '{body.action}', "
        f"approver = '{approver}', resolved_at = {now} "
        f"WHERE id = '{_esc(body.event_id)}'"
    )

    # Check if all events for this request are resolved
    request_id = event["access_request_id"]
    all_events = _query(
        f"SELECT status FROM approval_events WHERE access_request_id = '{_esc(request_id)}'"
    )
    all_resolved = all(e["status"] != "pending" for e in all_events)
    all_approved = all(e["status"] == "approved" for e in all_events)

    if all_resolved:
        new_status = "approved" if all_approved else "partially_rejected"
        _execute(
            f"UPDATE access_requests SET status = '{new_status}' "
            f"WHERE id = '{_esc(request_id)}'"
        )
        log("AGENT", f"Request {request_id} fully resolved: {new_status}")

    # Audit log
    audit_id = str(uuid.uuid4())
    event_acf2 = _esc(event["acf2_id"])
    action_details = _esc(json.dumps({"item": event["access_item"], "by": body.approver_name or "Manager"}))
    _execute(
        f"INSERT INTO audit_log (id, acf2_id, access_request_id, event_type, details, created_at) "
        f"VALUES ('{audit_id}', '{event_acf2}', '{_esc(request_id)}', "
        f"'approval_{body.action}', '{action_details}', {now})"
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

    review_url = f"{FRONTEND_PUBLIC_URL}/approvals?request_id={request_id}"

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
                            "text": "Access Request - Approval Needed",
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
                            "text": "Click the button below to review and approve or reject in the portal.",
                            "wrap": True,
                            "spacing": "Medium",
                        },
                    ],
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": "Review & Approve in Portal",
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
