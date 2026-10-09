"""
Per-adapter output contract (Chapter 6): each adapter asks its upstream engine for a direct conversational answer through
that engine's own controls, passes its budget profile through upstream-native configuration, and reports metrics.
"""
import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.integrations.research_engine.engine import CONVERSATIONAL_STYLE


# --------------------------------------------------------------------------- #
# ODR: profile knobs reach the graph config; style instruction in the user message; metrics before the answer
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
@pytest.mark.parametrize("profile", ["low", "balanced", "deep"])
async def test_odr_profile_reaches_the_graph_configuration(profile):
    from app.integrations.research_engine.open_deep_research.engine import ODR_BUDGET_PROFILES, OpenDeepResearchEngine

    seen = {}

    async def astream(initial_state, config, stream_mode="updates"):
        seen["config"], seen["message"] = config, initial_state["messages"][0]["content"]
        yield {"final_report_generation": {"final_report": "RAG grounds answers in retrieved documents."}}

    graph = MagicMock()
    graph.astream = astream
    with patch("app.integrations.research_engine.upstream.open_deep_research.deep_researcher.deep_researcher_builder.compile",
               return_value=graph):
        engine = OpenDeepResearchEngine(budget_profile=profile, token_ceiling=12345)
    with patch("app.core.database.async_session_maker") as sm, patch("app.repositories.research.ResearchRepository") as rc:
        sm.return_value.__aenter__.return_value = AsyncMock()
        rc.return_value = AsyncMock()
        events = [e async for e in engine.astream_events(run_id=uuid4(), workspace_id=uuid4(), objective="What is RAG?")]

    cfg, p = seen["config"]["configurable"], ODR_BUDGET_PROFILES[profile]
    for knob in ("max_concurrent_research_units", "max_researcher_iterations", "max_react_tool_calls",
                 "research_model_max_tokens", "compression_model_max_tokens", "final_report_model_max_tokens"):
        assert cfg[knob] == p[knob]
    assert CONVERSATIONAL_STYLE in seen["message"]  # native control: the user message ODR's answer prompt reads
    metrics = [e for e in events if e["status"] == "metrics"][0]
    assert metrics["budget_profile"] == profile
    assert metrics["limits"]["max_input_tokens"] == min(p["max_input_tokens"], 12345)  # turn ceiling caps the profile
    assert events[-1]["status"] == "turn_response" and events[-1]["format"] == "conversational"


# --------------------------------------------------------------------------- #
# STORM: the lead section STORM writes is the direct answer; the full article is kept as details
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_storm_returns_its_lead_section_as_the_conversational_answer(tmp_path):
    from app.core.config import settings
    from app.integrations.research_engine.storm.engine import PROTOCOL_PREFIX, StormResearchEngine

    article = "# summary\nRAG combines retrieval with generation [1].\n\n# History\nIt was introduced in 2020 [2]."
    runner = tmp_path / "runner.py"
    runner.write_text(
        "import json, sys\njob = json.load(sys.stdin)\n"
        f"print({PROTOCOL_PREFIX!r} + json.dumps({{'type': 'phase', 'phase': 'executing', 'message': 'x'}}), flush=True)\n"
        f"print({PROTOCOL_PREFIX!r} + json.dumps({{'type': 'result', 'article': {article!r}, 'usage': {{'model_calls': 4, 'input_tokens': 10, 'output_tokens': 5}},"
        " 'sources': [{'index': 1, 'url': 'https://a.example', 'title': 'A'}, {'index': 2, 'url': 'https://b.example', 'title': 'B'}],"
        " 'args': job['args']}), flush=True)\n"
    )
    engine = StormResearchEngine(python_executable=sys.executable, runner_path=str(runner), budget_profile="bounded")
    with patch("app.core.config.resolve_llm_provider") as resolve, \
         patch.object(settings, "TAVILY_API_KEY", "tvly-test"), \
         patch("app.integrations.research_engine.storm.engine.record_sources_as_evidence", new_callable=AsyncMock), \
         patch.object(StormResearchEngine, "_record_usage", new_callable=AsyncMock):
        resolve.return_value.api_key, resolve.return_value.base_url, resolve.return_value.model = "k", "http://x/v1", "auto"
        events = [e async for e in engine.astream_events(run_id=uuid4(), workspace_id=uuid4(), objective="What is RAG?")]

    final = events[-1]
    assert final["format"] == "conversational"
    assert final["text"].startswith("RAG combines retrieval with generation [1].")
    assert "[1] A: https://a.example" in final["text"] and "b.example" not in final["text"]  # only sources the lead cites
    assert "# History" in final["details"] and "[2] B: https://b.example" in final["details"]
    metrics = [e for e in events if e["status"] == "metrics"][0]
    assert metrics["budget_profile"] == "bounded" and metrics["limits"]["max_perspective"] == 2
    assert metrics["input_tokens"] == 10


def test_storm_article_without_a_lead_stays_an_article():
    from app.integrations.research_engine.storm.engine import split_storm_article

    assert split_storm_article("# History\nBody") == ("", "# History\nBody")


# --------------------------------------------------------------------------- #
# GPT-Researcher: the installed upstream generate_report honours custom_prompt (the native control we rely on)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_installed_gpt_researcher_uses_our_custom_prompt_instead_of_its_report_prompt(tmp_path):
    from gpt_researcher.actions import report_generation
    from gpt_researcher.config.config import Config

    from app.integrations.research_engine.gpt_researcher.engine import build_config, conversational_prompt

    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(build_config("auto", "text-embedding-3-small", "bounded")))
    cfg = Config(str(cfg_path))
    assert cfg.max_iterations == 2 and cfg.total_words == 500  # bounded profile parsed by upstream Config

    captured = {}

    async def fake_completion(**kwargs):
        captured.update(kwargs)
        return "RAG grounds answers in retrieved documents [source](https://a.example)."

    with patch.object(report_generation, "create_chat_completion", side_effect=fake_completion):
        out = await report_generation.generate_report(
            query="What is RAG?", context="CONTEXT-PASSAGES", agent_role_prompt="You are a research assistant.",
            report_type="research_report", tone=None, report_source="web", websocket=None, cfg=cfg,
            custom_prompt=conversational_prompt("What is RAG?"),
        )
    user_msg = captured["messages"][-1]["content"]
    assert user_msg.startswith(conversational_prompt("What is RAG?"))  # our prompt replaced the report-type prompt
    assert "CONTEXT-PASSAGES" in user_msg and "APA" not in user_msg
    assert captured["max_tokens"] == 3000  # bounded SMART_TOKEN_LIMIT reached the upstream call
    assert out.startswith("RAG grounds answers")
