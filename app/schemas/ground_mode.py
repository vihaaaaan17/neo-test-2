from pydantic import BaseModel
from uuid import UUID
from typing import List

class AskRequest(BaseModel):
    query: str

class AskResponse(BaseModel):
    answer: str
    evidence: List[UUID]
    knowledge_id: UUID | None = None
    provenance_status: str | None = None
    turn_id: UUID | None = None
    conversation_id: UUID | None = None
