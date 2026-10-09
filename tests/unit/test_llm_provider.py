"""resolve_llm_provider is the single provider-resolution path (Chapter 5, Phase 1, ticket 09)."""
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.config import resolve_llm_provider


def _cfg(**overrides):
    base = dict(
        LLM_PROVIDER="openai",
        OPENAI_API_KEY=None,
        OPENAI_BASE_URL=None,
        OPENAI_MODEL="gpt-4o",
        NVIDIA_API_KEY=None,
        NVIDIA_BASE_URL="https://integrate.api.nvidia.com/v1",
        NVIDIA_MODEL="deepseek-ai/deepseek-v4.1-flash",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_openai_compatible_provider():
    p = resolve_llm_provider(_cfg(OPENAI_API_KEY="sk-1", OPENAI_BASE_URL="http://localhost:3001/v1", OPENAI_MODEL="auto"))
    assert (p.name, p.api_key, p.base_url, p.model) == ("openai", "sk-1", "http://localhost:3001/v1", "auto")


def test_nvidia_provider_when_selected():
    p = resolve_llm_provider(_cfg(LLM_PROVIDER="nvidia", NVIDIA_API_KEY="nv-1", OPENAI_API_KEY="sk-ignored"))
    assert (p.name, p.api_key, p.base_url, p.model) == (
        "nvidia", "nv-1", "https://integrate.api.nvidia.com/v1", "deepseek-ai/deepseek-v4.1-flash"
    )


def test_nvidia_fallback_when_only_nvidia_key_is_set():
    p = resolve_llm_provider(_cfg(LLM_PROVIDER="openai", NVIDIA_API_KEY="nv-only"))
    assert p.name == "nvidia"
    assert p.api_key == "nv-only"


def test_chat_completions_suffix_is_stripped():
    p = resolve_llm_provider(_cfg(OPENAI_API_KEY="k", OPENAI_BASE_URL="http://x/v1/chat/completions"))
    assert p.base_url == "http://x/v1"


def test_missing_key_raises_only_when_required():
    assert resolve_llm_provider(_cfg()).api_key is None
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        resolve_llm_provider(_cfg(), require_key=True)


@pytest.mark.asyncio
async def test_odr_engine_run_does_not_modify_environment():
    from app.integrations.research_engine.open_deep_research.engine import OpenDeepResearchEngine

    async def mock_astream(initial_state, config, stream_mode="updates"):
        yield {"final_report_generation": {"final_report": "report"}}

    graph = MagicMock()
    graph.astream = mock_astream
    with patch("app.integrations.research_engine.upstream.open_deep_research.deep_researcher.deep_researcher_builder.compile",
               return_value=graph):
        engine = OpenDeepResearchEngine()

    before = dict(os.environ)
    with patch("app.core.database.async_session_maker") as session_maker, \
         patch("app.repositories.research.ResearchRepository", return_value=AsyncMock()):
        session_maker.return_value.__aenter__.return_value = AsyncMock()
        events = [e async for e in engine.astream_events(run_id=uuid4(), workspace_id=uuid4(), objective="x")]

    assert events[-1]["status"] == "final_report"
    assert dict(os.environ) == before
