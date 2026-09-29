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
    engine: str
    engine_revision: Optional[str] = None
    current_attempt_id: Optional[UUID] = None
    conversation_id: Optional[UUID] = None
    turn_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
