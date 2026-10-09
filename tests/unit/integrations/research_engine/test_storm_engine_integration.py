"""
STORM adapter contract. A stand-in runner script (speaking the same stdout line protocol) replaces the real
`knowledge_storm` process, so these tests need neither the STORM environment nor a network.
"""
import asyncio
import json
import sys
import textwrap
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.integrations.research_engine.storm.engine import (
    PROTOCOL_PREFIX,
    StormResearchEngine,
    format_storm_report,
)

TERMINAL = {"completed", "failed", "partial", "cancelled", "aborted_by_timeline_fence"}


def _write_runner(tmp_path, body: str) -> str:
    script = tmp_path / "fake_runner.py"
    script.write_text(textwrap.dedent(body))
    return str(script)


GOOD_RUNNER = f'''
import json, sys
job = json.load(sys.stdin)
def emit(t, **d):
    print({PROTOCOL_PREFIX!r} + json.dumps({{"type": t, **d}}), flush=True)
print("noise that is not protocol", flush=True)
emit("phase", phase="planning", message="Starting STORM")
emit("phase", phase="executing", message="Researching")
emit("phase", phase="synthesizing", message="Writing")
emit("result", article="# " + job["topic"] + "\\n\\nBody [1] and [2].",
     sources=[{{"index": 1, "url": "https://a.example/1", "title": "A", "description": "d", "snippets": ["s1"]}},
              {{"index": 2, "url": "https://b.example/2", "title": "B", "description": "d", "snippets": ["s2"]}}],
     usage={{"model_calls": 7, "input_tokens": 100, "output_tokens": 50}}, output_dir="x")
'''


@pytest.fixture(autouse=True)
def _job_inputs(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "TAVILY_API_KEY", "tvly-test")  # the configured key wins over the environment
    with patch("app.core.config.resolve_llm_provider") as resolve:
        resolve.return_value.api_key = "sk-test"
        resolve.return_value.base_url = "http://localhost:3001/v1"
        resolve.return_value.model = "auto"
        yield


def _engine(tmp_path, body):
    return StormResearchEngine(python_executable=sys.executable, runner_path=_write_runner(tmp_path, body))


@pytest.mark.asyncio
async def test_storm_adapter_yields_progress_then_one_turn_response_and_records_evidence(tmp_path):
    engine = _engine(tmp_path, GOOD_RUNNER)
    run_id, workspace_id = uuid4(), uuid4()

    with patch("app.integrations.research_engine.storm.engine.record_sources_as_evidence", new_callable=AsyncMock) as evidence, \
         patch.object(StormResearchEngine, "_record_usage", new_callable=AsyncMock) as usage:
        evidence.return_value = 2
        events = [e async for e in engine.astream_events(run_id=run_id, workspace_id=workspace_id, objective="Topic X")]

    statuses = [e["status"] for e in events]
    assert statuses[0] == "starting"
    assert {"planning", "executing", "synthesizing"} <= set(statuses)
    assert statuses.count("turn_response") == 1 and statuses[-1] == "turn_response"
    assert not TERMINAL & set(statuses)

    assert events[-1]["format"] == "article"  # STORM has no conversational output control
    report = events[-1]["text"]
    assert report.startswith("# Topic X") and "### Sources" in report
    assert "[1] A: https://a.example/1" in report and "[2] B: https://b.example/2" in report

    # Sources went through Neosis evidence persistence, scoped to this run/workspace.
    kwargs = evidence.await_args.kwargs
    assert kwargs["run_id"] == run_id and kwargs["workspace_id"] == workspace_id
    assert kwargs["retriever"] == "storm" and [s["url"] for s in kwargs["sources"]] == ["https://a.example/1", "https://b.example/2"]
    usage.assert_awaited_once()
    assert usage.await_args.args[2]["model_calls"] == 7


@pytest.mark.asyncio
async def test_storm_adapter_passes_objective_provider_and_credentials_to_runner(tmp_path):
    echo = f'''
import json, sys
job = json.load(sys.stdin)
print({PROTOCOL_PREFIX!r} + json.dumps({{"type": "result", "article": json.dumps(job), "sources": [], "usage": {{}}}}), flush=True)
'''
    engine = _engine(tmp_path, echo)
    with patch("app.integrations.research_engine.storm.engine.record_sources_as_evidence", new_callable=AsyncMock), \
         patch.object(StormResearchEngine, "_record_usage", new_callable=AsyncMock):
        events = [e async for e in engine.astream_events(run_id=uuid4(), workspace_id=uuid4(), objective="Quantum dots")]

    job = json.loads(events[-1]["text"])
    assert job["topic"] == "Quantum dots"
    assert job["llm"] == {"model": "auto", "api_key": "sk-test", "base_url": "http://localhost:3001/v1"}
    assert job["tavily_api_key"] == "tvly-test"
    assert job["args"]["max_conv_turn"] == 3  # STORM's own defaults


@pytest.mark.asyncio
async def test_storm_adapter_raises_when_runner_fails(tmp_path):
    failing = f'''
import json, sys
json.load(sys.stdin)
print({PROTOCOL_PREFIX!r} + json.dumps({{"type": "error", "message": "boom from storm"}}), flush=True)
sys.exit(1)
'''
    engine = _engine(tmp_path, failing)
    seen = []
    with pytest.raises(RuntimeError, match="boom from storm"):
        async for event in engine.astream_events(run_id=uuid4(), workspace_id=uuid4(), objective="x"):
            seen.append(event["status"])
    assert seen == ["starting"]


@pytest.mark.asyncio
async def test_storm_adapter_raises_when_runner_exits_without_result(tmp_path):
    engine = _engine(tmp_path, "import sys, json\njson.load(sys.stdin)\nprint('only noise')\n")
    with pytest.raises(RuntimeError, match="STORM runner failed"):
        async for _ in engine.astream_events(run_id=uuid4(), workspace_id=uuid4(), objective="x"):
            pass


@pytest.mark.asyncio
async def test_storm_adapter_cancellation_terminates_the_process(tmp_path):
    slow = f'''
import json, sys, time
json.load(sys.stdin)
print({PROTOCOL_PREFIX!r} + json.dumps({{"type": "phase", "phase": "executing", "message": "working"}}), flush=True)
time.sleep(60)
'''
    engine = _engine(tmp_path, slow)
    got_phase = asyncio.Event()

    async def consume():
        async for event in engine.astream_events(run_id=uuid4(), workspace_id=uuid4(), objective="x"):
            if event["status"] == "executing":
                got_phase.set()

    task = asyncio.create_task(consume())
    await asyncio.wait_for(got_phase.wait(), timeout=20)
    proc = engine._proc
    assert proc is not None and proc.returncode is None

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert proc.returncode is not None  # the STORM process was terminated, not left running
    assert engine._proc is None


@pytest.mark.asyncio
async def test_storm_adapter_reports_a_missing_storm_environment():
    engine = StormResearchEngine(python_executable="Z:/definitely/not/here/python.exe")
    with pytest.raises(RuntimeError, match="STORM environment not found"):
        async for _ in engine.astream_events(run_id=uuid4(), workspace_id=uuid4(), objective="x"):
            pass


@pytest.mark.asyncio
async def test_storm_adapter_accepts_a_result_line_larger_than_the_default_stream_limit(tmp_path):
    big = f'''
import json, sys
json.load(sys.stdin)
sources = [{{"index": i, "url": f"https://s{{i}}.example", "title": "T", "snippets": ["x" * 4000]}} for i in range(1, 60)]
print({PROTOCOL_PREFIX!r} + json.dumps({{"type": "result", "article": "# summary\\nLead [1].\\n\\n# Body\\nText [2].", "sources": sources, "usage": {{}}}}), flush=True)
'''
    engine = _engine(tmp_path, big)
    with patch("app.integrations.research_engine.storm.engine.record_sources_as_evidence", new_callable=AsyncMock) as evidence, \
         patch.object(StormResearchEngine, "_record_usage", new_callable=AsyncMock):
        events = [e async for e in engine.astream_events(run_id=uuid4(), workspace_id=uuid4(), objective="x")]
    assert events[-1]["status"] == "turn_response" and events[-1]["text"].startswith("Lead [1].")
    assert len(evidence.await_args.kwargs["sources"]) == 59  # a >200 KiB result line was read whole


def test_format_storm_report_appends_numbered_sources_in_order():
    sources = [
        {"index": 2, "url": "https://b", "title": "B"},
        {"index": 1, "url": "https://a", "title": None},
        {"index": None, "url": "https://skipped", "title": "S"},
    ]
    out = format_storm_report("Article [1][2]", sources)
    assert out.index("[1] https://a: https://a") < out.index("[2] B: https://b")
    assert "skipped" not in out
    assert format_storm_report("Article", []) == "Article"


def test_runner_drops_blank_search_queries_before_they_reach_tavily():
    from app.integrations.research_engine.storm.runner import non_empty_queries

    assert non_empty_queries("") == [] and non_empty_queries("   ") == []
    assert non_empty_queries(["RAG history", "", "  ", None, "BM25"]) == ["RAG history", "BM25"]
    assert non_empty_queries("What is RAG") == ["What is RAG"]


def test_runner_strips_characters_that_are_invalid_in_directory_names():
    from app.integrations.research_engine.storm.runner import safe_topic

    assert safe_topic("What is retrieval-augmented generation and why is it used?") ==         "What is retrieval-augmented generation and why is it used"
    assert safe_topic('a<b>c:d"e/f\g|h?i*j') == "abcdefghij"
    assert safe_topic("???") == "research topic"


@pytest.mark.asyncio
async def test_storm_subprocess_runs_in_utf8_mode(tmp_path):
    probe = f'''
import json, sys
json.load(sys.stdin)
print({PROTOCOL_PREFIX!r} + json.dumps({{"type": "result", "article": str(sys.flags.utf8_mode), "sources": [], "usage": {{}}}}), flush=True)
'''
    engine = _engine(tmp_path, probe)
    with patch("app.integrations.research_engine.storm.engine.record_sources_as_evidence", new_callable=AsyncMock),          patch.object(StormResearchEngine, "_record_usage", new_callable=AsyncMock):
        events = [e async for e in engine.astream_events(run_id=uuid4(), workspace_id=uuid4(), objective="x")]
    assert events[-1]["text"] == "1"
