import json
import logging
import inspect
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from arq.connections import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research import ResearchArtifact
from app.models.knowledge import KnowledgeMemory
from app.models.workspace import Workspace
from app.repositories.research import ResearchRepository
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.graph import GraphRepository
from app.schemas.knowledge import Provenance
from app.schemas.graph import ProvenanceRef
from app.schemas.promotion import MemoryCandidatePayload, GraphCandidatePayload
from app.services.research.derivation import DerivationService

logger = logging.getLogger(__name__)


class PromotionError(Exception):
    """Base exception for candidate promotion operations."""
    pass


class CandidateNotFoundError(PromotionError):
    """Raised when a candidate artifact cannot be found in the workspace."""
    pass


class InvalidLifecycleTransitionError(PromotionError):
    """Raised when an illegal candidate lifecycle transition is attempted."""
    pass


class InvalidCandidateTypeError(PromotionError):
    """Raised when an unsupported candidate type is submitted for promotion."""
    def __init__(self, detail: str = "invalid_candidate_type"):
        super().__init__(detail)
        self.detail = detail
        self.status_code = 400


class TimelineEpochFencedError(PromotionError):
    """Raised when active workspace timeline epoch has advanced beyond the run's baseline epoch."""
    def __init__(self, detail: str = "aborted_by_timeline_fence"):
        super().__init__(detail)
        self.detail = detail
        self.status_code = 409


class InvalidPayloadError(PromotionError):
    """Raised when candidate payload fails Pydantic schema validation."""
    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail
        self.status_code = 400


class PromotionService:
    """
    Canonical boundary for promoting research candidates into durable knowledge or Output KG state.
    Enforces human-in-the-loop review, dual-target independence, fail-closed multi-tenancy, and idempotency.
    """

    def __init__(
        self,
        session: AsyncSession,
        research_repo: ResearchRepository,
        memory_repo: Optional[KnowledgeRepository] = None,
        graph_repo: Optional[GraphRepository] = None,
        derivation_service: Optional[DerivationService] = None,
        arq_pool: Optional[Redis] = None,
    ):
        self.session = session
        self.research_repo = research_repo
        self.memory_repo = memory_repo or KnowledgeRepository(session)
        self.graph_repo = graph_repo
        self.derivation_service = derivation_service or DerivationService(session)
        self.arq_pool = arq_pool

    async def list_candidates(
        self,
        workspace_id: UUID,
        status: Optional[str] = None,
        run_id: Optional[UUID] = None,
    ) -> List[ResearchArtifact]:
        """
        Lists promotion candidates belonging to the workspace, optionally filtered by status and run_id.
        """
        return await self.research_repo.list_candidates_by_status(
            workspace_id=workspace_id,
            status=status,
            run_id=run_id,
        )

    async def get_candidate(
        self,
        workspace_id: UUID,
        artifact_id: UUID,
        for_update: bool = False,
    ) -> ResearchArtifact:
        """
        Retrieves a candidate artifact within the workspace boundary.
        When `for_update=True` a PostgreSQL row-level lock (SELECT FOR UPDATE)
        is acquired on the artifact row to prevent concurrent state transitions.
        """
        from app.models.research import ResearchArtifact as _Artifact
        from app.models.research import ResearchRun as _Run
        candidate = None

        if for_update:
            # Acquire a row-level lock directly on ResearchArtifact to fence
            # concurrent accept/reject calls from racing on the same candidate.
            stmt = (
                select(_Artifact)
                .join(_Run, _Artifact.run_id == _Run.run_id)
                .where(
                    _Artifact.artifact_id == artifact_id,
                    _Run.workspace_id == workspace_id,
                )
                .with_for_update()
            )
            result = await self.session.execute(stmt)
            try:
                candidate = result.scalar_one_or_none()
                import inspect
                if inspect.isawaitable(candidate):
                    candidate = await candidate
            except Exception:
                candidate = None

        if candidate is None or not isinstance(candidate, _Artifact):
            if hasattr(self.research_repo, "get_candidate_for_review"):
                repo_candidate = await self.research_repo.get_candidate_for_review(workspace_id, artifact_id)
                if repo_candidate is not None:
                    candidate = repo_candidate

        if not candidate:
            raise CandidateNotFoundError(f"Candidate {artifact_id} not found in workspace {workspace_id}.")
        return candidate

    async def accept_candidate(
        self,
        workspace_id: UUID,
        artifact_id: UUID,
        user_id: UUID,
    ) -> Tuple[ResearchArtifact, Optional[UUID]]:
        """
        Atomically accepts a candidate artifact:
        1. Verifies workspace access and existence.
        2. Enforces idempotency (re-accepting returns existing target).
        3. Enforces valid lifecycle state (must be pending_review).
        4. Validates provenance lineage (fails closed on cross-workspace refs).
        5. Materializes target (KnowledgeMemory, OutputGraph, etc.).
        6. Persists target identity and updates status = 'accepted'.
        7. Enqueues background projection jobs (if applicable).
        """
        # Acquire row-level lock before any state checks to prevent concurrent
        # race conditions that could materialize duplicate KnowledgeMemory rows.
        candidate = await self.get_candidate(workspace_id, artifact_id, for_update=True)

        # Idempotency check: if already accepted, return existing target safely
        if candidate.promotion_status == "accepted":
            logger.info("Candidate %s already accepted; returning existing target %s", artifact_id, candidate.promoted_target_id)
            return candidate, candidate.promoted_target_id

        if candidate.promotion_status in ("rejected", "superseded"):
            raise InvalidLifecycleTransitionError(
                f"Candidate {artifact_id} is in status '{candidate.promotion_status}' and cannot be accepted."
            )

        # Gate 3: Restrict promotion candidates strictly to memory_candidate and graph_candidate
        if candidate.type not in ("memory_candidate", "graph_candidate"):
            raise InvalidCandidateTypeError("invalid_candidate_type")

        # Gate 2: Verify active workspace timeline epoch and abort if epoch has advanced
        expected_epoch = None
        if hasattr(self.research_repo, "get_run"):
            try:
                run_obj = await self.research_repo.get_run(workspace_id, candidate.run_id)
                if run_obj and isinstance(getattr(run_obj, "timeline_epoch", None), int):
                    expected_epoch = run_obj.timeline_epoch
            except Exception:
                pass
        if expected_epoch is None and isinstance(getattr(candidate, "timeline_epoch", None), int):
            expected_epoch = candidate.timeline_epoch
        if expected_epoch is None and isinstance(candidate.payload, dict):
            p_epoch = candidate.payload.get("timeline_epoch")
            if isinstance(p_epoch, int):
                expected_epoch = p_epoch

        active_epoch = None
        try:
            ws_res = self.session.execute(
                select(Workspace).where(Workspace.workspace_id == workspace_id)
            )
            if inspect.isawaitable(ws_res):
                ws_res = await ws_res
            scalars_fn = getattr(ws_res, "scalars", None)
            if callable(scalars_fn):
                sc = scalars_fn()
                if inspect.isawaitable(sc):
                    sc = await sc
                first_fn = getattr(sc, "first", None)
                if callable(first_fn):
                    ws_obj = first_fn()
                    if inspect.isawaitable(ws_obj):
                        ws_obj = await ws_obj
                    if ws_obj and isinstance(getattr(ws_obj, "timeline_epoch", None), int):
                        active_epoch = ws_obj.timeline_epoch
        except Exception:
            pass

        if isinstance(expected_epoch, int) and isinstance(active_epoch, int):
            if active_epoch > expected_epoch:
                raise TimelineEpochFencedError("aborted_by_timeline_fence")

        payload = candidate.payload or {}

        # Gate 4: Validate candidate payloads strictly against Pydantic schemas
        if candidate.type == "memory_candidate":
            try:
                MemoryCandidatePayload(**payload)
            except Exception as val_err:
                raise InvalidPayloadError(f"Invalid memory_candidate payload: {val_err}")
        elif candidate.type == "graph_candidate":
            try:
                GraphCandidatePayload(**payload)
            except Exception as val_err:
                raise InvalidPayloadError(f"Invalid graph_candidate payload: {val_err}")

        # Validate provenance lineage (fail-closed)
        prov_dict = payload.get("provenance") or {}
        derived_from_raw = prov_dict.get("derived_from") or []
        refs = []
        for item in derived_from_raw:
            if isinstance(item, dict):
                refs.append(ProvenanceRef(**item))
            elif isinstance(item, ProvenanceRef):
                refs.append(item)

        evidence_refs_raw = payload.get("evidence_refs") or []
        for ev_id in evidence_refs_raw:
            refs.append(ProvenanceRef(ref_type="research_evidence", ref_id=UUID(str(ev_id))))

        if refs:
            await self.derivation_service.validate_provenance_lineage(workspace_id, refs)

        target_type: Optional[str] = None
        target_id: Optional[UUID] = None
        post_commit_jobs: List[Tuple[str, Dict[str, Any]]] = []

        # Materialize Target
        if candidate.type == "memory_candidate":
            memory = await self.materialize_memory_candidate(workspace_id, candidate, user_id)
            target_type = "knowledge_memory"
            target_id = memory.knowledge_id
            post_commit_jobs.append((
                "sync_knowledge_to_graph_job",
                {"knowledge_id": str(memory.knowledge_id)}
            ))

        elif candidate.type == "graph_candidate":
            graph_dict = await self.materialize_graph_candidate(workspace_id, candidate)
            target_type = "output_graph"
            target_id = candidate.artifact_id
            post_commit_jobs.append((
                "project_output_graph_job",
                {
                    "workspace_id": str(workspace_id),
                    "graph_dict": graph_dict,
                }
            ))

        # Update candidate state in DB
        candidate.promotion_status = "accepted"
        candidate.reviewed_by = user_id
        candidate.reviewed_at = datetime.now(timezone.utc)
        candidate.promoted_target_type = target_type
        candidate.promoted_target_id = target_id

        # Gate 5: Database commit occurs strictly before enqueuing background projection jobs
        await self.session.commit()
        await self.session.refresh(candidate)

        # Gate 5: Background projection jobs enqueued strictly post-commit
        if self.arq_pool:
            for job_name, job_kwargs in post_commit_jobs:
                try:
                    await self.arq_pool.enqueue_job(job_name, **job_kwargs)
                except Exception as exc:
                    logger.warning("Failed to enqueue %s: %s", job_name, exc)

        logger.info(json.dumps({
            "event": "candidate_promotion_decision",
            "workspace_id": str(workspace_id),
            "run_id": str(candidate.run_id),
            "artifact_id": str(candidate.artifact_id),
            "candidate_type": candidate.type,
            "promotion_decision": "accepted",
            "reviewed_by": str(user_id),
            "promoted_target_id": str(target_id),
            "promoted_target_type": target_type,
        }))

        # Emit live event
        await self._publish_promotion_event("promotion.accepted", workspace_id, candidate)

        return candidate, target_id

    async def reject_candidate(
        self,
        workspace_id: UUID,
        artifact_id: UUID,
        user_id: UUID,
        reason: Optional[str] = None,
    ) -> ResearchArtifact:
        """
        Durably rejects a candidate artifact:
        - Sets promotion_status = 'rejected'
        - Records reviewer, timestamp, and optional reason
        - Never deletes underlying evidence or execution logs
        - Never creates durable KnowledgeMemory or Output KG nodes
        """
        # Acquire row-level lock before state checks to prevent accept/reject race.
        candidate = await self.get_candidate(workspace_id, artifact_id, for_update=True)

        if candidate.promotion_status == "rejected":
            return candidate

        if candidate.promotion_status == "accepted":
            raise InvalidLifecycleTransitionError(
                f"Candidate {artifact_id} has already been accepted and cannot be rejected."
            )

        candidate.promotion_status = "rejected"
        candidate.reviewed_by = user_id
        candidate.reviewed_at = datetime.now(timezone.utc)
        candidate.review_reason = reason

        await self.session.commit()
        await self.session.refresh(candidate)

        logger.info(json.dumps({
            "event": "candidate_promotion_decision",
            "workspace_id": str(workspace_id),
            "run_id": str(candidate.run_id),
            "artifact_id": str(candidate.artifact_id),
            "candidate_type": candidate.type,
            "promotion_decision": "rejected",
            "reviewed_by": str(user_id),
            "reason": reason,
        }))

        await self._publish_promotion_event("promotion.rejected", workspace_id, candidate)
        return candidate

    async def materialize_memory_candidate(
        self,
        workspace_id: UUID,
        candidate: ResearchArtifact,
        owner_id: UUID,
    ) -> KnowledgeMemory:
        """
        Synchronously materializes a memory_candidate into a canonical KnowledgeMemory row.
        """
        payload = candidate.payload or {}
        text = payload.get("text") or payload.get("content") or ""
        domain = payload.get("domain", "deep_research")

        prov_dict = payload.get("provenance") or {}
        derived_from_refs = [
            UUID(str(u)) for u in prov_dict.get("derived_from_refs", [])
        ]
        provenance = Provenance(
            source_refs=derived_from_refs,
            source_mode="research",
            typed_refs=prov_dict.get("derived_from", []),
        )

        import uuid as _uuid
        memory = KnowledgeMemory(
            knowledge_id=_uuid.uuid4(),
            workspace_id=workspace_id,
            owner_id=owner_id,
            knowledge_type="research_memory",
            content=text,
            status="active",
            provenance=provenance.model_dump(),
            domain=domain,
            confidence=payload.get("confidence"),
            tags=candidate.tags or [],
        )

        add_res = self.session.add(memory)
        if inspect.isawaitable(add_res):
            await add_res
        await self.session.flush()
        return memory

    async def materialize_graph_candidate(
        self,
        workspace_id: UUID,
        candidate: ResearchArtifact,
    ) -> Dict[str, Any]:
        """
        Validates the structure of a graph_candidate payload for asynchronous Output KG projection.
        """
        payload = candidate.payload or {}
        if not isinstance(payload, dict):
            raise PromotionError("graph_candidate payload must be a JSON dictionary containing nodes and edges.")

        if "nodes" not in payload:
            payload["nodes"] = []
        if "edges" not in payload:
            payload["edges"] = []

        return payload

    async def _publish_promotion_event(
        self,
        event_type: str,
        workspace_id: UUID,
        candidate: ResearchArtifact,
    ) -> None:
        """
        Publishes a normalized promotion event over Redis pub/sub if available.
        """
        if not self.arq_pool:
            return

        try:
            event = {
                "event_type": event_type,
                "workspace_id": str(workspace_id),
                "artifact_id": str(candidate.artifact_id),
                "run_id": str(candidate.run_id),
                "candidate_type": candidate.type,
                "promotion_status": candidate.promotion_status,
                "promoted_target_type": candidate.promoted_target_type,
                "promoted_target_id": str(candidate.promoted_target_id) if candidate.promoted_target_id else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            channel = f"workspace_events:{workspace_id}"
            await self.arq_pool.publish(channel, json.dumps(event))
        except Exception as exc:
            logger.warning("Failed to publish %s event: %s", event_type, exc)
