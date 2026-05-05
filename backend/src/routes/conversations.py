from fastapi import APIRouter, Query
from ..lib.sqlite import get_db

router = APIRouter()


@router.get("/conversations")
def get_conversations(acf2_id: str = Query(..., description="Employee ACF2 ID")) -> dict:
    try:
        db = get_db()
        rows = db.execute(
            """SELECT id, acf2_id, created_at, updated_at
               FROM conversations
               WHERE acf2_id = ?
               ORDER BY updated_at DESC
               LIMIT 20""",
            (acf2_id.upper(),),
        ).fetchall()
        return {"conversations": [dict(r) for r in rows]}
    except Exception as e:
        print(f"[GET /api/conversations] {e}")
        return {"conversations": []}
