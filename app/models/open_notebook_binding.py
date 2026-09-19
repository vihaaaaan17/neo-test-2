import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

class OpenNotebookWorkspaceBinding(Base):
    __tablename__ = "open_notebook_workspace_bindings"

    # We use workspace_id as the primary key since it's a strict 1:1 mapping.
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), primary_key=True)
    open_notebook_notebook_id = Column(String, nullable=False, unique=True)
    status = Column(String, default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class OpenNotebookSourceBinding(Base):
    __tablename__ = "open_notebook_source_bindings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.source_id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_id = Column(UUID(as_uuid=True), ForeignKey("source_snapshots.snapshot_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Can be null initially if state is PENDING or PROJECTING
    open_notebook_source_id = Column(String, nullable=True, unique=True)
    
    checksum_sha256 = Column(String, nullable=False)
    
    # State machine: PENDING -> PROJECTING -> ACTIVE | FAILED | RECONCILIATION_REQUIRED
    projection_status = Column(String, default="PENDING", nullable=False)
    projected_at = Column(DateTime(timezone=True), nullable=True)
    error_meta = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint('source_id', 'snapshot_id', name='uq_source_snapshot_binding'),
    )

class OpenNotebookConversationBinding(Base):
    __tablename__ = "open_notebook_conversation_bindings"

    conversation_id = Column(UUID(as_uuid=True), ForeignKey("ground_conversations.conversation_id", ondelete="CASCADE"), primary_key=True)
    open_notebook_session_id = Column(String, nullable=False, unique=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

class DeletionTombstone(Base):
    __tablename__ = "deletion_tombstones"

    tombstone_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_type = Column(String, nullable=False) # 'workspace' or 'source'
    open_notebook_id = Column(String, nullable=True) # Upstream ID, can be null if creation never succeeded
    
    status = Column(String, default="pending", nullable=False, index=True) # pending, completed, failed
    attempt_count = Column(Integer, default=0, nullable=False)
    last_attempt = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
