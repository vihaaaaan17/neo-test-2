from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import List

class WorkspaceCreate(BaseModel):
    pass

class WorkspaceUpdate(BaseModel):
    status: str

class WorkspaceResponse(BaseModel):
    workspace_id: UUID
    owner_id: UUID
    status: str
    active_commit_id: UUID | None = None
    ground_version: int = 1
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WorkspaceCommitResponse(BaseModel):
    commit_id: UUID
    parent_id: UUID | None = None
    workspace_id: UUID
    active_knowledge_ids: List[UUID]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RollbackRequest(BaseModel):
    commit_id: UUID

class ResearchRequest(BaseModel):
    objective: str
