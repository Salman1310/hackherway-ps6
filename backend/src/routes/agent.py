from fastapi import APIRouter
from ..types import MessageRequest, AgentResponse
from ..agent.index import handle_agent_message
from ..lib.logger import error as log_error

router = APIRouter()


@router.post("/message", response_model=AgentResponse)
def agent_message(body: MessageRequest) -> AgentResponse:
    if not body.content.strip():
        return AgentResponse(reply="Message content is required.")

    try:
        result = handle_agent_message(body.content, body.session, body.history)
        return AgentResponse(**result)
    except Exception as e:
        log_error(f"POST /api/agent/message — {e}")
        return AgentResponse(reply="Something went wrong on my end. Please try again.")
