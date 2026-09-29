import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.integrations.open_notebook.client import OpenNotebookClient

@pytest.mark.asyncio
async def test_client_chat_stream_yields_incremental_tokens():
    client = OpenNotebookClient(workspace_id="ws_1")
    
    mock_post_context = MagicMock()
    mock_post_context.raise_for_status = MagicMock()
    mock_post_context.json.return_value = {"context": {}}

    mock_post_exec = MagicMock()
    mock_post_exec.raise_for_status = MagicMock()
    mock_post_exec.json.return_value = {
        "messages": [
            {"type": "human", "content": "hello"},
            {"type": "ai", "content": "This is a streaming test answer."}
        ],
        "evidence": ["ev_1"]
    }

    mock_http_client = AsyncMock()
    mock_http_client.post.side_effect = [mock_post_context, mock_post_exec]
    client.http_client = mock_http_client

    events = []
    async for event in client.chat_stream("sess_1", "nb_1", "hello"):
        events.append(event)

    token_events = [e for e in events if e.get("event") == "token"]
    # Verify incremental delivery (more than 1 token chunk for a multi-word answer)
    assert len(token_events) > 1
    reconstructed = "".join(e["data"]["token"] for e in token_events)
    assert reconstructed == "This is a streaming test answer."

    done_event = next(e for e in events if e.get("event") == "done")
    assert done_event["data"]["answer"] == "This is a streaming test answer."
    assert done_event["data"]["evidence"] == ["ev_1"]
