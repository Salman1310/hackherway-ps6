import json

from fastapi import APIRouter, HTTPException, Query
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


@router.get("/conversations/{conversation_id}")
def get_conversation_detail(conversation_id: str) -> dict:
    db = get_db()
    conversation = db.execute(
        """SELECT id, acf2_id, created_at, updated_at, session_json
           FROM conversations
           WHERE id = ?""",
        (conversation_id,),
    ).fetchone()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.execute(
        """SELECT id, role, content, created_at
           FROM messages
           WHERE conversation_id = ?
           ORDER BY created_at ASC""",
        (conversation_id,),
    ).fetchall()

    session_json = conversation["session_json"]
    try:
        session = json.loads(session_json) if session_json else None
    except json.JSONDecodeError:
        session = None

    return {
        "conversation": dict(conversation),
        "messages": [dict(row) for row in messages],
        "session": session,
    }
