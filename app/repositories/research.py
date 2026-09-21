from uuid import UUID
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import exc

from app.models.research import (
    ResearchRun,
    ResearchTask,
    ResearchEvidence,
    ResearchArtifact,
    ResearchReport,
    ResearchUsage,
    ResearchEvent,
)

class ResearchRepository:
    """
    Unified repository for all Research Fabric models.
    Enforces workspace_id isolation on all reads and writes.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==========================
    # Helper: workspace check
    # ==========================
    async def _verify_run_workspace(self, run_id: UUID, workspace_id: UUID) -> None:
        """
        Internal helper to ensure a given run_id belongs to the workspace_id.
        Raises an exception if it does not.
        """
        stmt = select(ResearchRun).where(ResearchRun.run_id == run_id, ResearchRun.workspace_id == workspace_id)
        result = await self.session.execute(stmt)
        run = result.scalar_one_or_none()
        if not run:
            raise ValueError(f"ResearchRun {run_id} not found in workspace {workspace_id}")

    # ==========================
    # ResearchRun
    # ==========================
    async def create_run(self, workspace_id: UUID, owner_id: UUID, objective: str, engine: str, engine_revision: Optional[str] = None) -> ResearchRun:
        run = ResearchRun(
            workspace_id=workspace_id,
            owner_id=owner_id,
            objective=objective,
            engine=engine,
            engine_revision=engine_revision,
            status="pending"
        )
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def get_run(self, workspace_id: UUID, run_id: UUID) -> Optional[ResearchRun]:
        stmt = select(ResearchRun).where(ResearchRun.run_id == run_id, ResearchRun.workspace_id == workspace_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ==========================
    # ResearchTask
    # ==========================
    async def create_task(self, workspace_id: UUID, run_id: UUID, objective: str) -> ResearchTask:
        await self._verify_run_workspace(run_id, workspace_id)
        task = ResearchTask(
            run_id=run_id,
            objective=objective,
            status="pending"
        )
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get_task(self, workspace_id: UUID, run_id: UUID, task_id: UUID) -> Optional[ResearchTask]:
        await self._verify_run_workspace(run_id, workspace_id)
        stmt = select(ResearchTask).where(ResearchTask.task_id == task_id, ResearchTask.run_id == run_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ==========================
    # ResearchEvidence
    # ==========================
    async def create_evidence(self, workspace_id: UUID, run_id: UUID, content: str, task_id: Optional[UUID] = None, source_id: Optional[UUID] = None, retriever: Optional[str] = None, query: Optional[str] = None, locator: Optional[str] = None, fingerprint: Optional[str] = None, tags: Optional[List[str]] = None, provenance: Optional[dict] = None) -> ResearchEvidence:
        await self._verify_run_workspace(run_id, workspace_id)
        evidence = ResearchEvidence(
            run_id=run_id,
            task_id=task_id,
            source_id=source_id,
            retriever=retriever,
            query=query,
            content=content,
            locator=locator,
            fingerprint=fingerprint,
            tags=tags or [],
            provenance=provenance
        )
        self.session.add(evidence)
        await self.session.commit()
        await self.session.refresh(evidence)
        return evidence

    async def get_evidence(self, workspace_id: UUID, run_id: UUID, evidence_id: UUID) -> Optional[ResearchEvidence]:
        await self._verify_run_workspace(run_id, workspace_id)
        stmt = select(ResearchEvidence).where(ResearchEvidence.evidence_id == evidence_id, ResearchEvidence.run_id == run_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
        
    async def list_evidence_for_run(self, workspace_id: UUID, run_id: UUID) -> List[ResearchEvidence]:
        await self._verify_run_workspace(run_id, workspace_id)
        stmt = select(ResearchEvidence).where(ResearchEvidence.run_id == run_id).order_by(ResearchEvidence.retrieved_at)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # ==========================
    # ResearchArtifact
    # ==========================
    async def create_artifact(self, workspace_id: UUID, run_id: UUID, artifact_type: str, payload: dict, task_id: Optional[UUID] = None, tags: Optional[List[str]] = None) -> ResearchArtifact:
        await self._verify_run_workspace(run_id, workspace_id)
        artifact = ResearchArtifact(
            run_id=run_id,
            task_id=task_id,
            type=artifact_type,
            tags=tags or [],
            payload=payload
        )
        self.session.add(artifact)
        await self.session.commit()
        await self.session.refresh(artifact)
        return artifact

    async def get_artifact(self, workspace_id: UUID, run_id: UUID, artifact_id: UUID) -> Optional[ResearchArtifact]:
        await self._verify_run_workspace(run_id, workspace_id)
        stmt = select(ResearchArtifact).where(ResearchArtifact.artifact_id == artifact_id, ResearchArtifact.run_id == run_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ==========================
    # ResearchReport
    # ==========================
    async def create_report(self, workspace_id: UUID, run_id: UUID, objective: str, content: str, citations: Optional[dict] = None, source_summary: Optional[dict] = None, limitations: Optional[str] = None, warnings: Optional[str] = None, version: Optional[str] = None) -> ResearchReport:
        await self._verify_run_workspace(run_id, workspace_id)
        report = ResearchReport(
            run_id=run_id,
            objective=objective,
            content=content,
            citations=citations,
            source_summary=source_summary,
            limitations=limitations,
            warnings=warnings,
            version=version
        )
        self.session.add(report)
        await self.session.commit()
        await self.session.refresh(report)
        return report

    async def get_report(self, workspace_id: UUID, run_id: UUID, report_id: UUID) -> Optional[ResearchReport]:
        await self._verify_run_workspace(run_id, workspace_id)
        stmt = select(ResearchReport).where(ResearchReport.report_id == report_id, ResearchReport.run_id == run_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ==========================
    # ResearchUsage
    # ==========================
    async def create_usage(self, workspace_id: UUID, run_id: UUID, task_id: Optional[UUID] = None, model_calls: int = 0, input_tokens: int = 0, output_tokens: int = 0, retrieval_calls: int = 0, search_calls: int = 0, mcp_calls: int = 0, latency: float = 0.0, cost: float = 0.0, estimation_type: str = "estimated") -> ResearchUsage:
        await self._verify_run_workspace(run_id, workspace_id)
        usage = ResearchUsage(
            run_id=run_id,
            task_id=task_id,
            model_calls=model_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            retrieval_calls=retrieval_calls,
            search_calls=search_calls,
            mcp_calls=mcp_calls,
            latency=latency,
            cost=cost,
            estimation_type=estimation_type
        )
        self.session.add(usage)
        await self.session.commit()
        await self.session.refresh(usage)
        return usage

    async def get_usage(self, workspace_id: UUID, run_id: UUID, usage_id: UUID) -> Optional[ResearchUsage]:
        await self._verify_run_workspace(run_id, workspace_id)
        stmt = select(ResearchUsage).where(ResearchUsage.usage_id == usage_id, ResearchUsage.run_id == run_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ==========================
    # ResearchEvent
    # ==========================
    async def create_event(self, workspace_id: UUID, run_id: UUID, event_type: str, payload: Optional[dict] = None, task_id: Optional[UUID] = None) -> ResearchEvent:
        await self._verify_run_workspace(run_id, workspace_id)
        event = ResearchEvent(
            run_id=run_id,
            task_id=task_id,
            event_type=event_type,
            payload=payload
        )
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def get_events_for_run(self, workspace_id: UUID, run_id: UUID) -> List[ResearchEvent]:
        await self._verify_run_workspace(run_id, workspace_id)
        stmt = select(ResearchEvent).where(ResearchEvent.run_id == run_id).order_by(ResearchEvent.created_at.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
