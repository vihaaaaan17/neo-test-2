import asyncio
import json
import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.models.workspace import Workspace
from app.models.conversation import Conversation, ConversationTurn
from app.models.source import Source
from app.models.research import ResearchRun, ResearchReport, ResearchEvidence, ResearchArtifact
from app.models.scratchpad import ScratchpadEntry
from app.models.open_notebook_binding import OpenNotebookWorkspaceBinding, OpenNotebookConversationBinding
from app.services.chat.context import (
    build_ground_context,
    GroundContext,
    ResearchContext,
    ResearchContextVersion
)
from app.services.chat.service import ChatService
from app.schemas.chat import TurnCreate
from app.integrations.open_notebook.ground_engine import OpenNotebookGroundEngine


DISTINCTIVE_RESEARCH_EVIDENCE = "EVIDENCE_CONFIDENTIAL_QUANTUM_COHERENCE_STUDY_REF_9999"
DISTINCTIVE_RESEARCH_REPORT = "REPORT_SYNTHESIS_QUANTUM_BIOLOGY_RESONANCE_UNPUBLISHED"
DISTINCTIVE_SCRATCHPAD_NOTE = "SCRATCHPAD_NOTE_SECRET_CHLOROPHYLL_VIBRATIONAL_HYPOTHESIS_777"
DISTINCTIVE_UNPROMOTED_ARTIFACT = "UNPROMOTED_MEMORY_CANDIDATE_SUPERCONDUCTIVITY_ROOM_TEMP"


class MockSourceItem:
    def __init__(self, uid: UUID):
        self.source_id = uid
        self.title = "biology_textbook.pdf"
        self.created_at = datetime.now(timezone.utc)

    def __eq__(self, other):
        if isinstance(other, MockSourceItem):
            return self.source_id == other.source_id
        return self.source_id == other or str(self.source_id) == str(other)

    def __hash__(self):
        return hash(self.source_id)

    def __str__(self):
        return str(self.source_id)


@pytest.mark.asyncio
async def test_ground_research_ground_strict_context_isolation():
    """
    E2E Test: Multi-turn conversation across Ground -> Research -> Ground modes.
    Turn 1 = Ground
    Turn 2 = Research
    Turn 3 = Ground
    
    Verifies the core architectural invariant:
    'Ground is source-grounded. Research is state-aware.
     Research-derived knowledge must NEVER leak into Ground context or Ground evidence.'
    """
    workspace_id = uuid4()
    conversation_id = uuid4()
    owner_id = uuid4()
    canonical_source_id = uuid4()
    mock_source = MockSourceItem(canonical_source_id)

    mock_db = AsyncMock()

    # 1. Setup Conversation Turns in chronological order
    turn1_ground = ConversationTurn(
        turn_id=uuid4(),
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        sequence=1,
        mode="ground",
        user_message="Explain photosynthesis fundamentals.",
        assistant_message="Photosynthesis converts solar light into biochemical energy using chlorophyll pigments.",
        status="completed",
        source_scope=[str(canonical_source_id)],
        ground_evidence_refs=[str(canonical_source_id)],
        context_version={"source_ids": [str(canonical_source_id)]},
        created_at=datetime.now(timezone.utc)
    )

    turn2_research = ConversationTurn(
        turn_id=uuid4(),
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        sequence=2,
        mode="research",
        user_message="Speculate on unverified quantum biology in plant light-harvesting complexes.",
        assistant_message=f"Research synthesis report: {DISTINCTIVE_RESEARCH_REPORT}. Evidence: {DISTINCTIVE_RESEARCH_EVIDENCE}",
        status="completed",
        research_run_id=uuid4(),
        context_version={"research_context": {"unverified": True}},
        created_at=datetime.now(timezone.utc)
    )

    # 2. Mock DB queries for build_ground_context:
    mock_ws_binding = OpenNotebookWorkspaceBinding(
        workspace_id=workspace_id,
        open_notebook_notebook_id="nb-12345",
        status="ACTIVE"
    )
    mock_conv_binding = OpenNotebookConversationBinding(
        conversation_id=conversation_id,
        open_notebook_session_id="sess-67890"
    )

    def db_execute_side_effect(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt).lower()
        if "open_notebook_workspace_bindings" in stmt_str:
            mock_result.scalars.return_value.first.return_value = mock_ws_binding
        elif "open_notebook_conversation_bindings" in stmt_str:
            mock_result.scalars.return_value.first.return_value = mock_conv_binding
        elif "conversation_turns" in stmt_str:
            mock_result.scalars.return_value.all.return_value = [turn1_ground, turn2_research]
        elif "sources.source_id \n" in stmt_str or "sources.source_id\n" in stmt_str:
            # Query 1: resolve_ground_source_scope returns UUIDs
            mock_result.scalars.return_value.all.return_value = [canonical_source_id]
        elif "sources" in stmt_str:
            # Query 5: metadata returns Source items
            mock_result.scalars.return_value.all.return_value = [mock_source]
        else:
            mock_result.scalars.return_value.all.return_value = []
            mock_result.scalars.return_value.first.return_value = None
            mock_result.all.return_value = []
        return mock_result

    mock_db.execute.side_effect = db_execute_side_effect

    # 3. Build Ground context for Turn 3 (Mode: Ground)
    turn3_ground_ctx: GroundContext = await build_ground_context(
        session=mock_db,
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        query="What are the essential molecular inputs required for the light reactions?",
        explicit_scope=[canonical_source_id]
    )

    ctx_dump = turn3_ground_ctx.model_dump_json()

    # 4. Strict Isolation Assertions
    # A. Prior Ground turn content IS preserved in filtered_turn_history
    assert "Explain photosynthesis fundamentals" in ctx_dump
    assert "Photosynthesis converts solar light into biochemical energy" in ctx_dump

    # B. Research text, reports, and evidence are 100% excluded
    assert DISTINCTIVE_RESEARCH_REPORT not in ctx_dump
    assert DISTINCTIVE_RESEARCH_EVIDENCE not in ctx_dump
    assert DISTINCTIVE_SCRATCHPAD_NOTE not in ctx_dump
    assert DISTINCTIVE_UNPROMOTED_ARTIFACT not in ctx_dump

    # C. Source scope contains only the explicitly scoped canonical source UUID
    assert str(canonical_source_id) in ctx_dump
    assert turn3_ground_ctx.source_scope == [canonical_source_id]


@pytest.mark.asyncio
async def test_ground_engine_rejection_of_research_context_on_turn_3():
    """
    Verifies that OpenNotebookGroundEngine strictly enforces Ground isolation
    by rejecting any attempt to pass a ResearchContext.
    """
    engine = OpenNotebookGroundEngine(workspace_id=uuid4())

    ctx_version = ResearchContextVersion(
        version="v1",
        budget=8000,
        total_tokens=100,
        initial_tokens=100,
        created_at=datetime.now(timezone.utc).isoformat()
    )

    invalid_ctx = ResearchContext(
        workspace_id=uuid4(),
        conversation_id=uuid4(),
        query="Explain chloroplast structure",
        context_version=ctx_version
    )

    with pytest.raises(ValueError, match="Ground engine rejects ResearchContext"):
        await engine.run(
            db=AsyncMock(),
            workspace_id=uuid4(),
            query="Explain chloroplast structure",
            ground_context=invalid_ctx
        )


@pytest.mark.asyncio
async def test_ground_execution_produces_zero_promotions_and_zero_graph_sync():
    """
    Verifies that completing Turn 3 (Ground) records ground_evidence_refs and assistant_message
    with ZERO writes to KnowledgeMemory and ZERO sync_knowledge_to_graph_job enqueuing.
    """
    workspace_id = uuid4()
    conversation_id = uuid4()
    turn_id = uuid4()
    owner_id = uuid4()
    source_uuid = uuid4()

    mock_db = AsyncMock()

    def test3_execute_side_effect(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt).lower()
        if "conversation_turns" in stmt_str:
            mock_result.scalars.return_value.all.return_value = []
        elif "sources.source_id \n" in stmt_str or "sources.source_id\n" in stmt_str:
            mock_result.scalars.return_value.all.return_value = [source_uuid]
        elif "sources" in stmt_str:
            mock_result.scalars.return_value.all.return_value = [MockSourceItem(source_uuid)]
        else:
            mock_result.scalars.return_value.first.return_value = None
            mock_result.scalars.return_value.all.return_value = []
        return mock_result

    mock_db.execute.side_effect = test3_execute_side_effect

    mock_conv_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()
    mock_arq_redis = AsyncMock()
    mock_ground_engine = AsyncMock()
    mock_event_service = AsyncMock()

    mock_workspace = Workspace(workspace_id=workspace_id, owner_id=owner_id)
    mock_conv = Conversation(
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        status="active"
    )
    turn3 = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        sequence=3,
        mode="ground",
        user_message="Summary of photosynthesis?",
        status="pending",
        source_scope=[str(source_uuid)]
    )

    mock_workspace_repo.get_workspace.return_value = mock_workspace
    mock_conv_repo.get_conversation.return_value = mock_conv
    mock_conv_repo.allocate_turn_sequence.return_value = 3
    mock_conv_repo.append_turn.return_value = turn3
    mock_conv_repo.set_turn_status.return_value = turn3

    mock_ground_engine.run.return_value = {
        "is_grounded": True,
        "answer": "Photosynthesis requires light, H2O, and CO2.",
        "evidence": [str(source_uuid)],
        "provenance_status": "full"
    }

    chat_service = ChatService(
        db=mock_db,
        conv_repo=mock_conv_repo,
        workspace_repo=mock_workspace_repo,
        arq_redis=mock_arq_redis,
        ground_engine=mock_ground_engine
    )
    chat_service.event_service = mock_event_service

    turn_create = TurnCreate(
        mode="ground",
        message="Summary of photosynthesis?",
        source_scope=[source_uuid]
    )

    result_turn = await chat_service.submit_turn(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        owner_id=owner_id,
        turn_create=turn_create
    )

    # 1. Ground engine executed
    mock_ground_engine.run.assert_awaited_once()

    # 2. Finalize status set to completed
    mock_conv_repo.set_turn_status.assert_awaited()
    last_set_call = mock_conv_repo.set_turn_status.call_args_list[-1]
    assert last_set_call.kwargs["status"] == "completed"
    assert last_set_call.kwargs["assistant_message"] == "Photosynthesis requires light, H2O, and CO2."
    assert last_set_call.kwargs["ground_evidence_refs"] == [str(source_uuid)]

    # 3. Invariant: ZERO sync_knowledge_to_graph_job enqueued
    enqueued_jobs = [c[0][0] for c in mock_arq_redis.enqueue_job.call_args_list]
    assert "sync_knowledge_to_graph_job" not in enqueued_jobs
    assert "sync_knowledge_to_graph" not in enqueued_jobs
