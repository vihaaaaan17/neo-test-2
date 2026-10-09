from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ResearchRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: UUID
    workspace_id: UUID
    owner_id: UUID
    objective: str
    status: str
    routing_mode: str = "explicit"
    engine: Optional[str] = None  # NULL for an auto-routed run until an attempt answers
    engine_revision: Optional[str] = None
    current_attempt_id: Optional[UUID] = None
    conversation_id: Optional[UUID] = None
    turn_id: Optional[UUID] = None
    timeline_epoch: int = 1
    created_at: datetime
    updated_at: datetime
