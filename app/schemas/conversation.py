from pydantic import BaseModel
from uuid import UUID
from typing import Optional

# Re-export modern canonical chat schemas
from app.schemas.chat import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationListResponse,
    TurnCreate,
    TurnResponse,
    TurnListResponse,
    ChatEventResponse
)

# Legacy compatibility schemas
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[UUID] = None

class ChatResponse(BaseModel):
    answer: str
    conversation_id: UUID

__all__ = [
    "ChatRequest",
    "ChatResponse",
    "ConversationCreate",
    "ConversationUpdate",
    "ConversationResponse",
    "ConversationListResponse",
    "TurnCreate",
    "TurnResponse",
    "TurnListResponse",
    "ChatEventResponse"
]
