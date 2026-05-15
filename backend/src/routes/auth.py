import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..lib.sqlite import get_db

router = APIRouter()


class LoginRequest(BaseModel):
    acf2_id: str
    password: str


@router.post("/login")
def login(body: LoginRequest) -> dict:
    acf2_id = body.acf2_id.strip().upper()
    if not acf2_id or not body.password:
        raise HTTPException(status_code=401, detail="Invalid ACF2 ID or password")

    db = get_db()
    row = db.execute(
        """
        SELECT u.acf2_id, u.name, u.team, u.manager, u.dept, u.employment_type
        FROM user_auth a
        JOIN users u ON u.acf2_id = a.acf2_id
        WHERE a.acf2_id = ? AND a.password = ?
        """,
        (acf2_id, body.password),
    ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid ACF2 ID or password")

    db.execute(
        "UPDATE user_auth SET last_login_at = ? WHERE acf2_id = ?",
        (int(time.time()), acf2_id),
    )
    db.commit()

    APPROVER_IDS = {"RAJ01", "DEEPA01"}
    user = dict(row)
    user["role"] = "approver" if acf2_id in APPROVER_IDS else "employee"
    return {"user": user}
