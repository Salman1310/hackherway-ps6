"""
Mock ServiceNow RITM route — HackHERway PS6.

Endpoint:
  GET /api/servicenow/ritms?acf2_id=ARUN01

Returns access requests formatted as ServiceNow RITM records.
"""

import json
from fastapi import APIRouter, HTTPException

router = APIRouter()


def _query(sql: str):
    from mcp_server.sqlite_server import query_db
    result = query_db(sql)
    parsed = json.loads(result)
    if isinstance(parsed, dict) and "error" in parsed:
        raise HTTPException(status_code=400, detail=parsed["error"])
    return parsed


def _esc(value: str) -> str:
    return str(value).replace("'", "''")


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
    user_rows = _query(f"SELECT * FROM users WHERE acf2_id = '{_esc(acf2_id)}'")
    if not user_rows:
        raise HTTPException(status_code=404, detail="User not found")

    user = user_rows[0]
    requester_name = user.get("name", acf2_id)

    requests = _query(
        f"SELECT * FROM access_requests WHERE acf2_id = '{_esc(acf2_id)}' "
        f"ORDER BY created_at DESC"
    )

    ritms = []
    for req in requests:
        designation_rows = _query(
            f"SELECT title FROM designations WHERE id = '{_esc(req.get('designation_id', ''))}'"
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
            item_rows = _query(
                f"SELECT display_name, system, servicenow_catalog_item_id "
                f"FROM role_access_items WHERE access_item = '{_esc(item_id)}' LIMIT 1"
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
    requests = _query(
        "SELECT * FROM access_requests "
        "WHERE status NOT IN ('approved', 'fully_approved') "
        "ORDER BY created_at DESC"
    )

    ritms = []
    for req in requests:
        # Only include if there are actual pending approval events
        pending_events = _query(
            f"SELECT * FROM approval_events "
            f"WHERE access_request_id = '{_esc(req['id'])}' AND status = 'pending'"
        )
        if not pending_events:
            continue

        user_rows = _query(f"SELECT name FROM users WHERE acf2_id = '{_esc(req['acf2_id'])}'")
        requester_name = user_rows[0]["name"] if user_rows else req["acf2_id"]

        designation_rows = _query(
            f"SELECT title FROM designations WHERE id = '{_esc(req.get('designation_id', ''))}'"
        )
        role_title = designation_rows[0]["title"] if designation_rows else req.get("designation_id", "Unknown Role")

        try:
            bundle_ids = json.loads(req.get("final_bundle") or "[]")
        except Exception:
            bundle_ids = []

        catalog_items = []
        for item_id in bundle_ids:
            item_rows = _query(
                f"SELECT display_name, system, servicenow_catalog_item_id "
                f"FROM role_access_items WHERE access_item = '{_esc(item_id)}' LIMIT 1"
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

        # Build per-item approval events with status
        all_events = _query(
            f"SELECT * FROM approval_events WHERE access_request_id = '{_esc(req['id'])}' "
            f"ORDER BY submitted_at ASC"
        )
        approval_items = []
        for ev in all_events:
            item_rows = _query(
                f"SELECT display_name FROM role_access_items "
                f"WHERE access_item = '{_esc(ev['access_item'])}' LIMIT 1"
            )
            display_name = item_rows[0]["display_name"] if item_rows else ev["access_item"]
            approval_items.append({
                "event_id": ev["id"],
                "access_item": ev["access_item"],
                "display_name": display_name,
                "approver": ev.get("approver", ""),
                "status": ev.get("status", "pending"),
            })

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
            "pending_count": len(pending_events),
        })

    return {"ritms": ritms}


@router.get("/resolved-ritms")
def get_resolved_ritms():
    """Return all fully resolved requests — for the approver completed tab."""
    requests = _query(
        "SELECT * FROM access_requests "
        "WHERE status IN ('approved', 'fully_approved', 'partially_rejected') "
        "ORDER BY created_at DESC"
    )

    ritms = []
    for req in requests:
        user_rows = _query(f"SELECT name FROM users WHERE acf2_id = '{_esc(req['acf2_id'])}'")
        requester_name = user_rows[0]["name"] if user_rows else req["acf2_id"]

        designation_rows = _query(
            f"SELECT title FROM designations WHERE id = '{_esc(req.get('designation_id', ''))}'"
        )
        role_title = designation_rows[0]["title"] if designation_rows else req.get("designation_id", "Unknown Role")

        all_events = _query(
            f"SELECT * FROM approval_events WHERE access_request_id = '{_esc(req['id'])}' "
            f"ORDER BY submitted_at ASC"
        )

        approval_items = []
        for ev in all_events:
            item_rows = _query(
                f"SELECT display_name FROM role_access_items "
                f"WHERE access_item = '{_esc(ev['access_item'])}' LIMIT 1"
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
