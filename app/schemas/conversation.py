from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[UUID] = None

class ChatResponse(BaseModel):
    answer: str
    conversation_id: UUID
