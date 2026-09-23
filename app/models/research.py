import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from app.core.database import Base

class ResearchRun(Base):
    __tablename__ = "research_runs"

    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    objective = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False)
    engine = Column(String, nullable=False)
    engine_revision = Column(String, nullable=True)
    current_attempt_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class ResearchTask(Base):
    __tablename__ = "research_tasks"

    task_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    objective = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class ResearchEvidence(Base):
    __tablename__ = "research_evidence"

    evidence_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("research_tasks.task_id", ondelete="CASCADE"), nullable=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.source_id", ondelete="SET NULL"), nullable=True)
    retriever = Column(String, nullable=True)
    query = Column(String, nullable=True)
    content = Column(String, nullable=False)
    locator = Column(String, nullable=True)
    fingerprint = Column(String, nullable=True)
    tags = Column(ARRAY(String), default=list, nullable=False)
    provenance = Column(JSONB, nullable=True)
    source_resolution_status = Column(String, default="unresolved_external", nullable=False)
    provider = Column(String, nullable=True)
    provider_reference = Column(JSONB, nullable=True)
    retrieved_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ResearchArtifact(Base):
    __tablename__ = "research_artifacts"

    artifact_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("research_tasks.task_id", ondelete="CASCADE"), nullable=True)
    type = Column(String, nullable=False)
    tags = Column(ARRAY(String), default=list, nullable=False)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ResearchReport(Base):
    __tablename__ = "research_reports"

    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    objective = Column(String, nullable=False)
    content = Column(String, nullable=False)
    citations = Column(JSONB, nullable=True)
    source_summary = Column(JSONB, nullable=True)
    limitations = Column(String, nullable=True)
    warnings = Column(String, nullable=True)
    version = Column(String, nullable=True)
    provenance_version = Column(String, default="v1", nullable=False)
    status = Column(String, default="draft", nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ResearchUsage(Base):
    __tablename__ = "research_usages"

    usage_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("research_tasks.task_id", ondelete="CASCADE"), nullable=True)
    model_calls = Column(Integer, default=0, nullable=False)
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    retrieval_calls = Column(Integer, default=0, nullable=False)
    search_calls = Column(Integer, default=0, nullable=False)
    mcp_calls = Column(Integer, default=0, nullable=False)
    latency = Column(Float, default=0.0, nullable=False)
    cost = Column(Float, default=0.0, nullable=False)
    estimation_type = Column(String, default="estimated", nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ResearchEvent(Base):
    __tablename__ = "research_events"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("research_tasks.task_id", ondelete="CASCADE"), nullable=True)
    event_type = Column(String, nullable=False)
    sequence = Column(Integer, nullable=False)
    payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
