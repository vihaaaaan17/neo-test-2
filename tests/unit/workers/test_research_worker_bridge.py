import json
import pytest
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.models.conversation import ConversationTurn
from app.models.workspace import Workspace
from app.models.research import ResearchRun, ResearchReport, ResearchArtifact
from app.workers.tasks import run_research_agent_job


@pytest.mark.asyncio
async def test_research_worker_synchronous_event_bridging_and_completion():
    """
    run_research_agent_job synchronously bridges lifecycle events to ChatEventService
    and finalizes ConversationTurn with assistant summary from ResearchReport.
    """
    workspace_id = uuid4()
    run_id = uuid4()
    conversation_id = uuid4()
    turn_id = uuid4()
    owner_id = uuid4()

    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock()

    ctx = {
        "job_id": "test_job_bridge_1",
        "redis": mock_redis,
        "llm_call": AsyncMock(return_value="mock LLM output")
    }

    mock_ws = Workspace(workspace_id=workspace_id, owner_id=owner_id, timeline_epoch=1)
    mock_run = ResearchRun(
        run_id=run_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        objective="Analyze high-Tc superconductors",
        status="pending",
        engine="open_deep_research",
        conversation_id=conversation_id,
        turn_id=turn_id
    )
    mock_report = ResearchReport(
        report_id=uuid4(),
        run_id=run_id,
        objective="Analyze high-Tc superconductors",
        content="Superconductors operate up to 138K at ambient pressure."
    )

    async def mock_stream_events(*args, **kwargs):
        yield {"status": "planning", "message": "Planning research breakdown"}
        yield {"status": "researching", "message": "Searching literature"}
        yield {
            "scratchpad_entry": {
                "entry_type": "finding",
                "content": "YBCO exhibits high-Tc transition.",
                "is_pinned_to_workspace": False,
                "metadata": {}
            }
        }
        yield {"status": "synthesizing", "message": "Synthesizing report"}
        yield {"status": "completed", "message": "Research complete"}

    mock_engine = MagicMock()
    mock_engine.astream_events = mock_stream_events

    mock_sp_entry = MagicMock()
    mock_sp_entry.entry_id = uuid4()
    mock_sp_entry.entry_type = "finding"
    mock_sp_entry.content = "YBCO exhibits high-Tc transition."
    mock_sp_entry.is_pinned_to_workspace = False
    mock_sp_entry.lifecycle = "active"
    mock_sp_entry.metadata_ = {}

    with patch("app.workers.tasks.async_session_maker") as mock_session_cls, \
         patch("app.integrations.research_engine.factory.ResearchEngineFactory.get_engine", return_value=mock_engine), \
         patch("app.repositories.scratchpad.ScratchpadRepository") as mock_sp_repo_cls, \
         patch("app.repositories.research.ResearchRepository") as mock_res_repo_cls, \
         patch("app.services.research.lifecycle.ResearchLifecycleService") as mock_lifecycle_cls, \
         patch("app.services.research.derivation.DerivationService") as mock_derivation_cls, \
         patch("app.repositories.conversation.ConversationRepository") as mock_conv_repo_cls, \
         patch("app.services.chat.events.ChatEventService") as mock_event_service_cls:

        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        def mock_execute_fn(stmt):
            res = MagicMock()
            stmt_str = str(stmt)
            if "research_reports" in stmt_str:
                res.scalars.return_value.first.return_value = mock_report
            elif "workspaces" in stmt_str:
                res.scalars.return_value.first.return_value = mock_ws
            elif "research_runs" in stmt_str:
                res.scalars.return_value.first.return_value = mock_run
            else:
                res.scalars.return_value.first.return_value = None
            res.scalars.return_value.all.return_value = []
            return res

        mock_session.execute = AsyncMock(side_effect=mock_execute_fn)

        mock_sp_repo = mock_sp_repo_cls.return_value
        mock_sp_repo.create_entry = AsyncMock(return_value=mock_sp_entry)

        mock_lifecycle = mock_lifecycle_cls.return_value
        mock_lifecycle.transition_run = AsyncMock()

        mock_res_repo = mock_res_repo_cls.return_value
        mock_res_repo.list_candidates_by_status = AsyncMock(return_value=[])
        mock_res_repo.get_run = AsyncMock(return_value=mock_run)

        mock_conv_repo = mock_conv_repo_cls.return_value
        mock_conv_repo.set_turn_status = AsyncMock()

        mock_event_service = mock_event_service_cls.return_value
        mock_event_service.record_and_publish = AsyncMock()

        res = await run_research_agent_job(
            ctx,
            workspace_id=str(workspace_id),
            objective="Analyze high-Tc superconductors",
            run_id=str(run_id)
        )

        assert res["status"] == "completed"

        # Verify set_turn_status finalized the turn with assistant_message and research_run_id
        mock_conv_repo.set_turn_status.assert_awaited()
        final_call_kwargs = mock_conv_repo.set_turn_status.call_args.kwargs
        assert final_call_kwargs["turn_id"] == turn_id
        assert final_call_kwargs["status"] == "completed"
        assert final_call_kwargs["assistant_message"] == mock_report.content
        assert final_call_kwargs["research_run_id"] == run_id

        # Verify synchronous bridging to ChatEventService
        recorded_types = [
            call.args[1] if len(call.args) > 1 else call.kwargs.get("event_type")
            for call in mock_event_service.record_and_publish.await_args_list
        ]
        assert "turn.research_started" in recorded_types
        assert "turn.research_planning" in recorded_types
        assert "turn.researching" in recorded_types
        assert "scratchpad_entry" in recorded_types
        assert "turn.synthesizing" in recorded_types
        assert "turn.promotion_available" in recorded_types
        assert "turn.completed" in recorded_types
        assert "done" in recorded_types


@pytest.mark.asyncio
async def test_research_worker_timeline_fence_cancellation():
    """
    When timeline_epoch advances due to rollback during execution, worker aborts,
    cancels ConversationTurn, and emits turn.cancelled and done.
    """
    workspace_id = uuid4()
    run_id = uuid4()
    conversation_id = uuid4()
    turn_id = uuid4()
    owner_id = uuid4()

    mock_redis = AsyncMock()
    ctx = {
        "job_id": "test_job_fence",
        "redis": mock_redis,
        "llm_call": AsyncMock(return_value="mock")
    }

    mock_ws_initial = Workspace(workspace_id=workspace_id, owner_id=owner_id, timeline_epoch=1)
    mock_ws_rolled_back = Workspace(workspace_id=workspace_id, owner_id=owner_id, timeline_epoch=2)
    mock_run = ResearchRun(
        run_id=run_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        objective="Analyze rollback fence",
        status="pending",
        engine="open_deep_research",
        conversation_id=conversation_id,
        turn_id=turn_id
    )

    async def mock_stream_events(*args, **kwargs):
        yield {"status": "researching", "message": "Researching before rollback"}

    mock_engine = MagicMock()
    mock_engine.astream_events = mock_stream_events

    with patch("app.workers.tasks.async_session_maker") as mock_session_cls, \
         patch("app.integrations.research_engine.factory.ResearchEngineFactory.get_engine", return_value=mock_engine), \
         patch("app.services.research.lifecycle.ResearchLifecycleService") as mock_lifecycle_cls, \
         patch("app.repositories.conversation.ConversationRepository") as mock_conv_repo_cls, \
         patch("app.services.chat.events.ChatEventService") as mock_event_service_cls:

        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        exec_res = MagicMock()
        exec_res.scalars.return_value.first.side_effect = [
            mock_ws_initial,      # Initial workspace load (epoch=1)
            mock_run,             # Initial run load
            mock_ws_rolled_back,  # Check concurrency fence (epoch=2)
            mock_run,             # Run query in transition fallback
        ]
        mock_session.execute = AsyncMock(return_value=exec_res)

        mock_conv_repo = mock_conv_repo_cls.return_value
        mock_conv_repo.set_turn_status = AsyncMock()

        mock_event_service = mock_event_service_cls.return_value
        mock_event_service.record_and_publish = AsyncMock()

        res = await run_research_agent_job(
            ctx,
            workspace_id=str(workspace_id),
            objective="Analyze rollback fence",
            run_id=str(run_id)
        )

        assert res["status"] == "aborted_by_timeline_fence"

        # Verify turn was cancelled
        mock_conv_repo.set_turn_status.assert_awaited()
        fence_call_kwargs = mock_conv_repo.set_turn_status.call_args.kwargs
        assert fence_call_kwargs["turn_id"] == turn_id
        assert fence_call_kwargs["status"] == "cancelled"
        assert fence_call_kwargs["error_code"] == "timeline_fence_aborted"

        # Verify turn.cancelled and done bridged
        recorded_types = [
            call.args[1] if len(call.args) > 1 else call.kwargs.get("event_type")
            for call in mock_event_service.record_and_publish.await_args_list
        ]
        assert "turn.cancelled" in recorded_types
        assert "done" in recorded_types


@pytest.mark.asyncio
async def test_research_worker_job_failure_updates_turn():
    """
    When research engine raises an unhandled exception, worker fails gracefully,
    updates turn to 'failed', and emits turn.failed and done events.
    """
    workspace_id = uuid4()
    run_id = uuid4()
    conversation_id = uuid4()
    turn_id = uuid4()
    owner_id = uuid4()

    mock_redis = AsyncMock()
    ctx = {
        "job_id": "test_job_failure",
        "redis": mock_redis,
        "llm_call": AsyncMock(return_value="mock")
    }

    mock_ws = Workspace(workspace_id=workspace_id, owner_id=owner_id, timeline_epoch=1)
    mock_run = ResearchRun(
        run_id=run_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        objective="Failure test",
        status="pending",
        engine="open_deep_research",
        conversation_id=conversation_id,
        turn_id=turn_id
    )

    async def mock_failing_stream(*args, **kwargs):
        raise RuntimeError("External research API rate limit exceeded")
        yield  # make it a generator

    mock_engine = MagicMock()
    mock_engine.astream_events = mock_failing_stream

    with patch("app.workers.tasks.async_session_maker") as mock_session_cls, \
         patch("app.integrations.research_engine.factory.ResearchEngineFactory.get_engine", return_value=mock_engine), \
         patch("app.services.research.lifecycle.ResearchLifecycleService") as mock_lifecycle_cls, \
         patch("app.repositories.conversation.ConversationRepository") as mock_conv_repo_cls, \
         patch("app.services.chat.events.ChatEventService") as mock_event_service_cls:

        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        exec_res = MagicMock()
        exec_res.scalars.return_value.first.side_effect = [
            mock_ws,
            mock_run,
        ]
        mock_session.execute = AsyncMock(return_value=exec_res)

        mock_conv_repo = mock_conv_repo_cls.return_value
        mock_conv_repo.set_turn_status = AsyncMock()

        mock_event_service = mock_event_service_cls.return_value
        mock_event_service.record_and_publish = AsyncMock()

        res = await run_research_agent_job(
            ctx,
            workspace_id=str(workspace_id),
            objective="Failure test",
            run_id=str(run_id)
        )

        assert res["status"] == "failed"

        # Verify turn was marked failed
        mock_conv_repo.set_turn_status.assert_awaited()
        fail_call_kwargs = mock_conv_repo.set_turn_status.call_args.kwargs
        assert fail_call_kwargs["turn_id"] == turn_id
        assert fail_call_kwargs["status"] == "failed"
        assert fail_call_kwargs["error_code"] == "research_job_failed"

        # Verify turn.failed and done bridged
        recorded_types = [
            call.args[1] if len(call.args) > 1 else call.kwargs.get("event_type")
            for call in mock_event_service.record_and_publish.await_args_list
        ]
        assert "turn.failed" in recorded_types
        assert "done" in recorded_types
