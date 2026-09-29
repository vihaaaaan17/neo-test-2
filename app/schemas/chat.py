from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, AliasChoices, field_validator


class ChatEventType(str, Enum):
    RESEARCH_STARTED = "turn.research_started"
    RESEARCH_PLANNING = "turn.research_planning"
    RESEARCHING = "turn.researching"
    SYNTHESIZING = "turn.synthesizing"
    PROMOTION_AVAILABLE = "turn.promotion_available"
    COMPLETED = "turn.completed"
    PARTIAL = "turn.partial"
    CANCELLED = "turn.cancelled"
    FAILED = "turn.failed"
    SCRATCHPAD_ENTRY = "scratchpad_entry"
    STATUS_CHANGE = "status_change"
    TOKEN = "token"
    CITATION = "citation"
    GROUND_ANSWER = "ground_answer"
    DONE = "done"
    ERROR = "error"


# Module-level event constants for easy importing
EVENT_TURN_RESEARCH_STARTED = ChatEventType.RESEARCH_STARTED.value
EVENT_TURN_RESEARCH_PLANNING = ChatEventType.RESEARCH_PLANNING.value
EVENT_TURN_RESEARCHING = ChatEventType.RESEARCHING.value
EVENT_TURN_SYNTHESIZING = ChatEventType.SYNTHESIZING.value
EVENT_TURN_PROMOTION_AVAILABLE = ChatEventType.PROMOTION_AVAILABLE.value
EVENT_TURN_COMPLETED = ChatEventType.COMPLETED.value
EVENT_TURN_PARTIAL = ChatEventType.PARTIAL.value
EVENT_TURN_CANCELLED = ChatEventType.CANCELLED.value
EVENT_TURN_FAILED = ChatEventType.FAILED.value
EVENT_SCRATCHPAD_ENTRY = ChatEventType.SCRATCHPAD_ENTRY.value
EVENT_STATUS_CHANGE = ChatEventType.STATUS_CHANGE.value
EVENT_TOKEN = ChatEventType.TOKEN.value
EVENT_CITATION = ChatEventType.CITATION.value
EVENT_GROUND_ANSWER = ChatEventType.GROUND_ANSWER.value
EVENT_DONE = ChatEventType.DONE.value
EVENT_ERROR = ChatEventType.ERROR.value


class ConversationCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=255, description="Optional title for the conversation")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom metadata for the conversation")


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, description="Status: 'active' or 'archived'")
    metadata: Optional[Dict[str, Any]] = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    conversation_id: UUID
    workspace_id: UUID
    owner_id: UUID
    title: Optional[str] = None
    status: str = "active"
    last_turn_sequence: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("metadata_", "metadata"))
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int


class TurnCreate(BaseModel):
    message: str = Field(..., min_length=1, description="User prompt or instruction")
    mode: str = Field("ground", description="Execution mode: 'ground' or 'research'")
    client_request_id: Optional[str] = Field(None, max_length=255, description="Client idempotency key")
    source_scope: Optional[List[UUID]] = Field(None, description="Optional explicit source IDs for Ground mode")
    selected_source_ids: Optional[List[UUID]] = Field(None, description="Alias for source_scope or explicit selected sources")
    research_options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional execution parameters for research mode")

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in ("ground", "research"):
            raise ValueError(f"Invalid turn mode: '{v}'. Must be 'ground' or 'research'")
        return v

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Turn message cannot be empty")
        return v


class TurnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    turn_id: UUID
    conversation_id: UUID
    workspace_id: UUID
    owner_id: UUID
    sequence: int
    mode: str
    user_message: str
    assistant_message: Optional[str] = None
    status: str = "pending"
    research_run_id: Optional[UUID] = None
    client_request_id: Optional[str] = None
    source_scope: Optional[List[UUID]] = None
    ground_evidence_refs: List[Any] = Field(default_factory=list)
    context_version: Dict[str, Any] = Field(default_factory=dict)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TurnListResponse(BaseModel):
    turns: List[TurnResponse]
    total: int


class ChatEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: UUID
    turn_id: UUID
    sequence: int
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ChatEventListResponse(BaseModel):
    events: List[ChatEventResponse]
    total: int

