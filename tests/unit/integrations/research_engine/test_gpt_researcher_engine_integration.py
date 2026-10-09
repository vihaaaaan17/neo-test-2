"""
GPT-Researcher adapter contract, using a fake `GPTResearcher` (the upstream API surface the adapter relies on:
`conduct_research`, `write_report`, `get_research_sources`, `get_source_urls`, `get_costs`, and the `log_handler` hook).
"""
import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.integrations.research_engine.gpt_researcher.engine import (
    GPTResearcherEngine,
    build_config,
    normalize_sources,
)

TERMINAL = {"completed", "failed", "partial", "cancelled", "aborted_by_timeline_fence"}


class FakeResearcher:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.log_handler = kwargs["log_handler"]
        self.config = json.load(open(kwargs["config_path"]))
        self.config_exists_during_run = os.path.exists(kwargs["config_path"])
        self.fail = False
        self.block = None
        FakeResearcher.instances.append(self)

    async def conduct_research(self):
        # Mirrors GPTResearcher._log_event exactly: the name is passed positionally AND inside **kwargs.
        await self.log_handler.on_agent_action("choose_agent", action="choose_agent")
        await self.log_handler.on_tool_start("tavily_search", tool_name="tavily_search")
        await self.log_handler.on_research_step("searching", {})
        if self.block is not None:
            await self.block.wait()
        if self.fail:
            raise RuntimeError("upstream failure")
        return ["ctx"]

    async def write_report(self, custom_prompt=""):
        self.custom_prompt = custom_prompt
        await self.log_handler.on_research_step("writing_report")
        return "# Report\n\nBody"

    def get_research_sources(self):
        return [
            {"url": "https://a.example", "title": "A", "content": "alpha"},
            {"url": "https://a.example", "title": "dup", "content": "dup"},
            {"title": "no url"},
        ]

    def get_source_urls(self):
        return ["https://a.example", "https://b.example"]

    def get_costs(self):
        return 0.0123


@pytest.fixture(autouse=True)
def _provider():
    FakeResearcher.instances.clear()
    with patch("app.core.config.resolve_llm_provider") as resolve:
        resolve.return_value.api_key = "sk-test"
        resolve.return_value.base_url = "http://localhost:3001/v1"
        resolve.return_value.model = "auto"
        yield


@pytest.mark.asyncio
async def test_gpt_researcher_adapter_yields_progress_then_one_turn_response_and_records_evidence():
    engine = GPTResearcherEngine(researcher_factory=FakeResearcher)
    run_id, workspace_id = uuid4(), uuid4()

    with patch("app.integrations.research_engine.gpt_researcher.engine.record_sources_as_evidence", new_callable=AsyncMock) as evidence, \
         patch.object(GPTResearcherEngine, "_record_usage", new_callable=AsyncMock) as usage:
        events = [e async for e in engine.astream_events(run_id=run_id, workspace_id=workspace_id, objective="What is RAG?")]

    statuses = [e["status"] for e in events]
    assert statuses[0] == "starting"
    assert {"planning", "executing", "synthesizing"} <= set(statuses)
    assert statuses.count("turn_response") == 1 and statuses[-1] == "turn_response"
    assert events[-1]["text"] == "# Report\n\nBody"
    assert not TERMINAL & set(statuses)

    kwargs = evidence.await_args.kwargs
    assert kwargs["run_id"] == run_id and kwargs["workspace_id"] == workspace_id and kwargs["retriever"] == "gpt_researcher"
    assert [s["url"] for s in kwargs["sources"]] == ["https://a.example", "https://b.example"]  # deduplicated, url-less dropped
    usage.assert_awaited_once()


@pytest.mark.asyncio
async def test_gpt_researcher_adapter_configures_through_upstream_config_not_environment():
    engine = GPTResearcherEngine(researcher_factory=FakeResearcher)
    env_before = dict(os.environ)

    with patch("app.integrations.research_engine.gpt_researcher.engine.record_sources_as_evidence", new_callable=AsyncMock), \
         patch.object(GPTResearcherEngine, "_record_usage", new_callable=AsyncMock):
        _ = [e async for e in engine.astream_events(run_id=uuid4(), workspace_id=uuid4(), objective="Objective text")]

    researcher = FakeResearcher.instances[0]
    assert researcher.kwargs["query"] == "Objective text"
    assert researcher.kwargs["report_source"] == "web"
    assert researcher.config["SMART_LLM"] == researcher.config["FAST_LLM"] == researcher.config["STRATEGIC_LLM"] == "openai:auto"
    assert researcher.config["RETRIEVER"] == "tavily"
    assert researcher.config_exists_during_run
    # The conversational answer is requested through GPT-Researcher's own write_report(custom_prompt=...) control.
    assert "Objective text" in researcher.custom_prompt and "conversationally" in researcher.custom_prompt
    assert not os.path.exists(researcher.kwargs["config_path"])  # temp config cleaned up
    assert dict(os.environ) == env_before  # no environment mutation


@pytest.mark.asyncio
async def test_gpt_researcher_adapter_raises_upstream_failures():
    def failing_factory(**kwargs):
        r = FakeResearcher(**kwargs)
        r.fail = True
        return r

    engine = GPTResearcherEngine(researcher_factory=failing_factory)
    seen = []
    with pytest.raises(RuntimeError, match="upstream failure"):
        async for event in engine.astream_events(run_id=uuid4(), workspace_id=uuid4(), objective="x"):
            seen.append(event["status"])
    assert "turn_response" not in seen and not TERMINAL & set(seen)


@pytest.mark.asyncio
async def test_gpt_researcher_adapter_cancellation_stops_the_upstream_task():
    gate = asyncio.Event()

    def blocking_factory(**kwargs):
        r = FakeResearcher(**kwargs)
        r.block = gate
        return r

    engine = GPTResearcherEngine(researcher_factory=blocking_factory)
    got_progress = asyncio.Event()

    async def consume():
        async for event in engine.astream_events(run_id=uuid4(), workspace_id=uuid4(), objective="x"):
            if event["status"] == "executing":
                got_progress.set()

    task = asyncio.create_task(consume())
    await asyncio.wait_for(got_progress.wait(), timeout=5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    await asyncio.sleep(0.1)
    leaked = [t for t in asyncio.all_tasks() if "run_upstream" in repr(t) and not t.done()]
    assert leaked == []  # the upstream task was cancelled with the consumer


def test_build_config_and_normalize_sources():
    cfg = build_config("auto", "auto")
    assert cfg["SMART_LLM"] == "openai:auto" and cfg["EMBEDDING"] == "openai:auto" and cfg["RETRIEVER"] == "tavily"

    import tempfile
    cfg_file = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    cfg_file.write("{}")
    cfg_file.close()
    fake = FakeResearcher(log_handler=MagicMock(), config_path=cfg_file.name)
    out = normalize_sources(fake)
    assert [s["url"] for s in out] == ["https://a.example", "https://b.example"]
    assert out[0]["title"] == "A" and out[0]["content"] == "alpha"
