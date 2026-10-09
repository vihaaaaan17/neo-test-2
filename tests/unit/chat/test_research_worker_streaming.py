import pytest
import json
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from app.schemas.chat import TurnCreate
from app.models.conversation import Conversation, ConversationTurn
from app.models.workspace import Workspace
from app.models.research import ResearchRun
from app.services.chat.service import ChatService
from app.workers.tasks import run_research_agent_job


@pytest.mark.asyncio
async def test_submit_research_turn_snapshots_context_version():
    """
    Submitting a Research turn must build research context and synchronously
    save the context_version manifest on ConversationTurn before background execution.
    """
    workspace_id = uuid4()
    conversation_id = uuid4()
    user_id = uuid4()
    turn_id = uuid4()
    run_id = uuid4()

    mock_db = AsyncMock()
    mock_workspace_repo = AsyncMock()
    mock_conv_repo = AsyncMock()
    mock_research_repo = AsyncMock()
    mock_arq_redis = AsyncMock()

    mock_ws = Workspace(workspace_id=workspace_id, owner_id=user_id)
    mock_conv = Conversation(
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=user_id,
        last_turn_sequence=0,
        status="active"
    )

    mock_initial_turn = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=user_id,
        sequence=1,
        mode="research",
        user_message="Investigate phase transitions",
        status="pending"
    )

    mock_running_turn = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=user_id,
        sequence=1,
        mode="research",
        user_message="Investigate phase transitions",
        research_run_id=run_id,
        context_version={"research_context": {"version": "v1", "budget": 5000, "total_tokens": 8}},
        status="running"
    )

    mock_workspace_repo.get_workspace = AsyncMock(return_value=mock_ws)
    mock_conv_repo.get_conversation = AsyncMock(return_value=mock_conv)
    mock_conv_repo.get_turn_by_client_request_id = AsyncMock(return_value=None)
    mock_conv_repo.allocate_turn_sequence = AsyncMock(return_value=1)
    mock_conv_repo.append_turn = AsyncMock(return_value=mock_initial_turn)
    mock_conv_repo.set_turn_status = AsyncMock(return_value=mock_running_turn)

    mock_run = MagicMock()
    mock_run.run_id = run_id
    mock_run.status = "pending"

    mock_admission = AsyncMock()
    mock_admission.admit_research_run = AsyncMock(return_value=mock_run)

    with patch("app.services.chat.service.ChatEventRepository"), \
         patch("app.services.chat.service.ChatEventService"):
        service = ChatService(
            db=mock_db,
            conv_repo=mock_conv_repo,
            workspace_repo=mock_workspace_repo,
            research_repo=mock_research_repo,
            arq_redis=mock_arq_redis,
            admission_controller=mock_admission
        )
        service.event_service = AsyncMock()

        turn_create = TurnCreate(
            mode="research",
            message="Investigate phase transitions",
            research_options={"token_budget": 5000}
        )

        with patch("app.services.chat.context.build_research_context") as mock_build_ctx:
            mock_ctx_obj = MagicMock()
            mock_ctx_obj.context_version.model_dump.return_value = {
                "version": "v1",
                "budget": 5000,
                "total_tokens": 8,
                "included_items": [{"item_id": "current_query", "item_type": "current_message", "tokens": 8}],
                "evicted_items": []
            }
            mock_build_ctx.return_value = mock_ctx_obj

            result_turn = await service.submit_turn(
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                owner_id=user_id,
                turn_create=turn_create,
                stream=False
            )

            assert result_turn.status == "running"
            assert result_turn.research_run_id == run_id

            # Verify build_research_context was called with correct parameters
            mock_build_ctx.assert_awaited_once()
            call_kwargs = mock_build_ctx.await_args.kwargs
            assert call_kwargs["workspace_id"] == workspace_id
            assert call_kwargs["conversation_id"] == conversation_id
            assert call_kwargs["token_budget"] == 5000

            # Verify set_turn_status was called with context_version snapshot
            mock_conv_repo.set_turn_status.assert_awaited_once()
            status_kwargs = mock_conv_repo.set_turn_status.await_args.kwargs
            assert status_kwargs["status"] == "running"
            assert status_kwargs["research_run_id"] == run_id
            assert "research_context" in status_kwargs["context_version"]
            assert status_kwargs["context_version"]["research_context"]["budget"] == 5000


@pytest.mark.asyncio
async def test_worker_persists_structured_scratchpad_and_publishes_event():
    """
    When research engine emits a structured scratchpad entry, run_research_agent_job
    must persist it via ScratchpadRepository and publish 'scratchpad_entry' event to Redis.
    """
    workspace_id = uuid4()
    run_id = uuid4()
    conversation_id = uuid4()
    turn_id = uuid4()
    user_id = uuid4()

    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock()

    ctx = {
        "job_id": "test_job_123",
        "redis": mock_redis,
        "llm_call": AsyncMock(return_value="mock response")
    }

    mock_run = MagicMock()
    mock_run.workspace_id = workspace_id
    mock_run.run_id = run_id
    mock_run.owner_id = user_id
    mock_run.engine = "open_deep_research"
    mock_run.conversation_id = conversation_id
    mock_run.turn_id = turn_id
    mock_run.status = "pending"

    mock_ws = Workspace(workspace_id=workspace_id, owner_id=user_id)

    # Simulated engine event stream with a structured scratchpad entry
    async def mock_stream_events(*args, **kwargs):
        yield {
            "status": "planning",
            "message": "Generated brief",
            "scratchpad_entry": {
                "entry_type": "hypothesis",
                "content": "Superconductivity transition occurs at 93K for YBCO.",
                "is_pinned_to_workspace": False,
                "metadata": {"source": "engine"}
            }
        }
        yield {"status": "turn_response", "text": "Report body"}

    mock_engine = MagicMock()
    mock_engine.astream_events = mock_stream_events

    mock_sp_entry = MagicMock()
    mock_sp_entry.entry_id = uuid4()
    mock_sp_entry.entry_type = "hypothesis"
    mock_sp_entry.content = "Superconductivity transition occurs at 93K for YBCO."
    mock_sp_entry.is_pinned_to_workspace = False
    mock_sp_entry.lifecycle = "active"
    mock_sp_entry.metadata_ = {"source": "engine"}

    with patch("app.workers.tasks.async_session_maker") as mock_session_cls, \
         patch("app.workers.tasks.build_research_engine", return_value=mock_engine), \
         patch("app.repositories.scratchpad.ScratchpadRepository") as mock_sp_repo_cls, \
         patch("app.services.research.lifecycle.ResearchLifecycleService") as mock_lifecycle_cls, \
         patch("app.services.research.service.ResearchService") as mock_res_service_cls:

        mock_lifecycle = mock_lifecycle_cls.return_value
        mock_lifecycle.transition_run = AsyncMock()

        mock_res_service = mock_res_service_cls.return_value
        mock_res_service.promote_memory_candidates = AsyncMock()
        mock_res_service.promote_graph_candidates = AsyncMock()
        mock_res_service.finalize_report = AsyncMock()

        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        exec_res = MagicMock()
        exec_res.scalars.return_value.first.side_effect = [mock_ws, mock_run, mock_run]
        mock_session.execute = AsyncMock(return_value=exec_res)

        mock_sp_repo = mock_sp_repo_cls.return_value
        mock_sp_repo.create_entry = AsyncMock(return_value=mock_sp_entry)

        res = await run_research_agent_job(
            ctx,
            workspace_id=str(workspace_id),
            objective="Analyze high-Tc superconductivity",
            run_id=str(run_id)
        )

        assert res["status"] == "completed"

        # Verify scratchpad repository was called to persist structured hypothesis
        mock_sp_repo.create_entry.assert_awaited_once_with(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            turn_id=turn_id,
            run_id=run_id,
            entry_type="hypothesis",
            content="Superconductivity transition occurs at 93K for YBCO.",
            is_pinned_to_workspace=False,
            metadata={"source": "engine"}
        )

        # Verify Redis publish was called with event_type="scratchpad_entry"
        published_calls = [args[0] for args, _ in mock_redis.publish.call_args_list]
        published_payloads = [args[1] for args, _ in mock_redis.publish.call_args_list]

        # Check that research_events:{run_id} and turn_events:{turn_id} channels received the event
        assert f"research_events:{run_id}" in published_calls
        assert f"turn_events:{turn_id}" in published_calls

        # Find the scratchpad_entry payload
        scratchpad_events = [
            json.loads(p) for p in published_payloads
            if isinstance(json.loads(p), dict) and json.loads(p).get("event_type") == "scratchpad_entry"
        ]
        assert len(scratchpad_events) > 0
        sp_event = scratchpad_events[0]
        assert sp_event["event_type"] == "scratchpad_entry"
        assert sp_event["payload"]["entry_type"] == "hypothesis"
        assert "Superconductivity" in sp_event["payload"]["content"]


@pytest.mark.asyncio
async def test_worker_rejects_raw_chain_of_thought_scratchpad():
    """
    If engine emits an event with raw chain-of-thought, it must NOT be persisted to scratchpad.
    """
    workspace_id = uuid4()
    run_id = uuid4()
    user_id = uuid4()

    mock_redis = AsyncMock()
    ctx = {
        "job_id": "job_cot_test",
        "redis": mock_redis,
        "llm_call": AsyncMock(return_value="mock")
    }

    mock_run = MagicMock()
    mock_run.workspace_id = workspace_id
    mock_run.run_id = run_id
    mock_run.owner_id = user_id
    mock_run.engine = "open_deep_research"
    mock_run.conversation_id = None
    mock_run.turn_id = None
    mock_run.status = "pending"

    mock_ws = Workspace(workspace_id=workspace_id, owner_id=user_id)

    async def mock_cot_stream(*args, **kwargs):
        yield {
            "status": "thinking",
            "scratchpad_entry": {
                "entry_type": "observation",
                "content": "<thought>I will now query Google for YBCO data and see what comes back</thought>"
            }
        }
        yield {"status": "turn_response", "text": "Report body"}

    mock_engine = MagicMock()
    mock_engine.astream_events = mock_cot_stream

    with patch("app.workers.tasks.async_session_maker") as mock_session_cls, \
         patch("app.workers.tasks.build_research_engine", return_value=mock_engine), \
         patch("app.repositories.scratchpad.ScratchpadRepository") as mock_sp_repo_cls, \
         patch("app.services.research.lifecycle.ResearchLifecycleService") as mock_lifecycle_cls, \
         patch("app.services.research.service.ResearchService") as mock_res_service_cls:

        mock_lifecycle = mock_lifecycle_cls.return_value
        mock_lifecycle.transition_run = AsyncMock()

        mock_res_service = mock_res_service_cls.return_value
        mock_res_service.promote_memory_candidates = AsyncMock()
        mock_res_service.promote_graph_candidates = AsyncMock()
        mock_res_service.finalize_report = AsyncMock()

        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        exec_res = MagicMock()
        exec_res.scalars.return_value.first.side_effect = [mock_ws, mock_run, mock_run]
        mock_session.execute = AsyncMock(return_value=exec_res)

        mock_sp_repo = mock_sp_repo_cls.return_value
        mock_sp_repo.create_entry = AsyncMock()

        res = await run_research_agent_job(
            ctx,
            workspace_id=str(workspace_id),
            objective="Test CoT rejection",
            run_id=str(run_id)
        )

        assert res["status"] == "completed"
        # ScratchpadRepository must NOT be called for raw CoT!
        mock_sp_repo.create_entry.assert_not_called()
