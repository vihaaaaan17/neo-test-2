import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.models.research import ResearchArtifact
from app.models.knowledge import KnowledgeMemory
from app.services.research.promotion import (
    PromotionService,
    CandidateNotFoundError,
    InvalidLifecycleTransitionError,
)
from app.services.research.derivation import CrossWorkspaceBoundaryError


@pytest.mark.asyncio
async def test_candidate_creation_with_pending_review_status():
    """
    Research candidate artifacts are initially created with 'pending_review' status.
    """
    artifact = ResearchArtifact(
        artifact_id=uuid4(),
        run_id=uuid4(),
        type="memory_candidate",
        payload={"claim": "Initial claim", "text": "Some text"},
        promotion_status="pending_review"
    )

    assert artifact.promotion_status == "pending_review"
    assert artifact.reviewed_by is None
    assert artifact.reviewed_at is None
    assert artifact.promoted_target_id is None


@pytest.mark.asyncio
async def test_accept_memory_candidate_creates_single_knowledge_memory():
    """
    Accepting a memory_candidate creates exactly one KnowledgeMemory record,
    sets candidate promotion_status to 'accepted', and populates audit fields.
    """
    workspace_id = uuid4()
    artifact_id = uuid4()
    user_id = uuid4()
    run_id = uuid4()

    mock_candidate = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=run_id,
        type="memory_candidate",
        payload={
            "text": "Critical observation on superconductors",
            "provenance": {"sources": [{"type": "source", "id": str(uuid4())}]}
        },
        promotion_status="pending_review"
    )

    session = AsyncMock()
    session.add = MagicMock()
    repo = MagicMock()
    repo.get_candidate_for_review = AsyncMock(return_value=mock_candidate)

    derivation_svc = MagicMock()
    derivation_svc.validate_provenance_lineage = AsyncMock(return_value=True)

    arq_pool = AsyncMock()
    promo_svc = PromotionService(
        session=session,
        research_repo=repo,
        derivation_service=derivation_svc,
        arq_pool=arq_pool
    )

    candidate, target_id = await promo_svc.accept_candidate(workspace_id, artifact_id, user_id)

    assert candidate.promotion_status == "accepted"
    assert candidate.reviewed_by == user_id
    assert candidate.promoted_target_type == "knowledge_memory"
    assert target_id is not None
    assert candidate.promoted_target_id == target_id

    # Verify KnowledgeMemory was added to session and synced
    assert session.add.called
    assert session.commit.called
    arq_pool.enqueue_job.assert_awaited_once()


@pytest.mark.asyncio
async def test_reject_candidate_durably_records_audit():
    """
    Rejecting a candidate sets promotion_status to 'rejected', records reviewer and reason,
    and commits without creating durable memory or graph entities.
    """
    workspace_id = uuid4()
    artifact_id = uuid4()
    user_id = uuid4()
    run_id = uuid4()

    mock_candidate = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=run_id,
        type="memory_candidate",
        payload={"text": "Unverified claim"},
        promotion_status="pending_review"
    )

    session = AsyncMock()
    repo = MagicMock()
    repo.get_candidate_for_review = AsyncMock(return_value=mock_candidate)

    promo_svc = PromotionService(
        session=session,
        research_repo=repo,
        arq_pool=AsyncMock()
    )

    candidate = await promo_svc.reject_candidate(
        workspace_id,
        artifact_id,
        user_id,
        reason="Claim lacked empirical backing"
    )

    assert candidate.promotion_status == "rejected"
    assert candidate.reviewed_by == user_id
    assert candidate.review_reason == "Claim lacked empirical backing"
    assert candidate.promoted_target_id is None
    # session.add should NOT have been called (no KnowledgeMemory created)
    assert not session.add.called
    assert session.commit.called


@pytest.mark.asyncio
async def test_accept_candidate_is_strictly_idempotent():
    """
    Re-accepting an already accepted candidate returns the existing candidate
    and promoted_target_id without creating duplicate records.
    """
    workspace_id = uuid4()
    artifact_id = uuid4()
    user_id = uuid4()
    existing_target_id = uuid4()

    mock_candidate = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=uuid4(),
        type="memory_candidate",
        payload={"text": "Already accepted"},
        promotion_status="accepted",
        promoted_target_type="KnowledgeMemory",
        promoted_target_id=existing_target_id,
        reviewed_by=user_id
    )

    session = AsyncMock()
    repo = MagicMock()
    repo.get_candidate_for_review = AsyncMock(return_value=mock_candidate)

    promo_svc = PromotionService(
        session=session,
        research_repo=repo,
        arq_pool=AsyncMock()
    )

    candidate, target_id = await promo_svc.accept_candidate(workspace_id, artifact_id, user_id)

    assert candidate.promotion_status == "accepted"
    assert target_id == existing_target_id
    # No new object added to session
    assert not session.add.called


@pytest.mark.asyncio
async def test_dual_target_independence():
    """
    Memory candidates and graph candidates are independently controllable.
    Accepting memory does not accept graph, and rejecting graph does not reject memory.
    """
    workspace_id = uuid4()
    mem_art_id = uuid4()
    graph_art_id = uuid4()
    user_id = uuid4()
    run_id = uuid4()

    mem_candidate = ResearchArtifact(
        artifact_id=mem_art_id,
        run_id=run_id,
        type="memory_candidate",
        payload={"text": "Independent memory"},
        promotion_status="pending_review"
    )

    graph_candidate = ResearchArtifact(
        artifact_id=graph_art_id,
        run_id=run_id,
        type="graph_candidate",
        payload={"nodes": [{"id": "n1"}], "edges": []},
        promotion_status="pending_review"
    )

    session = AsyncMock()
    session.add = MagicMock()
    repo = MagicMock()
    repo.get_candidate_for_review = AsyncMock(side_effect=[mem_candidate, graph_candidate])

    derivation_svc = MagicMock()
    derivation_svc.validate_provenance_lineage = AsyncMock(return_value=True)

    promo_svc = PromotionService(
        session=session,
        research_repo=repo,
        derivation_service=derivation_svc,
        arq_pool=AsyncMock()
    )

    # 1. Accept memory candidate
    accepted_mem, mem_target = await promo_svc.accept_candidate(workspace_id, mem_art_id, user_id)
    assert accepted_mem.promotion_status == "accepted"
    assert mem_target is not None

    # 2. Reject graph candidate
    rejected_graph = await promo_svc.reject_candidate(workspace_id, graph_art_id, user_id, reason="Graph too noisy")
    assert rejected_graph.promotion_status == "rejected"
    assert rejected_graph.promoted_target_id is None

    # Memory candidate remains accepted, graph candidate remains rejected
    assert accepted_mem.promotion_status == "accepted"
    assert rejected_graph.promotion_status == "rejected"


@pytest.mark.asyncio
async def test_cross_workspace_candidate_acceptance_rejection():
    """
    Attempting to accept a candidate referencing foreign workspace data fails closed.
    """
    workspace_id = uuid4()
    artifact_id = uuid4()
    user_id = uuid4()

    mock_candidate = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=uuid4(),
        type="memory_candidate",
        payload={
            "text": "Cross-workspace leak attempt",
            "provenance": {
                "derived_from": [{"ref_type": "source", "ref_id": str(uuid4())}]
            }
        },
        promotion_status="pending_review"
    )

    session = AsyncMock()
    repo = MagicMock()
    repo.get_candidate_for_review = AsyncMock(return_value=mock_candidate)

    derivation_svc = MagicMock()
    derivation_svc.validate_provenance_lineage = AsyncMock(
        side_effect=CrossWorkspaceBoundaryError("Cross workspace boundary violated")
    )

    promo_svc = PromotionService(
        session=session,
        research_repo=repo,
        derivation_service=derivation_svc,
        arq_pool=AsyncMock()
    )

    with pytest.raises(CrossWorkspaceBoundaryError):
        await promo_svc.accept_candidate(workspace_id, artifact_id, user_id)

    # Database must NOT be committed
    assert not session.commit.called
