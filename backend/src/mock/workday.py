"""
Mock Workday API — HackHERway PS6

Endpoint:
    GET /mock/workday/employee/{acf2_id}

Returns the employee record for a known ACF2 ID, or 404 for unknown IDs.
Logs every hit with [MOCK] prefix.
"""

from fastapi import APIRouter, HTTPException
from ..lib.logger import mock as log_mock

router = APIRouter()

# ── Demo employee records ─────────────────────────────────────────────────────

_EMPLOYEES = {
    "ARUN01": {
        "acf2_id":        "ARUN01",
        "name":           "Arun Mehta",
        "team":           "Cloud Infrastructure",
        "manager":        "Raj Kumar",
        "manager_email":  "raj.kumar@sunlife.com",
        "dept":           "Technology",
        "employment_type": "full-time",
        "location":       "Toronto, ON",
        "start_date":     "2024-09-01",
    },
    "NEHA02": {
        "acf2_id":        "NEHA02",
        "name":           "Neha Kapoor",
        "team":           "Finance Analytics",
        "manager":        "Deepa Menon",
        "manager_email":  "deepa.menon@sunlife.com",
        "dept":           "Finance",
        "employment_type": "contract",
        "location":       "Waterloo, ON",
        "start_date":     "2025-01-06",
    },
    "SARA03": {
        "acf2_id":        "SARA03",
        "name":           "Sara Chen",
        "team":           "TBD",
        "manager":        "TBD",
        "manager_email":  "hr@sunlife.com",
        "dept":           "TBD",
        "employment_type": "full-time",
        "location":       "Toronto, ON",
        "start_date":     "2025-02-03",
    },
}


@router.get("/employee/{acf2_id}")
def get_employee(acf2_id: str) -> dict:
    """Return Workday employee record for the given ACF2 ID."""
    uid = acf2_id.upper()
    log_mock(f"Workday lookup → {uid}")

    employee = _EMPLOYEES.get(uid)
    if not employee:
        log_mock(f"Workday lookup FAILED → {uid} not found")
        raise HTTPException(status_code=404, detail=f"Employee {uid} not found in Workday")

    log_mock(f"Workday lookup OK → {employee['name']} ({employee['team']})")
    return {"status": "found", "employee": employee}
