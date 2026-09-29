import asyncio
import json
import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.workspace import Workspace
from app.models.conversation import Conversation, ConversationTurn
from app.models.research import ResearchRun, ResearchReport, ResearchArtifact
from app.models.knowledge import KnowledgeMemory
from app.repositories.research import ResearchRepository
from app.repositories.knowledge import KnowledgeRepository
from app.services.research.promotion import PromotionService, InvalidLifecycleTransitionError
from app.services.chat.context import build_research_context, ResearchContext


@pytest.mark.asyncio
async def test_research_candidate_acceptance_materializes_memory_and_enables_ingestion():
    """
    E2E Test: Research turn -> candidate in pending_review -> acceptance materializes KnowledgeMemory
    -> subsequent Research turn ingests the approved memory into its context manifest.
    """
    workspace_id = uuid4()
    owner_id = uuid4()
    run_id = uuid4()
    artifact_id = uuid4()
    conv_id = uuid4()

    mock_session = AsyncMock()
    mock_research_repo = AsyncMock()
    mock_memory_repo = AsyncMock()
    mock_derivation = AsyncMock()
    mock_arq = AsyncMock()

    # 1. Candidate emitted by research run in pending_review
    candidate_payload = {
        "candidate_type": "memory_candidate",
        "proposed_memory_type": "research_memory",
        "content": "Superconducting critical temperature reached at 295K under 1.2 GPa pressure.",
        "evidence_refs": [],
        "source_refs": [],
        "provenance_version": "v2",
        "provenance": {
            "source_type": "research_run",
            "source_id": str(run_id),
            "derived_from": []
        }
    }
    candidate = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=run_id,
        type="memory_candidate",
        promotion_status="pending_review",
        payload=candidate_payload,
        created_at=datetime.now(timezone.utc)
    )

    mock_research_repo.get_candidate_for_review.return_value = candidate

    # Mock materialization of KnowledgeMemory
    knowledge_id = uuid4()
    materialized_memory = KnowledgeMemory(
        knowledge_id=knowledge_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        content=candidate_payload["content"],
        domain="deep_research",
        status="active"
    )

    promotion_svc = PromotionService(
        session=mock_session,
        research_repo=mock_research_repo,
        memory_repo=mock_memory_repo,
        derivation_service=mock_derivation,
        arq_pool=mock_arq
    )

    # Patch materialize_memory_candidate to return our model
    with patch.object(promotion_svc, "materialize_memory_candidate", AsyncMock(return_value=materialized_memory)):
        accepted_artifact, target_id = await promotion_svc.accept_candidate(
            workspace_id=workspace_id,
            artifact_id=artifact_id,
            user_id=owner_id
        )

        # Verify acceptance state transitions
        assert accepted_artifact.promotion_status == "accepted"
        assert accepted_artifact.reviewed_by == owner_id
        assert accepted_artifact.promoted_target_type == "knowledge_memory"
        assert target_id == knowledge_id
        assert accepted_artifact.promoted_target_id == knowledge_id

        # Verify background sync job enqueued
        mock_arq.enqueue_job.assert_awaited_with(
            "sync_knowledge_to_graph_job",
            knowledge_id=str(knowledge_id)
        )

    # 2. Subsequent Research turn ingests the accepted KnowledgeMemory
    def db_execute_side_effect(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt).lower()
        if "knowledge_memories" in stmt_str:
            mock_result.scalars.return_value.all.return_value = [materialized_memory]
        elif "conversation_turns" in stmt_str:
            mock_result.scalars.return_value.all.return_value = []
        elif "scratchpad_entries" in stmt_str:
            mock_result.scalars.return_value.all.return_value = []
        elif "research_evidence" in stmt_str:
            mock_result.scalars.return_value.all.return_value = []
        else:
            mock_result.scalars.return_value.all.return_value = []
            mock_result.scalars.return_value.first.return_value = None
        return mock_result

    mock_session.execute.side_effect = db_execute_side_effect

    subsequent_research_ctx: ResearchContext = await build_research_context(
        session=mock_session,
        workspace_id=workspace_id,
        conversation_id=conv_id,
        query="What was our previously accepted finding on superconducting critical temperatures?",
        token_budget=8000
    )

    # Assert that approved KnowledgeMemory is present in research context
    assert len(subsequent_research_ctx.knowledge_memories) == 1
    accepted_mem_entry = subsequent_research_ctx.knowledge_memories[0]
    assert "Superconducting critical temperature reached at 295K" in accepted_mem_entry["content"]
    assert str(knowledge_id) == accepted_mem_entry["knowledge_id"]

    # Assert that manifest records the item as included
    manifest_included = [item.item_id for item in subsequent_research_ctx.context_version.included_items]
    assert str(knowledge_id) in manifest_included


@pytest.mark.asyncio
async def test_research_candidate_rejection_preserves_audit_without_materialization():
    """
    E2E Test: Candidate rejection records reviewer, timestamp, and reason,
    guaranteeing zero KnowledgeMemory materialization and immutable audit history.
    """
    workspace_id = uuid4()
    owner_id = uuid4()
    artifact_id = uuid4()

    mock_session = AsyncMock()
    mock_research_repo = AsyncMock()
    mock_memory_repo = AsyncMock()

    candidate = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=uuid4(),
        type="memory_candidate",
        promotion_status="pending_review",
        payload={"content": "Unverified claims without supporting lab evidence."},
        created_at=datetime.now(timezone.utc)
    )
    mock_research_repo.get_candidate_for_review.return_value = candidate

    promotion_svc = PromotionService(
        session=mock_session,
        research_repo=mock_research_repo,
        memory_repo=mock_memory_repo
    )

    rejected_candidate = await promotion_svc.reject_candidate(
        workspace_id=workspace_id,
        artifact_id=artifact_id,
        user_id=owner_id,
        reason="Insufficient experimental evidence to substantiate findings."
    )

    # 1. State assertions
    assert rejected_candidate.promotion_status == "rejected"
    assert rejected_candidate.reviewed_by == owner_id
    assert rejected_candidate.review_reason == "Insufficient experimental evidence to substantiate findings."
    assert rejected_candidate.promoted_target_id is None
    assert rejected_candidate.promoted_target_type is None

    # 2. Immutable transition: cannot accept a rejected candidate
    with pytest.raises(InvalidLifecycleTransitionError, match="cannot be accepted"):
        await promotion_svc.accept_candidate(
            workspace_id=workspace_id,
            artifact_id=artifact_id,
            user_id=owner_id
        )


@pytest.mark.asyncio
async def test_dual_target_independence_memory_and_graph_candidates():
    """
    E2E Test: A single research run emitting both a memory_candidate and a graph_candidate.
    Promoting one candidate must never mutate, close, or auto-promote the other.
    """
    workspace_id = uuid4()
    user_id = uuid4()
    run_id = uuid4()

    mem_artifact_id = uuid4()
    graph_artifact_id = uuid4()

    mock_session = AsyncMock()
    mock_research_repo = AsyncMock()
    mock_arq = AsyncMock()

    mem_candidate = ResearchArtifact(
        artifact_id=mem_artifact_id,
        run_id=run_id,
        type="memory_candidate",
        promotion_status="pending_review",
        payload={"content": "Independent memory candidate finding."}
    )

    graph_candidate = ResearchArtifact(
        artifact_id=graph_artifact_id,
        run_id=run_id,
        type="graph_candidate",
        promotion_status="pending_review",
        payload={
            "nodes": [{"id": "n1", "label": "ConceptA"}],
            "edges": []
        }
    )

    def get_candidate_mock(ws_id, a_id):
        if a_id == mem_artifact_id:
            return mem_candidate
        elif a_id == graph_artifact_id:
            return graph_candidate
        return None

    mock_research_repo.get_candidate_for_review.side_effect = get_candidate_mock

    promotion_svc = PromotionService(
        session=mock_session,
        research_repo=mock_research_repo,
        arq_pool=mock_arq
    )

    mem_target_id = uuid4()
    mock_mem = KnowledgeMemory(knowledge_id=mem_target_id, workspace_id=workspace_id, owner_id=user_id)

    # Accept memory_candidate only
    with patch.object(promotion_svc, "materialize_memory_candidate", AsyncMock(return_value=mock_mem)):
        await promotion_svc.accept_candidate(workspace_id, mem_artifact_id, user_id)

    # Verify memory_candidate is accepted
    assert mem_candidate.promotion_status == "accepted"
    assert mem_candidate.promoted_target_id == mem_target_id

    # Verify graph_candidate remains strictly in pending_review
    assert graph_candidate.promotion_status == "pending_review"
    assert graph_candidate.promoted_target_id is None

    # Now accept graph_candidate
    with patch.object(promotion_svc, "materialize_graph_candidate", AsyncMock(return_value=graph_candidate.payload)):
        await promotion_svc.accept_candidate(workspace_id, graph_artifact_id, user_id)

    assert graph_candidate.promotion_status == "accepted"
    assert graph_candidate.promoted_target_type == "output_graph"
    assert graph_candidate.promoted_target_id == graph_artifact_id
    mock_arq.enqueue_job.assert_awaited_with(
        "project_output_graph_job",
        workspace_id=str(workspace_id),
        graph_dict=graph_candidate.payload
    )
