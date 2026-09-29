from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, AliasChoices


class ScratchpadEntryCreate(BaseModel):
    entry_type: str = Field(..., description="Entry type: note, observation, hypothesis, investigation, finding")
    content: str = Field(..., min_length=1, description="Text body of the scratchpad entry")
    turn_id: Optional[UUID] = Field(None, description="Optional associated turn ID")
    run_id: Optional[UUID] = Field(None, description="Optional associated research run ID")
    is_pinned_to_workspace: bool = Field(False, description="Whether this entry is pinned to the entire workspace")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom metadata")


class ScratchpadEntryUpdate(BaseModel):
    content: Optional[str] = None
    lifecycle: Optional[str] = Field(None, description="Lifecycle: active, promoted, dismissed, superseded")
    is_pinned_to_workspace: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class ScratchpadEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    entry_id: UUID
    workspace_id: UUID
    conversation_id: Optional[UUID] = None
    turn_id: Optional[UUID] = None
    run_id: Optional[UUID] = None
    entry_type: str
    lifecycle: str
    content: str
    is_pinned_to_workspace: bool = False
    pinned_at: Optional[datetime] = None
    superseded_by_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("metadata_", "metadata"))
    created_at: datetime
    updated_at: datetime


class ScratchpadEntryListResponse(BaseModel):
    entries: List[ScratchpadEntryResponse]
    total: int
