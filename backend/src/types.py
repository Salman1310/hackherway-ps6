from typing import Optional, Any, List
from pydantic import BaseModel


class WorkdayContext(BaseModel):
    name: str
    team: str
    manager: str
    dept: str
    employment_type: str


class SessionState(BaseModel):
    acf2_id: Optional[str] = None
    workday_context: Optional[WorkdayContext] = None
    resolved_role: Optional[Any] = None
    selected_template: Optional[Any] = None
    final_bundle: List[Any] = []
    request_id: Optional[str] = None


class ChatMessage(BaseModel):
    role: str  # 'user' | 'bot'
    content: str


class MessageRequest(BaseModel):
    content: str
    session: SessionState
    history: List[ChatMessage] = []


class AgentResponse(BaseModel):
    reply: str
    session_update: Optional[dict] = None
