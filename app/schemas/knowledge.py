from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Any, Literal

class Provenance(BaseModel):
    source_refs: list[UUID] = Field(default_factory=list, description="IDs of source chunks or snapshots")
    source_mode: Literal["ground", "research"] = Field(..., description="Mode that generated this knowledge (e.g. 'ground' or 'research')")

class KnowledgeMemoryCreate(BaseModel):
    knowledge_type: str
    content: str
    status: str
    provenance: Provenance
    confidence: Optional[float] = None
    tags: Optional[list[str]] = None
    entities: Optional[list[str]] = None
    domain: Optional[str] = None
    version: Optional[int] = 1

class KnowledgeMemoryResponse(KnowledgeMemoryCreate):
    knowledge_id: UUID
    workspace_id: UUID
    owner_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
