import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.integrations.open_notebook.ground_engine import OpenNotebookGroundEngine
from app.models.open_notebook_binding import OpenNotebookWorkspaceBinding, OpenNotebookConversationBinding

@pytest.mark.asyncio
async def test_ground_engine_source_scope_injected_into_context_config():
    workspace_id = uuid4()
    conv_id = uuid4()
    source1 = uuid4()
    on_source1_id = "on_source_1"

    mock_db = AsyncMock()
    mock_client = AsyncMock()

    mock_ws_binding = OpenNotebookWorkspaceBinding(
        workspace_id=workspace_id,
        open_notebook_notebook_id="notebook:123",
        status="active"
    )
    mock_conv_binding = OpenNotebookConversationBinding(
        conversation_id=conv_id,
        open_notebook_session_id="session:123"
    )

    engine = OpenNotebookGroundEngine(workspace_id=workspace_id, client=mock_client)
    engine._get_active_binding = AsyncMock(return_value=mock_ws_binding)
    engine._get_or_create_conversation_session = AsyncMock(return_value=(mock_conv_binding, "session:123"))

    mock_client.search.return_value = [{"id": on_source1_id}]
    mock_client.chat_execute.return_value = {"answer": "Grounded answer", "evidence": [on_source1_id]}

    with patch("app.integrations.open_notebook.ground_engine.map_canonical_sources_to_upstream", new_callable=AsyncMock) as mock_map_up, \
         patch("app.integrations.open_notebook.ground_engine.resolve_ground_evidence", new_callable=AsyncMock) as mock_map_cit:
        mock_map_up.return_value = [on_source1_id]
        mock_map_cit.return_value = {"source_ids": [source1], "evidence": [], "unresolved": [], "provenance_status": "full"}

        result = await engine.run(
            workspace_id=workspace_id,
            conversation_id=conv_id,
            query="test query",
            db=mock_db,
            source_scope=[source1]
        )

        assert result["is_grounded"] is True
        assert result["answer"] == "Grounded answer"
        mock_map_up.assert_awaited_once_with([source1], workspace_id, mock_db)
        
        # Verify context_config was passed with the mapped source IDs
        mock_client.chat_execute.assert_awaited_once()
        call_kwargs = mock_client.chat_execute.call_args.kwargs
        assert "context_config" in call_kwargs
        assert call_kwargs["context_config"] == {"sources": {on_source1_id: "full content"}}
        assert mock_map_cit.await_args.kwargs["source_scope"] == [source1]  # resolution is filtered by the same scope

@pytest.mark.asyncio
async def test_ground_engine_source_scope_fails_closed_when_unmapped():
    workspace_id = uuid4()
    conv_id = uuid4()
    unmapped_source = uuid4()

    mock_db = AsyncMock()
    mock_client = AsyncMock()

    mock_ws_binding = OpenNotebookWorkspaceBinding(
        workspace_id=workspace_id,
        open_notebook_notebook_id="notebook:123",
        status="active"
    )
    engine = OpenNotebookGroundEngine(workspace_id=workspace_id, client=mock_client)
    engine._get_active_binding = AsyncMock(return_value=mock_ws_binding)

    with patch("app.integrations.open_notebook.ground_engine.map_canonical_sources_to_upstream", new_callable=AsyncMock) as mock_map_up:
        mock_map_up.return_value = [] # No upstream mapping found

        with pytest.raises(HTTPException) as exc_info:
            await engine.run(
                workspace_id=workspace_id,
                conversation_id=conv_id,
                query="test query",
                db=mock_db,
                source_scope=[unmapped_source]
            )
        assert exc_info.value.status_code == 422
        assert "ground_provenance_failure" in str(exc_info.value.detail)
