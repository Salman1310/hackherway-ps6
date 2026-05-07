"""
Admin API routes — Role/Designation configuration (Phase 4).

Endpoints:
  GET    /api/admin/options                    — dropdown options (teams, depts, systems)
  GET    /api/admin/designations              — list all designations
  POST   /api/admin/designations              — create a designation
  PUT    /api/admin/designations/{id}         — update a designation
  DELETE /api/admin/designations/{id}         — delete a designation + its access items
  GET    /api/admin/designations/{id}/items   — list access items for a designation
  POST   /api/admin/designations/{id}/items   — create an access item
  PUT    /api/admin/items/{item_id}           — update an access item
  DELETE /api/admin/items/{item_id}           — delete an access item
"""

import json
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..lib.sqlite import get_db
from ..lib.logger import log

router = APIRouter()


# ── Request/Response models ──────────────────────────────────────────────────

class DesignationCreate(BaseModel):
    id: str
    title: str
    description: Optional[str] = ""
    team_hint: Optional[str] = ""
    dept_hint: Optional[str] = ""


class DesignationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    team_hint: Optional[str] = None
    dept_hint: Optional[str] = None


class AccessItemCreate(BaseModel):
    access_item: str
    display_name: Optional[str] = ""
    system: Optional[str] = ""
    description: Optional[str] = ""
    mandatory: bool = False
    owner_team: Optional[str] = ""
    servicenow_catalog_item_id: Optional[str] = ""
    sort_order: Optional[int] = 0


class AccessItemUpdate(BaseModel):
    access_item: Optional[str] = None
    display_name: Optional[str] = None
    system: Optional[str] = None
    description: Optional[str] = None
    mandatory: Optional[bool] = None
    owner_team: Optional[str] = None
    servicenow_catalog_item_id: Optional[str] = None
    sort_order: Optional[int] = None


class CopyDesignationRequest(BaseModel):
    source_designation_id: str
    id: str
    title: str
    description: Optional[str] = ""
    team_hint: Optional[str] = ""
    dept_hint: Optional[str] = ""


# ── Helpers ──────────────────────────────────────────────────────────────────

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


# ── Options (dropdowns) ──────────────────────────────────────────────────────

@router.get("/options")
def get_options():
    teams = _query(
        "SELECT DISTINCT team FROM users WHERE team IS NOT NULL AND team != 'TBD' "
        "UNION SELECT DISTINCT team_hint FROM designations WHERE team_hint IS NOT NULL AND team_hint != ''"
    )
    depts = _query(
        "SELECT DISTINCT dept FROM users WHERE dept IS NOT NULL AND dept != 'TBD' "
        "UNION SELECT DISTINCT dept_hint FROM designations WHERE dept_hint IS NOT NULL AND dept_hint != ''"
    )
    systems = _query(
        "SELECT DISTINCT system FROM role_access_items WHERE system IS NOT NULL AND system != ''"
    )
    owner_teams = _query(
        "SELECT DISTINCT owner_team FROM role_access_items WHERE owner_team IS NOT NULL AND owner_team != ''"
    )

    return {
        "teams": sorted(set(r.get("team") or r.get("team_hint") or "" for r in teams) - {""}),
        "departments": sorted(set(r.get("dept") or r.get("dept_hint") or "" for r in depts) - {""}),
        "systems": sorted(set(r.get("system", "") for r in systems) - {""}),
        "owner_teams": sorted(set(r.get("owner_team", "") for r in owner_teams) - {""}),
    }



# ── Designation CRUD ─────────────────────────────────────────────────────────

@router.get("/designations")
def list_designations():
    rows = _query("SELECT * FROM designations ORDER BY title ASC")
    for row in rows:
        items = _query(
            f"SELECT COUNT(*) as cnt FROM role_access_items WHERE designation_id = '{_esc(row['id'])}'"
        )
        row["item_count"] = items[0]["cnt"] if items else 0
    return {"designations": rows}


@router.post("/designations", status_code=201)
def create_designation(body: DesignationCreate):
    existing = _query(f"SELECT id FROM designations WHERE id = '{_esc(body.id)}'")
    if existing:
        raise HTTPException(status_code=409, detail=f"Designation '{body.id}' already exists")

    sql = (
        f"INSERT INTO designations (id, title, description, team_hint, dept_hint) "
        f"VALUES ('{_esc(body.id)}', '{_esc(body.title)}', '{_esc(body.description or '')}', "
        f"'{_esc(body.team_hint or '')}', '{_esc(body.dept_hint or '')}')"
    )
    _execute(sql)
    log("ADMIN", f"Created designation: {body.id}")
    return {"id": body.id, "created": True}


@router.post("/designations/copy", status_code=201)
def copy_designation(body: CopyDesignationRequest):
    source_id = body.source_designation_id.strip()
    target_id = body.id.strip()
    if not source_id or not target_id or not body.title.strip():
        raise HTTPException(status_code=400, detail="Source, target ID, and title are required")

    db = get_db()
    source = db.execute(
        "SELECT * FROM designations WHERE id = ?",
        (source_id,),
    ).fetchone()
    if not source:
        raise HTTPException(status_code=404, detail="Source designation not found")

    existing = db.execute(
        "SELECT id FROM designations WHERE id = ?",
        (target_id,),
    ).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail=f"Designation '{target_id}' already exists")

    rows = db.execute(
        "SELECT * FROM role_access_items WHERE designation_id = ? ORDER BY mandatory DESC, sort_order ASC",
        (source_id,),
    ).fetchall()

    try:
        db.execute("BEGIN")
        db.execute(
            "INSERT INTO designations (id, title, description, team_hint, dept_hint) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                target_id,
                body.title.strip(),
                body.description or "",
                body.team_hint or "",
                body.dept_hint or "",
            ),
        )
        for row in rows:
            db.execute(
                """
                INSERT INTO role_access_items
                  (id, designation_id, access_item, display_name, system, description,
                   mandatory, owner_team, servicenow_catalog_item_id, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{target_id}_{row['access_item']}",
                    target_id,
                    row["access_item"],
                    row["display_name"],
                    row["system"],
                    row["description"],
                    row["mandatory"],
                    row["owner_team"],
                    row["servicenow_catalog_item_id"],
                    row["sort_order"],
                ),
            )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

    log("ADMIN", f"Copied designation: {source_id} -> {target_id}")
    return {"id": target_id, "copied_from": source_id, "items_copied": len(rows)}


@router.put("/designations/{designation_id}")
def update_designation(designation_id: str, body: DesignationUpdate):
    existing = _query(f"SELECT id FROM designations WHERE id = '{_esc(designation_id)}'")
    if not existing:
        raise HTTPException(status_code=404, detail="Designation not found")

    updates = []
    if body.title is not None:
        updates.append(f"title = '{_esc(body.title)}'")
    if body.description is not None:
        updates.append(f"description = '{_esc(body.description)}'")
    if body.team_hint is not None:
        updates.append(f"team_hint = '{_esc(body.team_hint)}'")
    if body.dept_hint is not None:
        updates.append(f"dept_hint = '{_esc(body.dept_hint)}'")

    if not updates:
        return {"updated": False}

    sql = f"UPDATE designations SET {', '.join(updates)} WHERE id = '{_esc(designation_id)}'"
    _execute(sql)
    log("ADMIN", f"Updated designation: {designation_id}")
    return {"id": designation_id, "updated": True}


@router.delete("/designations/{designation_id}")
def delete_designation(designation_id: str):
    existing = _query(f"SELECT id FROM designations WHERE id = '{_esc(designation_id)}'")
    if not existing:
        raise HTTPException(status_code=404, detail="Designation not found")

    _execute(f"DELETE FROM role_access_items WHERE designation_id = '{_esc(designation_id)}'")
    _execute(f"DELETE FROM designations WHERE id = '{_esc(designation_id)}'")
    log("ADMIN", f"Deleted designation: {designation_id}")
    return {"id": designation_id, "deleted": True}


# ── Access Items CRUD ────────────────────────────────────────────────────────

@router.get("/designations/{designation_id}/items")
def list_access_items(designation_id: str):
    rows = _query(
        f"SELECT * FROM role_access_items WHERE designation_id = '{_esc(designation_id)}' "
        f"ORDER BY mandatory DESC, sort_order ASC"
    )
    return {"items": rows}


@router.post("/designations/{designation_id}/items", status_code=201)
def create_access_item(designation_id: str, body: AccessItemCreate):
    existing = _query(f"SELECT id FROM designations WHERE id = '{_esc(designation_id)}'")
    if not existing:
        raise HTTPException(status_code=404, detail="Designation not found")

    item_id = f"{designation_id}_{body.access_item}"
    mandatory_int = 1 if body.mandatory else 0

    sql = (
        f"INSERT INTO role_access_items "
        f"(id, designation_id, access_item, display_name, system, description, "
        f"mandatory, owner_team, servicenow_catalog_item_id, sort_order) "
        f"VALUES ('{_esc(item_id)}', '{_esc(designation_id)}', '{_esc(body.access_item)}', "
        f"'{_esc(body.display_name or '')}', '{_esc(body.system or '')}', "
        f"'{_esc(body.description or '')}', {mandatory_int}, "
        f"'{_esc(body.owner_team or '')}', '{_esc(body.servicenow_catalog_item_id or '')}', "
        f"{body.sort_order or 0})"
    )
    _execute(sql)
    log("ADMIN", f"Created access item: {item_id} for {designation_id}")
    return {"id": item_id, "created": True}


@router.put("/items/{item_id}")
def update_access_item(item_id: str, body: AccessItemUpdate):
    existing = _query(f"SELECT id FROM role_access_items WHERE id = '{_esc(item_id)}'")
    if not existing:
        raise HTTPException(status_code=404, detail="Access item not found")

    updates = []
    if body.access_item is not None:
        updates.append(f"access_item = '{_esc(body.access_item)}'")
    if body.display_name is not None:
        updates.append(f"display_name = '{_esc(body.display_name)}'")
    if body.system is not None:
        updates.append(f"system = '{_esc(body.system)}'")
    if body.description is not None:
        updates.append(f"description = '{_esc(body.description)}'")
    if body.mandatory is not None:
        updates.append(f"mandatory = {1 if body.mandatory else 0}")
    if body.owner_team is not None:
        updates.append(f"owner_team = '{_esc(body.owner_team)}'")
    if body.servicenow_catalog_item_id is not None:
        updates.append(f"servicenow_catalog_item_id = '{_esc(body.servicenow_catalog_item_id)}'")
    if body.sort_order is not None:
        updates.append(f"sort_order = {body.sort_order}")

    if not updates:
        return {"updated": False}

    sql = f"UPDATE role_access_items SET {', '.join(updates)} WHERE id = '{_esc(item_id)}'"
    _execute(sql)
    log("ADMIN", f"Updated access item: {item_id}")
    return {"id": item_id, "updated": True}


@router.delete("/items/{item_id}")
def delete_access_item(item_id: str):
    existing = _query(f"SELECT id FROM role_access_items WHERE id = '{_esc(item_id)}'")
    if not existing:
        raise HTTPException(status_code=404, detail="Access item not found")

    _execute(f"DELETE FROM role_access_items WHERE id = '{_esc(item_id)}'")
    log("ADMIN", f"Deleted access item: {item_id}")
    return {"id": item_id, "deleted": True}
