import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.integrations.research_engine.open_deep_research.engine import OpenDeepResearchEngine
from scripts.reconcile_chapter4_state import StateReconciliationEngine
from app.models.research import ResearchRun
from app.models.conversation import ConversationTurn
from app.models.open_notebook_binding import OpenNotebookConversationBinding


@pytest.mark.asyncio
async def test_odr_checkpointer_thread_id_scoping():
    """Verify that OpenDeepResearchEngine scopes thread_id strictly to '{workspace_id}:{run_id}'."""
    engine = OpenDeepResearchEngine()
    workspace_id = uuid.uuid4()
    run_id = uuid.uuid4()

    captured_config = None

    async def fake_astream(state, config, stream_mode):
        nonlocal captured_config
        captured_config = config
        yield {"supervisor": {"final_report": "All done"}}

    mock_graph = MagicMock()
    mock_graph.astream = fake_astream
    engine.graph = mock_graph

    from app.repositories.research import ResearchRepository

    events = []
    with patch.object(ResearchRepository, "list_evidence_for_run", new=AsyncMock(return_value=[])), \
         patch.object(ResearchRepository, "create_usage", new=AsyncMock()):
        async for event in engine.astream_events(
            run_id=run_id,
            workspace_id=workspace_id,
            objective="Analyze distributed consensus",
            research_context=None,
        ):
            events.append(event)

    assert captured_config is not None
    thread_id = captured_config["configurable"]["thread_id"]
    assert thread_id == f"{workspace_id}:{run_id}"
    assert str(workspace_id) in thread_id
    assert str(run_id) in thread_id


@pytest.mark.asyncio
async def test_reconcile_open_notebook_bindings_workspace_isolation():
    """Verify that _reconcile_open_notebook_bindings filters out bindings belonging to other workspaces."""
    mock_session = AsyncMock()
    reconciler = StateReconciliationEngine(session=mock_session)

    target_workspace_id = uuid.uuid4()
    foreign_workspace_id = uuid.uuid4()

    binding_target = OpenNotebookConversationBinding(
        conversation_id=uuid.uuid4(),
        open_notebook_session_id="session_target_1",
    )
    binding_foreign = OpenNotebookConversationBinding(
        conversation_id=uuid.uuid4(),
        open_notebook_session_id="session_foreign_1",
    )

    counts = {
        "ground_conversations_processed": 0,
        "canonical_conversations_created": 0,
        "open_notebook_bindings_reconciled": 0,
        "legacy_ground_memories_quarantined": 0,
        "research_runs_linked": 0,
        "skipped": 0,
        "errors": 0,
    }
    details = []

    # Mock DB query results:
    # 1. select bindings -> returns [binding_target, binding_foreign]
    bindings_res = MagicMock()
    bindings_res.scalars.return_value.all.return_value = [binding_target, binding_foreign]

    # For binding_target:
    # gc_ws_res -> returns target_workspace_id
    # c_res (check if canonical conversation exists) -> returns None
    # gc_res (check if GroundConversation exists) -> returns None
    gc_ws_target = MagicMock()
    gc_ws_target.scalar_one_or_none.return_value = target_workspace_id

    # For binding_foreign:
    # gc_ws_res -> returns foreign_workspace_id (should be skipped because b_ws != target_workspace_id)
    gc_ws_foreign = MagicMock()
    gc_ws_foreign.scalar_one_or_none.return_value = foreign_workspace_id

    c_res_target = MagicMock()
    c_res_target.scalars.return_value.first.return_value = None

    gc_res_target = MagicMock()
    gc_res_target.scalars.return_value.first.return_value = None

    mock_session.execute = AsyncMock(
        side_effect=[
            bindings_res,
            gc_ws_target,
            c_res_target,
            gc_res_target,
            gc_ws_foreign,
        ]
    )

    await reconciler._reconcile_open_notebook_bindings(
        workspace_id=target_workspace_id,
        newly_created_conv_ids=set(),
        counts=counts,
        details=details,
        now_iso="2026-09-29T12:00:00Z",
    )

    # Foreign binding was skipped without incrementing counts or attempting to load canonical/ground
    # Target binding was processed (and skipped because no ground conversation was found)
    assert counts["open_notebook_bindings_reconciled"] == 0
    assert counts["skipped"] == 1
    assert any("no matching GroundConversation" in d for d in details)


@pytest.mark.asyncio
async def test_link_historical_research_runs_strict_workspace_scoping():
    """Verify that historical research runs are only linked to turns in the same workspace."""
    mock_session = AsyncMock()
    reconciler = StateReconciliationEngine(session=mock_session)

    workspace_id = uuid.uuid4()
    foreign_workspace_id = uuid.uuid4()

    run = ResearchRun(
        run_id=uuid.uuid4(),
        workspace_id=workspace_id,
        owner_id=uuid.uuid4(),
        objective="Analyze consensus",
        status="completed",
        engine="open_deep_research",
        conversation_id=None,
        turn_id=None,
    )

    # 1. First query: find unlinked runs -> [run]
    runs_res = MagicMock()
    runs_res.scalars.return_value.all.return_value = [run]

    # 2. Second query: turn matching run_id AND matching workspace_id -> returns matching turn
    turn = ConversationTurn(
        turn_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        workspace_id=workspace_id,
        owner_id=uuid.uuid4(),
        sequence=1,
        mode="research",
        status="completed",
        user_message="test",
        research_run_id=run.run_id,
    )
    turn_res = MagicMock()
    turn_res.scalars.return_value.first.return_value = turn

    mock_session.execute = AsyncMock(side_effect=[runs_res, turn_res])

    counts = {
        "ground_conversations_processed": 0,
        "canonical_conversations_created": 0,
        "open_notebook_bindings_reconciled": 0,
        "legacy_ground_memories_quarantined": 0,
        "research_runs_linked": 0,
        "skipped": 0,
        "errors": 0,
    }
    details = []

    await reconciler._link_historical_research_runs(
        workspace_id=workspace_id,
        counts=counts,
        details=details,
    )

    assert counts["research_runs_linked"] == 1
    assert run.turn_id == turn.turn_id
    assert run.conversation_id == turn.conversation_id
