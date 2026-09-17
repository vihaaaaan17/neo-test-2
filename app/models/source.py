import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class Source(Base):
    __tablename__ = "sources"

    source_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False)
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    source_type = Column(String, default="document", nullable=False)
    # Tracks the background parsing job lifecycle.
    # Transitions: pending → processing → completed | failed
    processing_status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    snapshots = relationship("SourceSnapshot", back_populates="source", cascade="all, delete-orphan")

class SourceSnapshot(Base):
    __tablename__ = "source_snapshots"

    snapshot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.source_id", ondelete="CASCADE"), nullable=False)
    file_uri = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    checksum_sha256 = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    source = relationship("Source", back_populates="snapshots")
