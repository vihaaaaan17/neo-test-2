import pytest
import asyncio
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.integrations.open_notebook.ground_engine import OpenNotebookGroundEngine
from app.services.chat.context import GroundContext, ResearchContext
from app.models.open_notebook_binding import OpenNotebookWorkspaceBinding, OpenNotebookConversationBinding
from app.models.conversation import ConversationTurn, Conversation
from app.models.workspace import Workspace
from app.models.knowledge import KnowledgeMemory
from app.schemas.chat import TurnCreate
from app.services.chat.service import ChatService


@pytest.mark.asyncio
async def test_ground_engine_rejects_research_context():
    """Verify that OpenNotebookGroundEngine strictly rejects ResearchContext."""
    engine = OpenNotebookGroundEngine()
    db = AsyncMock()

    # Create dummy ResearchContext
    dummy_research_ctx = MagicMock(spec=ResearchContext)
    dummy_research_ctx.research_run_id = uuid4()
    dummy_research_ctx.working_memory = MagicMock()
    dummy_research_ctx.output_graph = MagicMock()

    with pytest.raises(ValueError, match="Ground engine rejects ResearchContext"):
        await engine.run(
            workspace_id=uuid4(),
            query="test query",
            db=db,
            ground_context=dummy_research_ctx
        )

    with pytest.raises(ValueError, match="Ground engine rejects ResearchContext"):
        async for _ in engine.astream(
            workspace_id=uuid4(),
            query="test query",
            db=db,
            ground_context=dummy_research_ctx
        ):
            pass


@pytest.mark.asyncio
async def test_ground_engine_missing_workspace_binding():
    """Verify that OpenNotebookGroundEngine raises HTTP 400 when workspace has no active binding."""
    engine = OpenNotebookGroundEngine()
    db = AsyncMock()

    # Mock DB returning None for OpenNotebookWorkspaceBinding
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = None
    db.execute.return_value = mock_res

    with pytest.raises(HTTPException) as exc_info:
        await engine.run(
            workspace_id=uuid4(),
            query="test query",
            db=db
        )
    assert exc_info.value.status_code == 400
    assert "Workspace does not have an active Open Notebook binding" in exc_info.value.detail


@pytest.mark.asyncio
async def test_ground_engine_unary_run_success():
    """Verify unary run maps citations to canonical Neosis UUIDs and returns expected structure."""
    workspace_id = uuid4()
    canonical_source_id = uuid4()
    engine = OpenNotebookGroundEngine(workspace_id=workspace_id)
    db = AsyncMock()

    # Mock active workspace binding
    mock_res = MagicMock()
    binding = OpenNotebookWorkspaceBinding(
        workspace_id=workspace_id,
        open_notebook_notebook_id="notebook-123",
        status="ACTIVE"
    )
    mock_res.scalars.return_value.first.return_value = binding
    db.execute.return_value = mock_res

    # Mock client methods
    engine.client.get_default_models = AsyncMock(return_value={"default_chat_model": "test-chat-model"})
    engine.client.search = AsyncMock(return_value=[{"id": "upstream-source-1"}])
    engine.client.ask_simple = AsyncMock(return_value={"answer": "Photosynthesis is the process..."})

    with patch("app.integrations.open_notebook.ground_engine.map_citations", new_callable=AsyncMock) as mock_map:
        mock_map.return_value = ([canonical_source_id], False)

        result = await engine.run(
            workspace_id=workspace_id,
            query="What is photosynthesis?",
            db=db
        )

        assert result["is_grounded"] is True
        assert result["answer"] == "Photosynthesis is the process..."
        assert result["evidence"] == [canonical_source_id]
        assert result["provenance_status"] == "full"


@pytest.mark.asyncio
async def test_ground_engine_astream_success():
    """Verify astream yields citation, token deltas, and final done event with canonical UUIDs."""
    workspace_id = uuid4()
    conversation_id = uuid4()
    canonical_source_id = uuid4()
    engine = OpenNotebookGroundEngine(workspace_id=workspace_id)
    db = AsyncMock()

    # Mock active workspace binding and conversation binding
    mock_ws_res = MagicMock()
    ws_binding = OpenNotebookWorkspaceBinding(
        workspace_id=workspace_id,
        open_notebook_notebook_id="notebook-123",
        status="ACTIVE"
    )
    mock_ws_res.scalars.return_value.first.return_value = ws_binding

    mock_conv_res = MagicMock()
    conv_binding = OpenNotebookConversationBinding(
        conversation_id=conversation_id,
        open_notebook_session_id="session-789"
    )
    mock_conv_res.scalars.return_value.first.return_value = conv_binding

    # Second query lists the workspace's projected upstream sources (no explicit scope given)
    mock_src_res = MagicMock()
    mock_src_res.scalars.return_value.all.return_value = []
    db.execute.side_effect = [mock_ws_res, mock_src_res, mock_conv_res]

    # Mock search and streaming chunks
    engine.client.search = AsyncMock(return_value=[{"id": "upstream-1"}])

    async def mock_chat_stream(session_id, notebook_id, message, context_config=None):
        yield {"event": "token", "data": {"token": "Paris "}}
        yield {"event": "token", "data": {"token": "is "}}
        yield {"event": "token", "data": {"token": "France."}}
        yield {"event": "done", "data": {"answer": "Paris is France."}}

    engine.client.chat_stream = mock_chat_stream

    with patch("app.integrations.open_notebook.ground_engine.map_citations", new_callable=AsyncMock) as mock_map:
        mock_map.return_value = ([canonical_source_id], False)

        events = []
        async for chunk in engine.astream(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            query="Capital of France?",
            db=db
        ):
            events.append(chunk)

        # Check citation event
        assert events[0]["type"] == "citation"
        assert events[0]["evidence"] == [canonical_source_id]
        assert events[0]["provenance_status"] == "full"

        # Check token events
        token_contents = [e["content"] for e in events if e["type"] == "token"]
        assert "".join(token_contents) == "Paris is France."

        # Check done event
        assert events[-1]["type"] == "done"
        assert events[-1]["answer"] == "Paris is France."
        assert events[-1]["evidence"] == [canonical_source_id]


@pytest.mark.asyncio
async def test_chat_service_ground_delegation_zero_knowledge_leak():
    """Verify ChatService delegates to ground_engine and writes zero KnowledgeMemory."""
    workspace_id = uuid4()
    conversation_id = uuid4()
    owner_id = uuid4()
    turn_id = uuid4()
    canonical_source_id = uuid4()

    mock_db = AsyncMock()
    mock_conv_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()
    mock_arq_redis = AsyncMock()

    mock_ws = Workspace(workspace_id=workspace_id, owner_id=owner_id)
    mock_conv = Conversation(
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        last_turn_sequence=0,
        status="active"
    )

    mock_initial_turn = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        sequence=1,
        mode="ground",
        user_message="Explain quantum tunneling.",
        status="pending"
    )

    mock_completed_turn = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        sequence=1,
        mode="ground",
        user_message="Explain quantum tunneling.",
        assistant_message="Quantum tunneling is a quantum mechanical phenomenon.",
        status="completed"
    )

    mock_workspace_repo.get_workspace = AsyncMock(return_value=mock_ws)
    mock_conv_repo.get_conversation = AsyncMock(return_value=mock_conv)
    mock_conv_repo.get_turn_by_client_request_id = AsyncMock(return_value=None)
    mock_conv_repo.allocate_turn_sequence = AsyncMock(return_value=1)
    mock_conv_repo.append_turn = AsyncMock(return_value=mock_initial_turn)
    mock_conv_repo.set_turn_status = AsyncMock(return_value=mock_completed_turn)

    mock_ground_engine = MagicMock()
    mock_ground_engine.run = AsyncMock(return_value={
        "is_grounded": True,
        "answer": "Quantum tunneling is a quantum mechanical phenomenon.",
        "evidence": [canonical_source_id],
        "provenance_status": "full"
    })

    with patch("app.services.chat.service.ChatEventRepository"), \
         patch("app.services.chat.service.ChatEventService"), \
         patch("app.services.chat.context.build_ground_context") as mock_build_ground_ctx:

        mock_ground_ctx = MagicMock()
        mock_ground_ctx.model_dump.return_value = {"query": "Explain quantum tunneling."}
        mock_build_ground_ctx.return_value = mock_ground_ctx

        service = ChatService(
            db=mock_db,
            conv_repo=mock_conv_repo,
            workspace_repo=mock_workspace_repo,
            arq_redis=mock_arq_redis,
            ground_engine=mock_ground_engine
        )
        service.event_service = AsyncMock()

        turn_create = TurnCreate(
            mode="ground",
            message="Explain quantum tunneling."
        )

        completed_turn = await service.submit_turn(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            owner_id=owner_id,
            turn_create=turn_create,
            stream=False
        )

        assert completed_turn.status == "completed"
        mock_ground_engine.run.assert_called_once()

        # Zero KnowledgeMemory added
        for call_args in mock_db.add.call_args_list:
            assert not isinstance(call_args[0][0], KnowledgeMemory)

        # Zero graph sync jobs
        if mock_arq_redis.enqueue_job.called:
            enqueued = [call[0][0] for call in mock_arq_redis.enqueue_job.call_args_list]
            assert "sync_knowledge_to_graph_job" not in enqueued
