from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime

class WorkspaceCreate(BaseModel):
    pass

class WorkspaceUpdate(BaseModel):
    status: str

class WorkspaceResponse(BaseModel):
    workspace_id: UUID
    owner_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
