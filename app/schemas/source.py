from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime

class SourceSnapshotResponse(BaseModel):
    snapshot_id: UUID
    source_id: UUID
    file_uri: str
    filename: str
    size: int
    checksum_sha256: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SourceResponse(BaseModel):
    source_id: UUID
    workspace_id: UUID
    owner_id: UUID
    source_type: str
    created_at: datetime
    updated_at: datetime
    snapshots: list[SourceSnapshotResponse] = []

    model_config = ConfigDict(from_attributes=True)
