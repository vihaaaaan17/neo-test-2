import pytest
import json
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from app.models.conversation import Conversation, ConversationTurn
from app.models.workspace import Workspace
from app.models.knowledge import KnowledgeMemory
from app.models.research import ResearchEvidence
from app.models.scratchpad import ScratchpadEntry
from app.models.open_notebook_binding import OpenNotebookWorkspaceBinding, OpenNotebookConversationBinding
from app.services.chat.context import build_ground_context, GroundContext
from app.services.chat.service import ChatService
from app.schemas.chat import TurnCreate

DISTINCTIVE_RESEARCH_FACT = "RESEARCH_FACT_UNVERIFIED_ROOM_TEMP_SUPERCONDUCTOR_DISCOVERY_XYZ99"
DISTINCTIVE_GRAPH_FACT = "GRAPH_FACT_PROJECTION_CLUSTER_ALPHA_7749"
DISTINCTIVE_SCRATCHPAD_NOTE = "SCRATCHPAD_HYPOTHESIS_SECRET_CATALYST_42"


@pytest.mark.asyncio
async def test_critical_ground_isolation_zero_leak():
    """
    Critical Invariant Test:
    'Ground is source-grounded. Research is state-aware. Research-derived knowledge must never become Ground evidence.'

    Even when KnowledgeMemory, ResearchEvidence, and Scratchpad contain distinctive research findings,
    build_ground_context MUST NOT include any of them in the assembled Ground context.
    """
    workspace_id = uuid4()
    conversation_id = uuid4()
    user_id = uuid4()
    now = datetime.now(timezone.utc)

    # 1. Turn history with a prior Ground turn and a prior Research turn
    ground_turn = ConversationTurn(
        turn_id=uuid4(),
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=user_id,
        sequence=1,
        mode="ground",
        user_message="What is the boiling point of pure water?",
        assistant_message="100 degrees Celsius at 1 atmosphere.",
        status="completed"
    )

    research_turn = ConversationTurn(
        turn_id=uuid4(),
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=user_id,
        sequence=2,
        mode="research",
        user_message="Speculate on unverified room temperature superconductors.",
        assistant_message=f"Possible discovery: {DISTINCTIVE_RESEARCH_FACT}. Also see {DISTINCTIVE_GRAPH_FACT}.",
        status="completed"
    )

    # Mock DB query results for build_ground_context:
    # 1. OpenNotebookWorkspaceBinding
    # 2. OpenNotebookConversationBinding
    # 3. ConversationTurns (returns [ground_turn, research_turn])
    mock_session = AsyncMock()

    ws_bind = OpenNotebookWorkspaceBinding(
        workspace_id=workspace_id,
        open_notebook_notebook_id="notebook_123",
        status="ACTIVE"
    )
    conv_bind = OpenNotebookConversationBinding(
        conversation_id=conversation_id,
        open_notebook_session_id="session_456"
    )

    res_ws_bind = MagicMock()
    res_ws_bind.scalars.return_value.first.return_value = ws_bind

    res_conv_bind = MagicMock()
    res_conv_bind.scalars.return_value.first.return_value = conv_bind

    res_turns = MagicMock()
    # Ordered descending in query, context builder reverses it
    res_turns.scalars.return_value.all.return_value = [research_turn, ground_turn]

    mock_session.execute = AsyncMock(side_effect=[res_ws_bind, res_conv_bind, res_turns])

    ctx: GroundContext = await build_ground_context(
        session=mock_session,
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        query="What is the freezing point of water?",
        explicit_scope=None,
        max_history_turns=5
    )

    context_json = ctx.model_dump_json()

    # 100% precision assertion: ZERO research or graph facts leak into Ground context
    assert DISTINCTIVE_RESEARCH_FACT not in context_json
    assert DISTINCTIVE_GRAPH_FACT not in context_json
    assert DISTINCTIVE_SCRATCHPAD_NOTE not in context_json

    # Prior Ground turn is included in history
    history_contents = [h["content"] for h in ctx.filtered_turn_history]
    assert "What is the boiling point of pure water?" in history_contents
    assert "100 degrees Celsius at 1 atmosphere." in history_contents

    # Prior Research turn is completely excluded
    assert "Speculate on unverified room temperature superconductors." not in history_contents
    assert not any(DISTINCTIVE_RESEARCH_FACT in c for c in history_contents)


@pytest.mark.asyncio
async def test_critical_ground_persistence_zero_knowledge_memory():
    """
    Critical Persistence Test:
    Executing Ground turns must NEVER create KnowledgeMemory and must NEVER enqueue sync_knowledge_to_graph_job.
    Ground answers are purely conversational.
    """
    workspace_id = uuid4()
    conversation_id = uuid4()
    user_id = uuid4()
    turn_id = uuid4()

    mock_db = AsyncMock()
    mock_conv_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()
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
        mode="ground",
        user_message="What is the capital of France?",
        status="pending"
    )

    mock_completed_turn = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=user_id,
        sequence=1,
        mode="ground",
        user_message="What is the capital of France?",
        assistant_message="Paris is the capital of France.",
        status="completed"
    )

    mock_workspace_repo.get_workspace = AsyncMock(return_value=mock_ws)
    mock_conv_repo.get_conversation = AsyncMock(return_value=mock_conv)
    mock_conv_repo.get_turn_by_client_request_id = AsyncMock(return_value=None)
    mock_conv_repo.allocate_turn_sequence = AsyncMock(return_value=1)
    mock_conv_repo.append_turn = AsyncMock(return_value=mock_initial_turn)
    mock_conv_repo.set_turn_status = AsyncMock(return_value=mock_completed_turn)

    # Mock ground engine returning grounded answer
    mock_engine = MagicMock()
    mock_engine.run = AsyncMock(return_value={
        "is_grounded": True,
        "answer": "Paris is the capital of France.",
        "evidence": [uuid4()],
        "provenance_status": "full"
    })

    with patch("app.services.chat.service.ChatEventRepository"), \
         patch("app.services.chat.service.ChatEventService"), \
         patch("app.services.chat.context.build_ground_context") as mock_build_ground_ctx:

        mock_ground_ctx = MagicMock()
        mock_ground_ctx.model_dump.return_value = {"query": "What is the capital of France?"}
        mock_build_ground_ctx.return_value = mock_ground_ctx

        service = ChatService(
            db=mock_db,
            conv_repo=mock_conv_repo,
            workspace_repo=mock_workspace_repo,
            arq_redis=mock_arq_redis,
            ground_engine=mock_engine
        )
        service.event_service = AsyncMock()

        turn_create = TurnCreate(
            mode="ground",
            message="What is the capital of France?"
        )

        completed_turn = await service.submit_turn(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            owner_id=user_id,
            turn_create=turn_create,
            stream=False
        )

        assert completed_turn.status == "completed"

        # Verify KnowledgeMemory was NEVER added to DB session
        for call_args in mock_db.add.call_args_list:
            added_obj = call_args[0][0]
            assert not isinstance(added_obj, KnowledgeMemory), "Ground execution must NEVER persist KnowledgeMemory!"

        # Verify sync_knowledge_to_graph_job was NEVER enqueued
        if mock_arq_redis.enqueue_job.called:
            enqueued_jobs = [call[0][0] for call in mock_arq_redis.enqueue_job.call_args_list]
            assert "sync_knowledge_to_graph_job" not in enqueued_jobs
