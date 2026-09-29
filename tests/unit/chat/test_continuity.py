import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.conversation import Conversation, ConversationTurn
from app.models.open_notebook_binding import OpenNotebookWorkspaceBinding, OpenNotebookConversationBinding
from app.services.chat.context import build_ground_context, build_research_context


@pytest.mark.asyncio
async def test_multi_turn_ground_research_ground_continuity():
    """
    Scenario: Multi-Turn Conversation with Mode Switching
      Turn 1 (Ground): 'What does Paper A state about Compound Alpha?'
        Assistant: 'Compound Alpha has a verified tensile strength of 450 MPa.'
      Turn 2 (Research): 'Brainstorm hypothetical treatments to increase its strength by 50%.'
        Assistant: 'Hypothesis: Annealing with 2% Nitrogen might increase strength to 675 MPa.'
      Turn 3 (Ground): 'What does Paper B state about the annealing temperature?'

    Verification:
      - For Turn 2 (Research): Research context includes Turn 1 (Ground) so the researcher can explore facts.
      - For Turn 3 (Ground): Ground context includes Turn 1 (Ground), but STRICTLY STRIPS Turn 2 (Research)!
      - The unverified 675 MPa hypothesis never leaks into Turn 3's Ground prompt.
    """
    workspace_id = uuid4()
    conversation_id = uuid4()
    user_id = uuid4()
    now = datetime.now(timezone.utc)

    turn_1_ground = ConversationTurn(
        turn_id=uuid4(),
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=user_id,
        sequence=1,
        mode="ground",
        user_message="What does Paper A state about Compound Alpha?",
        assistant_message="Compound Alpha has a verified tensile strength of 450 MPa.",
        status="completed",
        created_at=now - timedelta(minutes=10)
    )

    turn_2_research = ConversationTurn(
        turn_id=uuid4(),
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=user_id,
        sequence=2,
        mode="research",
        user_message="Brainstorm hypothetical treatments to increase its strength by 50%.",
        assistant_message="Hypothesis: Annealing with 2% Nitrogen might increase strength to 675 MPa.",
        status="completed",
        created_at=now - timedelta(minutes=5)
    )

    # ----------------------------------------------------------------------- #
    # 1. Verify Turn 2 (Research) Context Assembly includes Turn 1
    # ----------------------------------------------------------------------- #
    mock_session_research = AsyncMock()

    # Query results for build_research_context:
    # 1. km_stmt -> []
    # 2. turns_stmt -> [turn_1_ground]
    # 3. ev_stmt -> []
    km_res = MagicMock()
    km_res.scalars.return_value.all.return_value = []

    turns_res_r = MagicMock()
    turns_res_r.scalars.return_value.all.return_value = [turn_1_ground]

    ev_res = MagicMock()
    ev_res.scalars.return_value.all.return_value = []

    mock_session_research.execute = AsyncMock(side_effect=[km_res, turns_res_r, ev_res])

    with patch("app.services.chat.context.ScratchpadRepository") as mock_sp_repo_cls:
        mock_sp_repo = mock_sp_repo_cls.return_value
        mock_sp_repo.list_entries = AsyncMock(return_value=([], 0))

        research_ctx = await build_research_context(
            session=mock_session_research,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            query="Brainstorm hypothetical treatments to increase its strength by 50%.",
            token_budget=8000
        )

        # Research mode is state-aware: includes prior Ground turns in history
        turn_ids_in_research = [t["turn_id"] for t in research_ctx.turn_history]
        assert str(turn_1_ground.turn_id) in turn_ids_in_research
        assert "Compound Alpha has a verified tensile strength of 450 MPa." in research_ctx.turn_history[0]["assistant_message"]

    # ----------------------------------------------------------------------- #
    # 2. Verify Turn 3 (Ground) Context Assembly isolates from Turn 2 (Research)
    # ----------------------------------------------------------------------- #
    mock_session_ground = AsyncMock()

    ws_bind = OpenNotebookWorkspaceBinding(
        workspace_id=workspace_id,
        open_notebook_notebook_id="nb_alpha",
        status="ACTIVE"
    )
    conv_bind = OpenNotebookConversationBinding(
        conversation_id=conversation_id,
        open_notebook_session_id="session_alpha"
    )

    res_ws = MagicMock()
    res_ws.scalars.return_value.first.return_value = ws_bind
    res_conv = MagicMock()
    res_conv.scalars.return_value.first.return_value = conv_bind

    # Prior turns query returns both turn 2 and turn 1 (descending sequence)
    res_turns_g = MagicMock()
    res_turns_g.scalars.return_value.all.return_value = [turn_2_research, turn_1_ground]

    mock_session_ground.execute = AsyncMock(side_effect=[res_ws, res_conv, res_turns_g])

    ground_ctx = await build_ground_context(
        session=mock_session_ground,
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        query="What does Paper B state about the annealing temperature?",
        max_history_turns=5
    )

    ground_ctx_json = ground_ctx.model_dump_json()

    # Ground Turn 1 is present in history
    assert "What does Paper A state about Compound Alpha?" in ground_ctx_json
    assert "Compound Alpha has a verified tensile strength of 450 MPa." in ground_ctx_json

    # Research Turn 2 is completely absent
    assert "Brainstorm hypothetical treatments" not in ground_ctx_json
    assert "675 MPa" not in ground_ctx_json
    assert "Nitrogen" not in ground_ctx_json

    # Exactly 2 history entries (User + Assistant of Turn 1)
    assert len(ground_ctx.filtered_turn_history) == 2
    assert ground_ctx.filtered_turn_history[0]["role"] == "user"
    assert ground_ctx.filtered_turn_history[1]["role"] == "assistant"
