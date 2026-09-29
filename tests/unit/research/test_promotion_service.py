import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.models.research import ResearchArtifact
from app.repositories.research import ResearchRepository
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.graph import GraphRepository
from app.services.research.derivation import DerivationService, CrossWorkspaceBoundaryError
from app.services.research.promotion import (
    PromotionService,
    CandidateNotFoundError,
    InvalidLifecycleTransitionError,
)
from app.schemas.graph import ProvenanceRef


@pytest.mark.asyncio
async def test_accept_memory_candidate_creates_memory_and_enqueues_sync():
    workspace_id = uuid4()
    artifact_id = uuid4()
    run_id = uuid4()
    user_id = uuid4()

    mock_artifact = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=run_id,
        type="memory_candidate",
        payload={
            "text": "Distinctive synthesized fact",
            "domain": "materials_science",
            "confidence": 0.95,
            "provenance": {"derived_from_refs": [str(uuid4())]}
        },
        promotion_status="pending_review",
        created_at=datetime.now(timezone.utc)
    )

    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    research_repo = MagicMock(spec=ResearchRepository)
    research_repo.get_candidate_for_review = AsyncMock(return_value=mock_artifact)

    arq_pool = AsyncMock()
    arq_pool.enqueue_job = AsyncMock()
    arq_pool.publish = AsyncMock()

    derivation_svc = MagicMock(spec=DerivationService)
    derivation_svc.validate_provenance_lineage = AsyncMock(return_value=True)

    service = PromotionService(
        session=session,
        research_repo=research_repo,
        derivation_service=derivation_svc,
        arq_pool=arq_pool
    )

    candidate, target_id = await service.accept_candidate(workspace_id, artifact_id, user_id)

    assert candidate.promotion_status == "accepted"
    assert candidate.promoted_target_type == "knowledge_memory"
    assert target_id is not None
    assert candidate.promoted_target_id == target_id
    assert candidate.reviewed_by == user_id
    assert session.add.called
    assert session.commit.called
    assert arq_pool.enqueue_job.called
    assert arq_pool.enqueue_job.call_args[0][0] == "sync_knowledge_to_graph_job"


@pytest.mark.asyncio
async def test_accept_candidate_idempotent():
    workspace_id = uuid4()
    artifact_id = uuid4()
    run_id = uuid4()
    user_id = uuid4()
    existing_target_id = uuid4()

    mock_artifact = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=run_id,
        type="memory_candidate",
        payload={"text": "Already accepted fact"},
        promotion_status="accepted",
        promoted_target_type="knowledge_memory",
        promoted_target_id=existing_target_id,
        created_at=datetime.now(timezone.utc)
    )

    session = AsyncMock()
    research_repo = MagicMock(spec=ResearchRepository)
    research_repo.get_candidate_for_review = AsyncMock(return_value=mock_artifact)

    service = PromotionService(
        session=session,
        research_repo=research_repo
    )

    candidate, target_id = await service.accept_candidate(workspace_id, artifact_id, user_id)

    assert candidate.promotion_status == "accepted"
    assert target_id == existing_target_id
    assert not session.add.called


@pytest.mark.asyncio
async def test_accept_graph_candidate_enqueues_projection_job():
    workspace_id = uuid4()
    artifact_id = uuid4()
    run_id = uuid4()
    user_id = uuid4()

    graph_payload = {
        "nodes": [{"id": "n1", "label": "Concept", "properties": {"name": "Graphene"}}],
        "edges": [{"source_id": "n1", "target_id": "n2", "type": "RELATES_TO"}]
    }

    mock_artifact = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=run_id,
        type="graph_candidate",
        payload=graph_payload,
        promotion_status="pending_review",
        created_at=datetime.now(timezone.utc)
    )

    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    research_repo = MagicMock(spec=ResearchRepository)
    research_repo.get_candidate_for_review = AsyncMock(return_value=mock_artifact)

    arq_pool = AsyncMock()
    arq_pool.enqueue_job = AsyncMock()
    arq_pool.publish = AsyncMock()

    service = PromotionService(
        session=session,
        research_repo=research_repo,
        arq_pool=arq_pool
    )

    candidate, target_id = await service.accept_candidate(workspace_id, artifact_id, user_id)

    assert candidate.promotion_status == "accepted"
    assert candidate.promoted_target_type == "output_graph"
    assert not session.add.called  # Zero KnowledgeMemory added for graph candidate
    assert arq_pool.enqueue_job.called
    assert arq_pool.enqueue_job.call_args[0][0] == "project_output_graph_job"


@pytest.mark.asyncio
async def test_reject_candidate_durably_records_audit():
    workspace_id = uuid4()
    artifact_id = uuid4()
    run_id = uuid4()
    user_id = uuid4()

    mock_artifact = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=run_id,
        type="memory_candidate",
        payload={"text": "Unverified assertion"},
        promotion_status="pending_review",
        created_at=datetime.now(timezone.utc)
    )

    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    research_repo = MagicMock(spec=ResearchRepository)
    research_repo.get_candidate_for_review = AsyncMock(return_value=mock_artifact)

    service = PromotionService(
        session=session,
        research_repo=research_repo
    )

    rejected = await service.reject_candidate(
        workspace_id=workspace_id,
        artifact_id=artifact_id,
        user_id=user_id,
        reason="Methodology unreplicable"
    )

    assert rejected.promotion_status == "rejected"
    assert rejected.reviewed_by == user_id
    assert rejected.review_reason == "Methodology unreplicable"
    assert rejected.promoted_target_id is None
    assert session.commit.called


@pytest.mark.asyncio
async def test_reject_accepted_candidate_raises_error():
    workspace_id = uuid4()
    artifact_id = uuid4()
    user_id = uuid4()

    mock_artifact = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=uuid4(),
        type="memory_candidate",
        payload={"text": "Already accepted"},
        promotion_status="accepted"
    )

    session = AsyncMock()
    research_repo = MagicMock(spec=ResearchRepository)
    research_repo.get_candidate_for_review = AsyncMock(return_value=mock_artifact)

    service = PromotionService(session=session, research_repo=research_repo)

    with pytest.raises(InvalidLifecycleTransitionError, match="cannot be rejected"):
        await service.reject_candidate(workspace_id, artifact_id, user_id)


@pytest.mark.asyncio
async def test_accept_candidate_fails_closed_on_cross_workspace_provenance():
    workspace_id = uuid4()
    artifact_id = uuid4()
    user_id = uuid4()
    foreign_ev_id = uuid4()

    mock_artifact = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=uuid4(),
        type="memory_candidate",
        payload={
            "text": "Fact derived from another workspace evidence",
            "evidence_refs": [str(foreign_ev_id)]
        },
        promotion_status="pending_review"
    )

    session = AsyncMock()
    research_repo = MagicMock(spec=ResearchRepository)
    research_repo.get_candidate_for_review = AsyncMock(return_value=mock_artifact)

    derivation_svc = MagicMock(spec=DerivationService)
    derivation_svc.validate_provenance_lineage = AsyncMock(
        side_effect=CrossWorkspaceBoundaryError("Evidence belongs to foreign workspace")
    )

    service = PromotionService(
        session=session,
        research_repo=research_repo,
        derivation_service=derivation_svc
    )

    with pytest.raises(CrossWorkspaceBoundaryError, match="foreign workspace"):
        await service.accept_candidate(workspace_id, artifact_id, user_id)
