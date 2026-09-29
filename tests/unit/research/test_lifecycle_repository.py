import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.models.research import ResearchArtifact, ResearchRun
from app.repositories.research import ResearchRepository


@pytest.mark.asyncio
async def test_create_artifact_with_candidate_fields():
    workspace_id = uuid4()
    run_id = uuid4()
    artifact_id = uuid4()

    session = AsyncMock()
    session.add = MagicMock()
    mock_run_res = MagicMock()
    mock_run_res.scalar_one_or_none.return_value = ResearchRun(run_id=run_id, workspace_id=workspace_id)
    session.execute.return_value = mock_run_res

    repo = ResearchRepository(session)

    artifact = await repo.create_artifact(
        workspace_id=workspace_id,
        run_id=run_id,
        artifact_type="memory_candidate",
        payload={"text": "Superconductor Tc reaches 150K under 20GPa", "domain": "physics"},
        promotion_status="pending_review",
        verification_status="verified",
        verification_reason={"computed": 150.0, "tolerance": 0.01},
        verification_metadata={"evaluator": "DeterministicArithmeticVerifier"}
    )

    assert artifact.run_id == run_id
    assert artifact.type == "memory_candidate"
    assert artifact.promotion_status == "pending_review"
    assert artifact.verification_status == "verified"
    assert artifact.verification_reason == {"computed": 150.0, "tolerance": 0.01}
    assert session.add.called
    assert session.commit.called


@pytest.mark.asyncio
async def test_list_candidates_by_status():
    workspace_id = uuid4()
    run_id = uuid4()

    session = AsyncMock()
    mock_artifacts = [
        ResearchArtifact(
            artifact_id=uuid4(),
            run_id=run_id,
            type="memory_candidate",
            payload={"text": "Fact A"},
            promotion_status="pending_review",
            created_at=datetime.now(timezone.utc)
        ),
        ResearchArtifact(
            artifact_id=uuid4(),
            run_id=run_id,
            type="graph_candidate",
            payload={"nodes": []},
            promotion_status="pending_review",
            created_at=datetime.now(timezone.utc)
        ),
    ]

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = mock_artifacts
    session.execute.return_value = mock_res

    repo = ResearchRepository(session)
    candidates = await repo.list_candidates_by_status(workspace_id=workspace_id, status="pending_review", run_id=run_id)

    assert len(candidates) == 2
    assert candidates[0].promotion_status == "pending_review"
    assert candidates[1].promotion_status == "pending_review"
    assert session.execute.called


@pytest.mark.asyncio
async def test_get_candidate_for_review_found():
    workspace_id = uuid4()
    artifact_id = uuid4()
    run_id = uuid4()

    mock_artifact = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=run_id,
        type="finding_candidate",
        payload={"claim": "Test finding"},
        promotion_status="pending_review"
    )

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_artifact
    session.execute.return_value = mock_res

    repo = ResearchRepository(session)
    candidate = await repo.get_candidate_for_review(workspace_id, artifact_id)

    assert candidate is not None
    assert candidate.artifact_id == artifact_id
    assert candidate.type == "finding_candidate"


@pytest.mark.asyncio
async def test_set_candidate_decision_accept_and_reject():
    workspace_id = uuid4()
    artifact_id = uuid4()
    run_id = uuid4()
    reviewer_id = uuid4()

    mock_artifact = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=run_id,
        type="memory_candidate",
        payload={"text": "To be accepted"},
        promotion_status="pending_review"
    )

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_artifact
    session.execute.return_value = mock_res

    repo = ResearchRepository(session)

    # Accept
    updated = await repo.set_candidate_decision(
        workspace_id=workspace_id,
        artifact_id=artifact_id,
        status="accepted",
        reviewed_by=reviewer_id
    )
    assert updated is not None
    assert updated.promotion_status == "accepted"
    assert updated.reviewed_by == reviewer_id
    assert updated.reviewed_at is not None
    assert session.commit.called

    # Reject with reason
    updated_reject = await repo.set_candidate_decision(
        workspace_id=workspace_id,
        artifact_id=artifact_id,
        status="rejected",
        reviewed_by=reviewer_id,
        review_reason="Evidence is outdated"
    )
    assert updated_reject.promotion_status == "rejected"
    assert updated_reject.review_reason == "Evidence is outdated"


@pytest.mark.asyncio
async def test_link_candidate_target():
    workspace_id = uuid4()
    artifact_id = uuid4()
    run_id = uuid4()
    target_id = uuid4()

    mock_artifact = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=run_id,
        type="memory_candidate",
        payload={"text": "Accepted memory"},
        promotion_status="accepted"
    )

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_artifact
    session.execute.return_value = mock_res

    repo = ResearchRepository(session)
    linked = await repo.link_candidate_target(
        workspace_id=workspace_id,
        artifact_id=artifact_id,
        target_type="knowledge_memory",
        target_id=target_id
    )
    assert linked is not None
    assert linked.promoted_target_type == "knowledge_memory"
    assert linked.promoted_target_id == target_id
    assert session.commit.called


@pytest.mark.asyncio
async def test_set_candidate_verification():
    workspace_id = uuid4()
    artifact_id = uuid4()
    run_id = uuid4()

    mock_artifact = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=run_id,
        type="claim_candidate",
        payload={"claim": "Density = 4.5 g/cm3"},
        promotion_status="pending_review"
    )

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_artifact
    session.execute.return_value = mock_res

    repo = ResearchRepository(session)
    verified = await repo.set_candidate_verification(
        workspace_id=workspace_id,
        artifact_id=artifact_id,
        status="unverified",
        reason={"error": "Expression syntax invalid"},
        metadata={"attempts": 1}
    )
    assert verified is not None
    assert verified.verification_status == "unverified"
    assert verified.verification_reason == {"error": "Expression syntax invalid"}
    assert verified.verification_metadata == {"attempts": 1}
    assert session.commit.called
