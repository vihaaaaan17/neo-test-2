import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.models.conversation import ConversationTurn
from app.models.open_notebook_binding import OpenNotebookConversationBinding, OpenNotebookWorkspaceBinding
from app.services.chat.context import build_ground_context, resolve_ground_source_scope


@pytest.mark.asyncio
async def test_build_ground_context_strips_research_turns():
    """
    In a mixed-mode conversation:
      Turn 1: Ground ("What is in doc A?", "Doc A contains factual finding.")
      Turn 2: Research ("Search web for trends", "Web claims 18% efficiency increase.")
      Turn 3: Ground ("Summarize our discussion.")
    build_ground_context MUST include Turn 1 and completely exclude Turn 2.
    """
    workspace_id = uuid4()
    conversation_id = uuid4()

    turn1 = ConversationTurn(
        turn_id=uuid4(),
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=uuid4(),
        sequence=1,
        mode="ground",
        user_message="What is in doc A?",
        assistant_message="Doc A contains factual finding.",
        status="completed"
    )

    turn2 = ConversationTurn(
        turn_id=uuid4(),
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=uuid4(),
        sequence=2,
        mode="research",
        user_message="Search web for trends",
        assistant_message="Web claims 18% efficiency increase.",
        status="completed"
    )

    ws_binding = OpenNotebookWorkspaceBinding(
        workspace_id=workspace_id,
        open_notebook_notebook_id="nb-123",
        status="active"
    )
    conv_binding = OpenNotebookConversationBinding(
        conversation_id=conversation_id,
        open_notebook_session_id="sess-456"
    )

    session = AsyncMock()

    # Mock DB queries:
    # 1. ws_binding query
    # 2. conv_binding query
    # 3. turns query
    def mock_execute(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt).lower()
        if "open_notebook_workspace_bindings" in stmt_str:
            mock_res.scalars.return_value.first.return_value = ws_binding
        elif "open_notebook_conversation_bindings" in stmt_str:
            mock_res.scalars.return_value.first.return_value = conv_binding
        elif "conversation_turns" in stmt_str:
            mock_res.scalars.return_value.all.return_value = [turn2, turn1]  # descending sequence order from DB
        else:
            mock_res.scalars.return_value.all.return_value = []
            mock_res.scalars.return_value.first.return_value = None
        return mock_res

    session.execute.side_effect = mock_execute

    ground_ctx = await build_ground_context(
        session=session,
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        query="Summarize our discussion."
    )

    assert ground_ctx.workspace_id == workspace_id
    assert ground_ctx.conversation_id == conversation_id
    assert ground_ctx.notebook_id == "nb-123"
    assert ground_ctx.session_id == "sess-456"

    # Turn history must contain ONLY Turn 1
    messages = ground_ctx.filtered_turn_history
    assert len(messages) == 2
    assert messages[0] == {"role": "user", "content": "What is in doc A?"}
    assert messages[1] == {"role": "assistant", "content": "Doc A contains factual finding."}

    # Verify Turn 2's research content is 100% absent
    all_content_str = " ".join([m["content"] for m in messages])
    assert "Search web for trends" not in all_content_str
    assert "18% efficiency increase" not in all_content_str


@pytest.mark.asyncio
async def test_resolve_ground_source_scope():
    workspace_id = uuid4()
    source1 = uuid4()
    source2 = uuid4()

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [source1, source2]
    session.execute.return_value = mock_res

    resolved = await resolve_ground_source_scope(
        session=session,
        workspace_id=workspace_id,
        explicit_scope=[source1, source2]
    )

    assert resolved == [source1, source2]
