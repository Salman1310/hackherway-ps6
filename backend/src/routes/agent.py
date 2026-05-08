import json
import time
import uuid

from fastapi import APIRouter

from ..agent.index import handle_agent_message
from ..lib.logger import error as log_error
from ..lib.sqlite import get_db
from ..types import AgentResponse, MessageRequest

router = APIRouter()


@router.post("/message", response_model=AgentResponse)
def agent_message(body: MessageRequest) -> AgentResponse:
    if not body.content.strip():
        return AgentResponse(reply="Message content is required.")

    conversation_id = _ensure_conversation(
        body.authenticated_acf2_id,
        body.conversation_id,
    )

    try:
        result = handle_agent_message(body.content, body.session, body.history)
        if conversation_id:
            _persist_exchange(conversation_id, body, result)
        return AgentResponse(**result, conversation_id=conversation_id)
    except Exception as e:
        log_error(f"POST /api/agent/message - {e}")
        return AgentResponse(
            reply="Something went wrong on my end. Please try again.",
            conversation_id=conversation_id,
        )


def _ensure_conversation(
    authenticated_acf2_id: str | None,
    conversation_id: str | None,
) -> str | None:
    if not authenticated_acf2_id:
        return None

    acf2_id = authenticated_acf2_id.strip().upper()
    if not acf2_id:
        return None

    db = get_db()
    now = int(time.time())
    if conversation_id:
        existing = db.execute(
            "SELECT id FROM conversations WHERE id = ? AND acf2_id = ?",
            (conversation_id, acf2_id),
        ).fetchone()
        if existing:
            return conversation_id

    new_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO conversations (id, acf2_id, created_at, updated_at, session_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (new_id, acf2_id, now, now, None),
    )
    db.commit()
    return new_id


def _persist_exchange(conversation_id: str, body: MessageRequest, result: dict) -> None:
    db = get_db()
    now = int(time.time())
    reply = result.get("reply", "")
    session_snapshot = _merged_session_json(body, result.get("session_update"))

    db.execute(
        "INSERT INTO messages (id, conversation_id, role, content, created_at) "
        "VALUES (?, ?, 'user', ?, ?)",
        (str(uuid.uuid4()), conversation_id, body.content.strip(), now),
    )
    db.execute(
        "INSERT INTO messages (id, conversation_id, role, content, created_at) "
        "VALUES (?, ?, 'bot', ?, ?)",
        (str(uuid.uuid4()), conversation_id, reply, now + 1),
    )
    db.execute(
        "UPDATE conversations SET updated_at = ?, session_json = ? WHERE id = ?",
        (now + 1, session_snapshot, conversation_id),
    )
    db.commit()


def _merged_session_json(body: MessageRequest, session_update: dict | None) -> str:
    session_data = body.session.model_dump()
    if session_update:
        session_data.update(session_update)
    return json.dumps(session_data)
