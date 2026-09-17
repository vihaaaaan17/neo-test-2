from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional

class EpisodicMemoryCreate(BaseModel):
    event_type: str
    summary: str
    importance: Optional[float] = None
    run_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    outcome: Optional[str] = None
    entities: Optional[list[str]] = None
    embedding_ref: Optional[str] = None

class EpisodicMemoryResponse(EpisodicMemoryCreate):
    episode_id: UUID
    workspace_id: UUID
    owner_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
