"""neosis_web_search is the bridge where ODR search results enter Neosis evidence/provenance and usage tracking."""
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.integrations.research_engine.tools import neosis_search_tools as tools_mod
from app.integrations.research_engine.tools.neosis_search_tools import neosis_web_search


def _config(run_id, workspace_id, tracker):
    return {
        "configurable": {"usage_tracker": tracker},
        "metadata": {"run_id": str(run_id), "owner": str(workspace_id)},
    }


@pytest.mark.asyncio
async def test_search_persists_evidence_with_provenance_and_counts_usage(monkeypatch):
    run_id, workspace_id = uuid4(), uuid4()
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    client = MagicMock()
    client.search = AsyncMock(return_value={"results": [
        {"url": "https://a.example/1", "title": "A", "content": "alpha", "raw_content": "alpha raw", "score": 0.9},
        {"url": "https://a.example/1", "title": "A dup", "content": "dup"},  # duplicate URL is ignored
        {"url": "https://b.example/2", "title": "B", "content": "beta", "score": 0.5},
    ]})

    repo = MagicMock()
    repo._verify_run_workspace = AsyncMock()
    repo.create_evidence = AsyncMock()

    @asynccontextmanager
    async def fake_session_maker():
        yield MagicMock()

    tracker = MagicMock()

    with patch.object(tools_mod, "AsyncTavilyClient", return_value=client), \
         patch.object(tools_mod, "async_session_maker", fake_session_maker), \
         patch.object(tools_mod, "ResearchRepository", return_value=repo):
        output = await neosis_web_search.ainvoke(
            {"queries": ["what is x"]}, config=_config(run_id, workspace_id, tracker)
        )

    tracker.add_search_call.assert_called_once()
    assert "https://a.example/1" in output and "https://b.example/2" in output
    assert repo.create_evidence.await_count == 2  # duplicate URL collapsed

    first = repo.create_evidence.await_args_list[0].kwargs
    assert first["workspace_id"] == workspace_id and first["run_id"] == run_id
    assert first["locator"] == "https://a.example/1"
    assert first["retriever"] == "tavily_web_search"
    assert first["provenance"] == {"title": "A", "url": "https://a.example/1"}
    assert first["source_resolution_status"] == "unresolved_external"


@pytest.mark.asyncio
async def test_search_without_execution_context_does_not_search(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    with patch.object(tools_mod, "AsyncTavilyClient") as client_cls:
        output = await neosis_web_search.ainvoke(
            {"queries": ["q"]}, config={"configurable": {}, "metadata": {}}
        )
    assert output.startswith("Error: Missing execution context")
    client_cls.assert_not_called()
