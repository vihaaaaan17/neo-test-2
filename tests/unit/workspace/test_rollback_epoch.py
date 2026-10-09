import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from app.models.workspace import Workspace, WorkspaceCommit
from app.models.research import ResearchRun, ResearchArtifact, ResearchEvidence
from app.repositories.workspace import WorkspaceRepository
from app.workers.tasks import run_research_agent_job
from app.services.research.promotion import PromotionService


@pytest.mark.asyncio
async def test_rollback_increments_timeline_epoch_atomically():
    """
    Rolling back to a commit atomically increments timeline_epoch and updates active_commit_id.
    """
    workspace_id = uuid4()
    owner_id = uuid4()
    commit_id = uuid4()

    mock_workspace = Workspace(
        workspace_id=workspace_id,
        owner_id=owner_id,
        status="active",
        timeline_epoch=1,
        active_commit_id=uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    mock_commit = WorkspaceCommit(
        commit_id=commit_id,
        workspace_id=workspace_id,
        active_knowledge_ids=[],
        manifest={"schema_version": 1},
        created_at=datetime.now(timezone.utc)
    )

    session = AsyncMock()
    mock_ws_res = MagicMock()
    mock_ws_res.scalars.return_value.first.return_value = mock_workspace

    mock_commit_res = MagicMock()
    mock_commit_res.scalars.return_value.first.return_value = mock_commit

    session.execute.side_effect = [mock_ws_res, mock_commit_res]

    repo = WorkspaceRepository(session)
    updated_ws, new_epoch = await repo.rollback_workspace_atomic(workspace_id, commit_id, owner_id)

    assert updated_ws is not None
    assert new_epoch == 2
    assert updated_ws.timeline_epoch == 2
    assert updated_ws.active_commit_id == commit_id
    assert session.commit.called


@pytest.mark.asyncio
async def test_worker_fence_blocks_stale_epoch_mutation():
    """
    If a rollback increments the workspace timeline_epoch while a research job is running,
    the worker detects the mismatch, aborts durable mutations, transitions the run to
    'aborted_by_timeline_fence', and publishes a 'workspace.rollback.fence_triggered' event.
    """
    workspace_id = uuid4()
    run_id = uuid4()
    owner_id = uuid4()

    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock()

    ctx = {
        "job_id": "test_fence_job_1",
        "redis": mock_redis,
        "llm_call": AsyncMock(return_value="mock")
    }

    # At start: timeline_epoch is 1
    mock_ws_start = Workspace(
        workspace_id=workspace_id,
        owner_id=owner_id,
        status="active",
        timeline_epoch=1
    )

    # During execution, rollback occurred, so epoch is now 2
    mock_ws_rolled_back = Workspace(
        workspace_id=workspace_id,
        owner_id=owner_id,
        status="active",
        timeline_epoch=2
    )

    mock_run = ResearchRun(
        run_id=run_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        objective="Investigate quantum hall effect",
        engine="open_deep_research",
        status="pending"
    )

    # Simulated engine events
    async def mock_stream_events(*args, **kwargs):
        yield {"status": "researching", "message": "Searching sources"}
        yield {"status": "completed", "message": "Finished"}

    mock_engine = MagicMock()
    mock_engine.astream_events = mock_stream_events

    with patch("app.workers.tasks.async_session_maker") as mock_session_cls, \
         patch("app.workers.tasks.build_research_engine", return_value=mock_engine), \
         patch("app.services.research.lifecycle.ResearchLifecycleService") as mock_lifecycle_cls, \
         patch("app.repositories.research.ResearchRepository") as mock_res_repo_cls:

        mock_lifecycle = mock_lifecycle_cls.return_value
        mock_lifecycle.transition_run = AsyncMock()

        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        # 1. First session query: workspace (epoch 1), run (pending)
        res_ws_1 = MagicMock()
        res_ws_1.scalars.return_value.first.return_value = mock_ws_start
        res_run_1 = MagicMock()
        res_run_1.scalars.return_value.first.return_value = mock_run

        # 2. Concurrency check query: workspace current (epoch 2)
        res_ws_2 = MagicMock()
        res_ws_2.scalars.return_value.first.return_value = mock_ws_rolled_back

        mock_session.execute = AsyncMock(side_effect=[res_ws_1, res_run_1, res_ws_2])

        res = await run_research_agent_job(
            ctx,
            workspace_id=str(workspace_id),
            objective="Investigate quantum hall effect",
            run_id=str(run_id)
        )

        # Worker must return aborted_by_timeline_fence status
        assert res["status"] == "aborted_by_timeline_fence"
        assert "fence" in res["reason"].lower()

        # Lifecycle service must be called with aborted_by_timeline_fence
        mock_lifecycle.transition_run.assert_awaited_once()
        assert mock_lifecycle.transition_run.await_args[0][2] == "aborted_by_timeline_fence"

        # Redis fence_triggered event must be published
        fence_calls = [
            json.loads(args[1]) for args, _ in mock_redis.publish.call_args_list
            if "workspace.rollback.fence_triggered" in args[1]
        ]
        assert len(fence_calls) > 0
        fence_ev = fence_calls[0]
        assert fence_ev["event_type"] == "workspace.rollback.fence_triggered"
        assert fence_ev["expected_epoch"] == 1
        assert fence_ev["current_epoch"] == 2


@pytest.mark.asyncio
async def test_historical_runs_and_evidence_preserved_after_rollback():
    """
    Workspace rollback increments timeline_epoch and changes active_commit_id,
    but does NOT delete historical research runs, tasks, evidence, or candidate artifacts.
    """
    workspace_id = uuid4()
    owner_id = uuid4()
    commit_id = uuid4()
    run_id = uuid4()

    mock_workspace = Workspace(
        workspace_id=workspace_id,
        owner_id=owner_id,
        status="active",
        timeline_epoch=2,
        active_commit_id=uuid4()
    )

    mock_commit = WorkspaceCommit(
        commit_id=commit_id,
        workspace_id=workspace_id,
        active_knowledge_ids=[],
        manifest={"schema_version": 1}
    )

    # Historical runs and evidence exist
    mock_run = ResearchRun(
        run_id=run_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        objective="Past research run",
        status="completed"
    )

    mock_evidence = ResearchEvidence(
        evidence_id=uuid4(),
        run_id=run_id,
        content="Historical research citation"
    )

    mock_artifact = ResearchArtifact(
        artifact_id=uuid4(),
        run_id=run_id,
        type="candidate",
        payload={"claim": "Historical claim"},
        promotion_status="pending_review"
    )

    session = AsyncMock()
    mock_ws_res = MagicMock()
    mock_ws_res.scalars.return_value.first.return_value = mock_workspace

    mock_commit_res = MagicMock()
    mock_commit_res.scalars.return_value.first.return_value = mock_commit

    session.execute.side_effect = [mock_ws_res, mock_commit_res]

    repo = WorkspaceRepository(session)
    updated_ws, new_epoch = await repo.rollback_workspace_atomic(workspace_id, commit_id, owner_id)

    assert new_epoch == 3
    # Verify session.delete was NEVER called on any entity
    assert not session.delete.called
    assert mock_run.status == "completed"
    assert mock_artifact.promotion_status == "pending_review"
    assert mock_evidence.content == "Historical research citation"


@pytest.mark.asyncio
async def test_post_rollback_promotion_with_matching_epoch_succeeds():
    """
    After rollback, a new research run or promotion operation executed with the
    new matching epoch completes successfully.
    """
    workspace_id = uuid4()
    artifact_id = uuid4()
    user_id = uuid4()
    run_id = uuid4()

    # Workspace at epoch 3 (after rollbacks)
    mock_ws = Workspace(
        workspace_id=workspace_id,
        owner_id=user_id,
        status="active",
        timeline_epoch=3
    )

    mock_candidate = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=run_id,
        type="memory_candidate",
        payload={
            "text": "Valid finding under epoch 3",
            "provenance": {"sources": [{"type": "evidence", "id": str(uuid4())}]}
        },
        promotion_status="pending_review"
    )

    session = AsyncMock()
    session.add = MagicMock()
    repo = MagicMock()
    repo.get_candidate_for_review = AsyncMock(return_value=mock_candidate)

    derivation_svc = MagicMock()
    derivation_svc.validate_provenance_lineage = AsyncMock(return_value=True)

    promo_svc = PromotionService(
        session=session,
        research_repo=repo,
        derivation_service=derivation_svc,
        arq_pool=AsyncMock()
    )

    # Acceptance succeeds under current epoch
    updated_cand, target_id = await promo_svc.accept_candidate(workspace_id, artifact_id, user_id)

    assert updated_cand.promotion_status == "accepted"
    assert updated_cand.reviewed_by == user_id
    assert target_id is not None
