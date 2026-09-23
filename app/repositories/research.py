import json
import uuid
from uuid import UUID
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from arq.connections import Redis
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

    def __init__(self, session: AsyncSession, redis_client: Optional[Redis] = None):
        self.redis_client = redis_client
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
        attempt_id = uuid.uuid4()
        run = ResearchRun(
            workspace_id=workspace_id,
            owner_id=owner_id,
            objective=objective,
            engine=engine,
            engine_revision=engine_revision,
            status="pending",
            current_attempt_id=attempt_id
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
    async def batch_create_evidence(
        self,
        workspace_id: UUID,
        run_id: UUID,
        evidence_list: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> List[ResearchEvidence]:
        """
        Creates multiple evidence records in batches with fingerprint deduplication.
        """
        await self._verify_run_workspace(run_id, workspace_id)

        # Deduplicate by fingerprint
        unique_evidence = {}
        for ev in evidence_list:
            fingerprint = ev.get("fingerprint")
            if fingerprint and fingerprint not in unique_evidence:
                unique_evidence[fingerprint] = ev

        # Check for existing evidence with the same fingerprints
        fingerprints = list(unique_evidence.keys())
        existing_evidence = await self._get_evidence_by_fingerprints(workspace_id, run_id, fingerprints)
        existing_fingerprints = {ev.fingerprint for ev in existing_evidence}

        # Filter out evidence that already exists
        new_evidence = [
            ev for fingerprint, ev in unique_evidence.items()
            if fingerprint not in existing_fingerprints
        ]

        # Batch insert new evidence
        inserted_evidence = []
        for i in range(0, len(new_evidence), batch_size):
            batch = new_evidence[i:i + batch_size]
            created_batch = await self._bulk_insert_evidence(workspace_id, run_id, batch)
            inserted_evidence.extend(created_batch)

        return inserted_evidence

    async def _get_evidence_by_fingerprints(self, workspace_id: UUID, run_id: UUID, fingerprints: List[str]) -> List[ResearchEvidence]:
        """
        Retrieves evidence records by their fingerprints.
        """
        stmt = select(ResearchEvidence).where(
            ResearchEvidence.run_id == run_id,
            ResearchEvidence.fingerprint.in_(fingerprints)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def _bulk_insert_evidence(self, workspace_id: UUID, run_id: UUID, evidence_list: List[Dict[str, Any]]) -> List[ResearchEvidence]:
        """
        Performs a bulk insert of evidence records.
        """
        evidence_objects = [
            ResearchEvidence(
                run_id=run_id,
                task_id=ev.get("task_id"),
                source_id=ev.get("source_id"),
                retriever=ev.get("retriever"),
                query=ev.get("query"),
                content=ev.get("content"),
                locator=ev.get("locator"),
                fingerprint=ev.get("fingerprint"),
                tags=ev.get("tags", []),
                provenance=ev.get("provenance"),
                source_resolution_status=ev.get("source_resolution_status", "unresolved_external"),
                provider=ev.get("provider"),
                provider_reference=ev.get("provider_reference")
            )
            for ev in evidence_list
        ]
        self.session.add_all(evidence_objects)
        await self.session.commit()
        return evidence_objects

    async def create_evidence(
        self,
        workspace_id: UUID,
        run_id: UUID,
        content: str,
        task_id: Optional[UUID] = None,
        source_id: Optional[UUID] = None,
        retriever: Optional[str] = None,
        query: Optional[str] = None,
        locator: Optional[str] = None,
        fingerprint: Optional[str] = None,
        tags: Optional[List[str]] = None,
        provenance: Optional[dict] = None,
        source_resolution_status: str = "unresolved_external",
        provider: Optional[str] = None,
        provider_reference: Optional[dict] = None
    ) -> ResearchEvidence:
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
            provenance=provenance,
            source_resolution_status=source_resolution_status,
            provider=provider,
            provider_reference=provider_reference
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
    async def checkpoint_usage(self, workspace_id: UUID, run_id: UUID, usage_metrics: dict) -> ResearchUsage:
        """
        Persists usage metrics to the database as a periodic checkpoint.
        """
        await self._verify_run_workspace(run_id, workspace_id)

        usage = ResearchUsage(
            run_id=run_id,
            task_id=None,
            model_calls=usage_metrics.get('model_calls', 0),
            input_tokens=usage_metrics.get('input_tokens', 0),
            output_tokens=usage_metrics.get('output_tokens', 0),
            retrieval_calls=usage_metrics.get('retrieval_calls', 0),
            search_calls=usage_metrics.get('search_calls', 0),
            mcp_calls=usage_metrics.get('mcp_calls', 0),
            latency=usage_metrics.get('latency', 0.0),
            cost=usage_metrics.get('cost', 0.0),
            estimation_type="periodic_checkpoint"
        )
        self.session.add(usage)
        await self.session.commit()
        await self.session.refresh(usage)
        return usage

    async def create_usage(
        self,
        workspace_id: UUID,
        run_id: UUID,
        task_id: Optional[UUID] = None,
        model_calls: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        retrieval_calls: int = 0,
        search_calls: int = 0,
        mcp_calls: int = 0,
        latency: float = 0.0,
        cost: float = 0.0,
        estimation_type: str = "exact"
    ) -> ResearchUsage:
        """
        Records a usage entry for a research run.
        """
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

        # Calculate next sequence number for the run
        result = await self.session.execute(
            select(func.coalesce(func.max(ResearchEvent.sequence), 0)).where(ResearchEvent.run_id == run_id)
        )
        next_sequence = result.scalar() + 1

        event = ResearchEvent(
            run_id=run_id,
            task_id=task_id,
            event_type=event_type,
            sequence=next_sequence,
            payload=payload
        )
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)

        # Publish to Redis Pub/Sub
        if self.redis_client:
            channel = f"research_events:{run_id}"
            await self.redis_client.publish(
                channel,
                json.dumps({
                    "run_id": str(run_id),
                    "event_type": event_type,
                    "sequence": next_sequence,
                    "payload": payload
                })
            )

        return event

    async def get_events_for_run(self, workspace_id: UUID, run_id: UUID) -> List[ResearchEvent]:
        await self._verify_run_workspace(run_id, workspace_id)
        stmt = select(ResearchEvent).where(ResearchEvent.run_id == run_id).order_by(ResearchEvent.created_at.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
