"""
Shared engine contract, run against all three adapters (Open Deep Research, STORM, GPT-Researcher), each over a
deterministic stand-in for its upstream runtime. Every engine must: yield progress events then exactly one
`turn_response`, never a terminal status; carry the run identity into evidence persistence; signal failure by
raising; and stop its upstream work when the consuming task is cancelled.
"""
import asyncio
import contextlib
import json
import sys
import textwrap
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.integrations.research_engine.engine import SUPPORTED_ENGINES
from app.integrations.research_engine.factory import ResearchEngineFactory

TERMINAL = {"completed", "failed", "partial", "cancelled", "aborted_by_timeline_fence"}
PREFIX = "@@NEOSIS@@"

_HEAD = f"import json, sys, time\njob = json.load(sys.stdin)\ndef emit(t, **d): print({PREFIX!r} + json.dumps({{'type': t, **d}}), flush=True)\n"
STORM_SCRIPTS = {
    "ok": _HEAD + (
        "emit('phase', phase='executing', message='working')\n"
        "emit('result', article='# ' + job['topic'], sources=[{'index': 1, 'url': 'https://a.example', 'title': 'A', 'snippets': ['s']}], usage={})\n"
    ),
    "fail": _HEAD + "emit('error', message='upstream failure')\nsys.exit(1)\n",
    "slow": _HEAD + "emit('phase', phase='executing', message='working')\ntime.sleep(60)\n",
}


class FakeResearcher:
    mode = "ok"
    gate = None

    def __init__(self, **kwargs):
        self.log_handler = kwargs["log_handler"]
        self.query = kwargs["query"]

    async def conduct_research(self):
        await self.log_handler.on_research_step("searching")
        if FakeResearcher.gate is not None:
            await FakeResearcher.gate.wait()
        if FakeResearcher.mode == "fail":
            raise RuntimeError("upstream failure")

    async def write_report(self, custom_prompt=""):
        return f"# {self.query}"

    def get_research_sources(self):
        return [{"url": "https://a.example", "title": "A", "content": "alpha"}]

    def get_source_urls(self):
        return ["https://a.example"]

    def get_costs(self):
        return 0.0


def _provider():
    resolve = patch("app.core.config.resolve_llm_provider")
    mock = resolve.start()
    mock.return_value.api_key, mock.return_value.base_url, mock.return_value.model = "k", "http://x/v1", "auto"
    return resolve


@contextlib.contextmanager
def _engine(name, tmp_path, scenario="ok"):
    """Yield (engine, evidence_handle) with the upstream runtime replaced by a deterministic stand-in."""
    if name == "storm":
        from app.integrations.research_engine.storm.engine import StormResearchEngine

        path = tmp_path / "runner.py"
        path.write_text(STORM_SCRIPTS[scenario])
        provider = _provider()
        try:
            with patch("app.integrations.research_engine.storm.engine.record_sources_as_evidence", new_callable=AsyncMock) as ev, \
                 patch.object(StormResearchEngine, "_record_usage", new_callable=AsyncMock):
                yield StormResearchEngine(python_executable=sys.executable, runner_path=str(path)), ev
        finally:
            provider.stop()
    elif name == "gpt_researcher":
        from app.integrations.research_engine.gpt_researcher.engine import GPTResearcherEngine

        FakeResearcher.mode = "fail" if scenario == "fail" else "ok"
        FakeResearcher.gate = asyncio.Event() if scenario == "slow" else None
        provider = _provider()
        try:
            with patch("app.integrations.research_engine.gpt_researcher.engine.record_sources_as_evidence", new_callable=AsyncMock) as ev, \
                 patch.object(GPTResearcherEngine, "_record_usage", new_callable=AsyncMock):
                yield GPTResearcherEngine(researcher_factory=FakeResearcher), ev
        finally:
            provider.stop()
    else:
        from app.integrations.research_engine.open_deep_research.engine import OpenDeepResearchEngine
        from tests.harness.odr_offline import offline_odr

        with offline_odr("Contract objective") as rec:
            yield OpenDeepResearchEngine(), rec


def _evidence_scopes(name, handle):
    if name == "open_deep_research":
        return [(e["run_id"], e["workspace_id"]) for e in handle.evidence]
    return [(c.kwargs["run_id"], c.kwargs["workspace_id"]) for c in handle.await_args_list]


@pytest.mark.parametrize("name", SUPPORTED_ENGINES)
def test_factory_resolves_every_supported_engine(name):
    assert ResearchEngineFactory.get_engine(engine_name=name) is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("name", SUPPORTED_ENGINES)
async def test_contract_progress_then_exactly_one_turn_response_with_run_identity(name, tmp_path):
    run_id, workspace_id = uuid4(), uuid4()
    with _engine(name, tmp_path) as (engine, handle):
        events = [e async for e in engine.astream_events(run_id=run_id, workspace_id=workspace_id, objective="Contract objective")]

    statuses = [e["status"] for e in events]
    assert statuses[0] == "starting"
    assert statuses.count("turn_response") == 1 and statuses[-1] == "turn_response"
    assert not TERMINAL & set(statuses)  # the worker, not the engine, owns terminal state
    assert isinstance(events[-1]["text"], str) and "Contract objective" in events[-1]["text"]

    # Evidence is persisted through Neosis, scoped to this run and workspace (no bypass of provenance).
    scopes = _evidence_scopes(name, handle)
    assert scopes and all(s == (run_id, workspace_id) for s in scopes)


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["storm", "gpt_researcher"])
async def test_contract_failure_is_raised_not_yielded(name, tmp_path):
    seen = []
    with _engine(name, tmp_path, "fail") as (engine, _):
        with pytest.raises(RuntimeError, match="upstream failure"):
            async for e in engine.astream_events(run_id=uuid4(), workspace_id=uuid4(), objective="x"):
                seen.append(e["status"])
    assert "turn_response" not in seen and not TERMINAL & set(seen)


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["storm", "gpt_researcher"])
async def test_contract_cancellation_stops_the_consumer_and_upstream(name, tmp_path):
    with _engine(name, tmp_path, "slow") as (engine, _):
        progressed = asyncio.Event()

        async def consume():
            async for e in engine.astream_events(run_id=uuid4(), workspace_id=uuid4(), objective="x"):
                if e["status"] == "executing":
                    progressed.set()

        task = asyncio.create_task(consume())
        await asyncio.wait_for(progressed.wait(), timeout=20)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0.1)
        if name == "storm":
            assert engine._proc is None
        else:
            assert not [t for t in asyncio.all_tasks() if "run_upstream" in repr(t) and not t.done()]
