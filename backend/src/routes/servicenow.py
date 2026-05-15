"""
Mock ServiceNow RITM route — HackHERway PS6.

Endpoint:
  GET /api/servicenow/ritms?acf2_id=ARUN01

Returns access requests formatted as ServiceNow RITM records.
"""

import json
from fastapi import APIRouter, HTTPException

from ..lib.sqlite import get_db

router = APIRouter()

# Items routed to Jira — should NOT appear on ServiceNow portal
JIRA_ROUTED_SYSTEMS = {
    "Jira", "GitHub", "Confluence",
    "Database", "Data Warehouse", "Data Platform",
    "Notebook", "BI",
}


def _safe_query(sql: str, params: tuple = ()):
    db = get_db()
    rows = db.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def _is_snow_item(access_item: str) -> bool:
    """Check if an access item belongs to ServiceNow (not Jira-routed)."""
    rows = _safe_query(
        "SELECT system FROM role_access_items WHERE access_item = ? LIMIT 1",
        (access_item,),
    )
    if not rows:
        return True
    return rows[0].get("system", "") not in JIRA_ROUTED_SYSTEMS


_STATUS_MAP = {
    "pending": "Awaiting Approval",
    "pending_approval": "Awaiting Approval",
    "approved": "Closed Complete",
    "partially_rejected": "Closed Incomplete",
    "fully_approved": "Closed Complete",
}

_STATE_COLOR = {
    "Awaiting Approval": "blue",
    "Closed Complete": "green",
    "Closed Incomplete": "gray",
}


def _ritm_number(request_id: str) -> str:
    """Derive a deterministic 7-digit RITM number from the request UUID."""
    numeric = int(request_id.replace("-", "")[:12], 16) % 9_000_000 + 1_000_000
    return f"RITM{numeric}"


@router.get("/ritms")
def get_ritms(acf2_id: str):
    # Validate user exists
    user_rows = _safe_query("SELECT * FROM users WHERE acf2_id = ?", (acf2_id,))
    if not user_rows:
        raise HTTPException(status_code=404, detail="User not found")

    user = user_rows[0]
    requester_name = user.get("name", acf2_id)

    requests = _safe_query(
        "SELECT * FROM access_requests WHERE acf2_id = ? ORDER BY created_at DESC",
        (acf2_id,),
    )

    ritms = []
    for req in requests:
        designation_rows = _safe_query(
            "SELECT title FROM designations WHERE id = ?",
            (req.get("designation_id", ""),),
        )
        role_title = designation_rows[0]["title"] if designation_rows else req.get("designation_id", "Unknown Role")

        # Parse the final_bundle JSON to get access item IDs
        try:
            bundle_ids = json.loads(req.get("final_bundle") or "[]")
        except Exception:
            bundle_ids = []

        # Fetch catalog details for each item
        catalog_items = []
        for item_id in bundle_ids:
            item_rows = _safe_query(
                "SELECT display_name, system, servicenow_catalog_item_id "
                "FROM role_access_items WHERE access_item = ? LIMIT 1",
                (item_id,),
            )
            if item_rows:
                row = item_rows[0]
                catalog_items.append({
                    "id": item_id,
                    "display_name": row.get("display_name", item_id),
                    "system": row.get("system", ""),
                    "catalog_id": row.get("servicenow_catalog_item_id", ""),
                })
            else:
                catalog_items.append({
                    "id": item_id,
                    "display_name": item_id,
                    "system": "",
                    "catalog_id": "",
                })

        raw_status = req.get("status", "pending")
        sn_state = _STATUS_MAP.get(raw_status, "Awaiting Approval")

        ritms.append({
            "ritm_number": _ritm_number(req["id"]),
            "request_id": req["id"],
            "short_description": f"Access Request - {requester_name} ({acf2_id})",
            "role_title": role_title,
            "requested_for": requester_name,
            "requested_by": "Access Assistant AI",
            "state": sn_state,
            "state_color": _STATE_COLOR.get(sn_state, "blue"),
            "opened_at": req.get("created_at"),
            "catalog_items": catalog_items,
            "item_count": len(catalog_items),
        })

    return {"ritms": ritms, "requester_name": requester_name}


@router.get("/pending-ritms")
def get_pending_ritms():
    """Return all access requests with pending approvals — for the approver view."""
    requests = _safe_query(
        "SELECT * FROM access_requests "
        "WHERE status NOT IN ('approved', 'fully_approved') "
        "ORDER BY created_at DESC",
    )

    ritms = []
    for req in requests:
        # Only include if there are actual pending approval events
        pending_events = _safe_query(
            "SELECT * FROM approval_events "
            "WHERE access_request_id = ? AND status = 'pending'",
            (req["id"],),
        )
        if not pending_events:
            continue

        user_rows = _safe_query("SELECT name FROM users WHERE acf2_id = ?", (req["acf2_id"],))
        requester_name = user_rows[0]["name"] if user_rows else req["acf2_id"]

        designation_rows = _safe_query(
            "SELECT title FROM designations WHERE id = ?",
            (req.get("designation_id", ""),),
        )
        role_title = designation_rows[0]["title"] if designation_rows else req.get("designation_id", "Unknown Role")

        try:
            bundle_ids = json.loads(req.get("final_bundle") or "[]")
        except Exception:
            bundle_ids = []

        catalog_items = []
        for item_id in bundle_ids:
            if not _is_snow_item(item_id):
                continue
            item_rows = _safe_query(
                "SELECT display_name, system, servicenow_catalog_item_id "
                "FROM role_access_items WHERE access_item = ? LIMIT 1",
                (item_id,),
            )
            if item_rows:
                row = item_rows[0]
                catalog_items.append({
                    "id": item_id,
                    "display_name": row.get("display_name", item_id),
                    "system": row.get("system", ""),
                    "catalog_id": row.get("servicenow_catalog_item_id", ""),
                })
            else:
                catalog_items.append({"id": item_id, "display_name": item_id, "system": "", "catalog_id": ""})

        # Build per-item approval events — only ServiceNow-routed items
        all_events = _safe_query(
            "SELECT * FROM approval_events WHERE access_request_id = ? "
            "ORDER BY submitted_at ASC",
            (req["id"],),
        )
        approval_items = []
        for ev in all_events:
            if not _is_snow_item(ev["access_item"]):
                continue
            item_rows = _safe_query(
                "SELECT display_name FROM role_access_items "
                "WHERE access_item = ? LIMIT 1",
                (ev["access_item"],),
            )
            display_name = item_rows[0]["display_name"] if item_rows else ev["access_item"]
            approval_items.append({
                "event_id": ev["id"],
                "access_item": ev["access_item"],
                "display_name": display_name,
                "approver": ev.get("approver", ""),
                "status": ev.get("status", "pending"),
            })

        if not approval_items:
            continue

        ritms.append({
            "ritm_number": _ritm_number(req["id"]),
            "request_id": req["id"],
            "short_description": f"Access Request - {requester_name} ({req['acf2_id']})",
            "acf2_id": req["acf2_id"],
            "role_title": role_title,
            "requested_for": requester_name,
            "requested_by": "Access Assistant AI",
            "state": "Awaiting Approval",
            "state_color": "blue",
            "opened_at": req.get("created_at"),
            "catalog_items": catalog_items,
            "approval_items": approval_items,
            "item_count": len(catalog_items),
            "pending_count": len(approval_items),
        })

    return {"ritms": ritms}


@router.get("/resolved-ritms")
def get_resolved_ritms():
    """Return all fully resolved requests — for the approver completed tab."""
    requests = _safe_query(
        "SELECT * FROM access_requests "
        "WHERE status IN ('approved', 'fully_approved', 'partially_rejected') "
        "ORDER BY created_at DESC",
    )

    ritms = []
    for req in requests:
        user_rows = _safe_query("SELECT name FROM users WHERE acf2_id = ?", (req["acf2_id"],))
        requester_name = user_rows[0]["name"] if user_rows else req["acf2_id"]

        designation_rows = _safe_query(
            "SELECT title FROM designations WHERE id = ?",
            (req.get("designation_id", ""),),
        )
        role_title = designation_rows[0]["title"] if designation_rows else req.get("designation_id", "Unknown Role")

        all_events = _safe_query(
            "SELECT * FROM approval_events WHERE access_request_id = ? "
            "ORDER BY submitted_at ASC",
            (req["id"],),
        )

        approval_items = []
        for ev in all_events:
            item_rows = _safe_query(
                "SELECT display_name FROM role_access_items "
                "WHERE access_item = ? LIMIT 1",
                (ev["access_item"],),
            )
            display_name = item_rows[0]["display_name"] if item_rows else ev["access_item"]
            approval_items.append({
                "event_id": ev["id"],
                "access_item": ev["access_item"],
                "display_name": display_name,
                "approver": ev.get("approver", ""),
                "status": ev.get("status", "pending"),
                "resolved_at": ev.get("resolved_at"),
            })

        raw_status = req.get("status", "approved")
        sn_state = _STATUS_MAP.get(raw_status, "Closed Complete")

        ritms.append({
            "ritm_number": _ritm_number(req["id"]),
            "request_id": req["id"],
            "short_description": f"Access Request - {requester_name} ({req['acf2_id']})",
            "acf2_id": req["acf2_id"],
            "role_title": role_title,
            "requested_for": requester_name,
            "state": sn_state,
            "state_color": _STATE_COLOR.get(sn_state, "green"),
            "opened_at": req.get("created_at"),
            "approval_items": approval_items,
            "item_count": len(approval_items),
        })

    return {"ritms": ritms}
