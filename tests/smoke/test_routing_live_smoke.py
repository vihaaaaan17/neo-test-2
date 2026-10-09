"""
Live routing checks (opt-in; real API + worker + LLM gateway + Tavily + venv-storm + gpt-researcher):

    RUN_REAL_PROVIDER_SMOKE=1 pytest tests/smoke/test_routing_live_smoke.py -q -p no:cacheprovider -s

Each test asserts the routing invariants (engine actually executed, profile, sequential attempts, one terminal event)
for one class of question. Answer quality is not asserted. `test_escalation_probe` does not force an escalation: it
records whether the router judged the ODR answer insufficient and, if so, that exactly one specialist ran after it.
"""
import asyncio
import json

import httpx
import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from tests.smoke.test_real_provider import (
    API,
    TERMINAL_TURN_EVENTS,
    _new_conversation,
    _rows,
    _scalar,
    _token,
    _wait_turn,
    pytestmark,  # noqa: F401  (same opt-in gate)
)


async def _auto_turn(client, db, message, timeout_s=1200):
    ws, conv = await _new_conversation(client)
    r = await client.post(f"/workspaces/{ws}/conversations/{conv}/turns", params={"stream": "false"},
                          json={"message": message, "mode": "research", "research_options": {"routing_mode": "auto"}})
    assert r.status_code == 202, r.text
    turn = r.json()
    done = await _wait_turn(client, ws, conv, turn["turn_id"], timeout_s=timeout_s)
    run_id = turn["research_run_id"]
    attempts = await _rows(db, "select sequence, engine, budget_profile, trigger, status, started_at, finished_at, preferred_engine, "
                               "latency_ms, input_tokens + output_tokens, timings from research_engine_attempts where run_id=:r "
                               "order by sequence", r=run_id)
    events = await _rows(db, "select event_type, payload from chat_events where turn_id=:t order by sequence", t=turn["turn_id"])
    terminal = [t for t, _ in events if t in TERMINAL_TURN_EVENTS]
    completed = next((p for t, p in events if t == "turn.completed"), None)
    print(f"\n[{message[:60]}] status={done['status']} attempts=" + json.dumps(
        [{"engine": a[1], "profile": a[2], "trigger": a[3], "status": a[4], "preferred": a[7], "latency_s": (a[8] or 0) // 1000,
          "tokens": a[9], "engine_timings": (a[10] or {}).get("engine")} for a in attempts], default=str))
    if completed:
        print("routing:", json.dumps({k: completed["routing"].get(k) for k in ("intent", "preferred_engine", "answered_by",
                                                                               "answer_budget_profile", "escalated", "escalation")},
                                     default=str)[:900])
        print("answer head:", (completed.get("assistant_message") or "")[:300].replace("\n", " "))
    # Invariants for every routed turn.
    assert len(terminal) == 2 and terminal[-1] == "done", terminal  # exactly one terminal turn event (+ done)
    assert 1 <= len(attempts) <= 2
    if len(attempts) == 2:
        assert attempts[1][5] >= attempts[0][6], "attempts overlapped"
    return done, attempts, completed


@pytest.fixture
async def live():
    db = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    client = httpx.AsyncClient(base_url=API, headers={"Authorization": f"Bearer {_token()}"}, timeout=120,
                               limits=httpx.Limits(max_keepalive_connections=0))
    yield client, db
    await client.aclose()
    await db.dispose()


@pytest.mark.asyncio
async def test_simple_question_uses_odr_low_profile(live):
    client, db = live
    done, attempts, _ = await _auto_turn(client, db, "Who wrote the novel Dune?")
    assert done["status"] == "completed"
    assert [(a[1], a[2]) for a in attempts][0] == ("open_deep_research", "low")
    limits = (attempts[0][10] or {}).get("engine", {}).get("limits", {})
    assert limits.get("max_researcher_iterations") == 1  # the low profile reached ODR itself


@pytest.mark.asyncio
async def test_normal_question_uses_odr_balanced_profile(live):
    client, db = live
    done, attempts, _ = await _auto_turn(client, db, "Explain how retrieval-augmented generation reduces hallucinations in language models.")
    assert done["status"] == "completed"
    assert (attempts[0][1], attempts[0][2], attempts[0][3]) == ("open_deep_research", "balanced", "initial")


@pytest.mark.asyncio
async def test_deep_request_routes_directly_to_storm(live):
    client, db = live
    done, attempts, completed = await _auto_turn(
        client, db, "Give me an in-depth investigation of how retrieval-augmented generation evolved from 2020 to 2025.")
    assert attempts[0][7] == "storm"  # preferred engine
    assert (attempts[0][1], attempts[0][3], attempts[0][2]) == ("storm", "intent", "bounded"), attempts
    assert done["status"] == "completed"
    assert completed["routing"]["answered_by"] in ("storm", "open_deep_research")  # ODR only if STORM failed (fallback)


@pytest.mark.asyncio
async def test_broad_request_routes_directly_to_gpt_researcher(live):
    client, db = live
    done, attempts, completed = await _auto_turn(
        client, db, "Find as many sources as possible about microplastics in drinking water.")
    assert attempts[0][7] == "gpt_researcher"
    assert (attempts[0][1], attempts[0][3], attempts[0][2]) == ("gpt_researcher", "intent", "bounded"), attempts
    assert done["status"] == "completed"


@pytest.mark.asyncio
async def test_escalation_probe(live):
    """A two-part question whose second part is obscure: ODR often leaves it unanswered. Escalation is not forced."""
    client, db = live
    done, attempts, completed = await _auto_turn(
        client, db,
        "What is the BM25 ranking function, and what did the Zeta-7 committee decide about it in its unpublished 2026 minutes?")
    assert done["status"] == "completed"
    routing = completed["routing"]
    first_assessment = routing["attempts"][0]["assessment"]
    print("first assessment:", json.dumps(first_assessment, default=str)[:900])
    if routing["escalated"]:
        assert len(attempts) == 2 and attempts[1][3] == "escalation" and attempts[1][1] == routing["escalation"]["to"]
    else:
        assert len(attempts) == 1


@pytest.mark.asyncio
async def test_storm_cancellation_stops_the_run(live):
    client, db = live
    ws, conv = await _new_conversation(client)
    r = await client.post(f"/workspaces/{ws}/conversations/{conv}/turns", params={"stream": "false"},
                          json={"message": "Write a detailed history of semiconductor lithography.", "mode": "research",
                                "research_options": {"routing_mode": "explicit", "engine": "storm"}})
    assert r.status_code == 202, r.text
    turn = r.json()
    for _ in range(60):  # wait until the STORM attempt is actually running
        if await _scalar(db, "select count(*) from research_engine_attempts where run_id=:r and status='running'", r=turn["research_run_id"]):
            break
        await asyncio.sleep(2)
    await asyncio.sleep(15)
    cancel = await client.post(f"/workspaces/{ws}/conversations/{conv}/turns/{turn['turn_id']}/cancel")
    assert cancel.status_code == 200, cancel.text
    done = await _wait_turn(client, ws, conv, turn["turn_id"], timeout_s=120)
    assert done["status"] == "cancelled"
    for _ in range(30):
        status = await _scalar(db, "select status from research_engine_attempts where run_id=:r", r=turn["research_run_id"])
        if status != "running":
            break
        await asyncio.sleep(2)
    assert status == "cancelled", status
    assert await _scalar(db, "select status from research_runs where run_id=:r", r=turn["research_run_id"]) == "cancelled"


@pytest.mark.asyncio
async def test_gpt_researcher_escalation_probe(live):
    """
    Questions whose ODR answers tend to carry many uncited figures or few distinct sources. Escalation is NOT forced:
    the test records the router's diagnosis and, if it escalated, that exactly one GPT-Researcher attempt followed ODR.
    """
    client, db = live
    outcomes = []
    for q in ("List every open-source RAG evaluation framework released in 2025 together with its GitHub star count.",
              "What were the reported 2024 funding totals of the five largest European vector database startups?"):
        done, attempts, completed = await _auto_turn(client, db, q)
        routing = (completed or {}).get("routing") or {}
        outcomes.append((routing.get("escalation") or {}).get("to"))
        if routing.get("escalated") and routing["escalation"]["to"] == "gpt_researcher":
            assert [a[1] for a in attempts] == ["open_deep_research", "gpt_researcher"] and attempts[1][3] == "escalation"
            break
    print("\nGPT-Researcher escalation probe outcomes:", outcomes)
