import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from app.integrations.open_notebook.ground_engine import OpenNotebookGroundEngine
from app.models.open_notebook_binding import OpenNotebookConversationBinding

@pytest.mark.asyncio
async def test_get_or_create_conversation_session_row_locking():
    conv_id = uuid4()
    notebook_id = "nb_test"
    db = AsyncMock()

    # Simulate existing binding found under FOR UPDATE lock
    existing_binding = OpenNotebookConversationBinding(
        conversation_id=conv_id,
        open_notebook_session_id="session:locked_123"
    )
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = existing_binding
    db.execute.return_value = mock_res

    client = AsyncMock()
    engine = OpenNotebookGroundEngine(client=client)

    binding, session_id = await engine._get_or_create_conversation_session(conv_id, notebook_id, db)

    assert session_id == "session:locked_123"
    assert binding.open_notebook_session_id == "session:locked_123"
    # Verify execute was called with row lock (with_for_update)
    executed_stmts = [str(call[0][0]) for call in db.execute.call_args_list]
    assert any("FOR UPDATE" in s for s in executed_stmts)
