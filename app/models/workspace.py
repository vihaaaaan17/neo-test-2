import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base

class Workspace(Base):
    __tablename__ = "workspaces"

    workspace_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String, default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    active_commit_id = Column(UUID(as_uuid=True), nullable=True)

class WorkspaceCommit(Base):
    __tablename__ = "workspace_commits"

    commit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id = Column(UUID(as_uuid=True), nullable=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False, index=True)
    active_knowledge_ids = Column(JSONB, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
