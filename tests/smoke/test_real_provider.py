"""
Real-provider smoke gate, one run per supported engine (Chapter 5 - verification checklist section E).

Opt-in: runs only with RUN_REAL_PROVIDER_SMOKE=1, against the live stack (API + ARQ worker + Postgres + Redis)
using the configured LLM provider and Tavily. Report quality is not asserted.

    RUN_REAL_PROVIDER_SMOKE=1 pytest tests/smoke -m real_provider -q -p no:cacheprovider
    RUN_REAL_PROVIDER_SMOKE=1 pytest tests/smoke -m real_provider -k storm      # a single engine

STORM additionally needs its isolated environment (`venv-storm`, see requirements-storm.txt). The worker and API must be
restarted after code changes so they run this revision.

Environment:
    SMOKE_API_BASE_URL   default http://localhost:8000/api/v1
    SUPABASE_JWT_SECRET  used to mint a throwaway user token (falls back to the local dev secret)
"""
import asyncio
import datetime
import json
import os
import re
import uuid

import httpx
import jwt
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.integrations.research_engine.engine import SUPPORTED_ENGINES

pytestmark = [
    pytest.mark.real_provider,
    pytest.mark.skipif(os.environ.get("RUN_REAL_PROVIDER_SMOKE") != "1",
                       reason="real-provider smoke test; set RUN_REAL_PROVIDER_SMOKE=1 to run"),
]

API = os.environ.get("SMOKE_API_BASE_URL", "http://localhost:8000/api/v1")
TERMINAL = {"completed", "failed", "partial", "cancelled", "aborted_by_timeline_fence"}
# Real upstream runs are slow on the free gateway: allow each engine generously (seconds).
COMPLETION_TIMEOUT_S = {"open_deep_research": 480, "storm": 900, "gpt_researcher": 900}
TERMINAL_TURN_EVENTS = ("turn.completed", "turn.failed", "turn.cancelled", "turn.partial", "done")


def _token() -> str:
    secret = os.environ.get("SUPABASE_JWT_SECRET") or getattr(settings, "SUPABASE_JWT_SECRET", None)
    if not secret and os.path.exists(".env"):
        m = re.search(r"^SUPABASE_JWT_SECRET=(.*)$", open(".env").read(), re.M)
        secret = m.group(1).strip() if m else None
    secret = secret or "super-secret-jwt-token-for-supabase-local-dev-only"
    payload = {"sub": str(uuid.uuid4()), "aud": "authenticated",
               "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)}
    return jwt.encode(payload, secret, algorithm="HS256")


async def _scalar(db, sql, **params):
    async with db.connect() as conn:
        return (await conn.execute(text(sql), params)).scalar()


async def _rows(db, sql, **params):
    async with db.connect() as conn:
        return (await conn.execute(text(sql), params)).all()


async def _wait_turn(client, ws, conv, turn, timeout_s):
    deadline = asyncio.get_event_loop().time() + timeout_s
    while True:
        d = (await client.get(f"/workspaces/{ws}/conversations/{conv}/turns/{turn}")).json()
        if d["status"] in TERMINAL:
            return d
        assert asyncio.get_event_loop().time() < deadline, f"turn still {d['status']} after {timeout_s}s"
        await asyncio.sleep(3)


async def _collect_terminal_events(run_id: str, stop: asyncio.Event, sink: list):
    import redis.asyncio as aioredis
    r = aioredis.from_url(settings.REDIS_URL)
    ps = r.pubsub()
    await ps.subscribe(f"research_events:{run_id}")
    try:
        while not stop.is_set():
            msg = await ps.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg and msg.get("type") == "message":
                data = json.loads(msg["data"])
                if data.get("status") in TERMINAL:
                    sink.append(data["status"])
    finally:
        await ps.unsubscribe()
        await r.aclose()


async def _new_conversation(client):
    ws = (await client.post("/workspaces/", json={})).json()["workspace_id"]
    conv = (await client.post(f"/workspaces/{ws}/conversations", json={})).json()["conversation_id"]
    return ws, conv


async def _submit_research(client, ws, conv, message, engine="open_deep_research"):
    return await client.post(
        f"/workspaces/{ws}/conversations/{conv}/turns", params={"stream": "false"},
        json={"message": message, "mode": "research", "research_options": {"routing_mode": "explicit", "engine": engine}},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("engine", SUPPORTED_ENGINES)
async def test_real_provider_smoke(engine):
    db = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    headers = {"Authorization": f"Bearer {_token()}"}
    async with httpx.AsyncClient(base_url=API, headers=headers, timeout=60,
                                 limits=httpx.Limits(max_keepalive_connections=0)) as client:
        health = (await client.get("/health")).json()
        assert health.get("status") == "ok", f"stack not healthy: {health}"

        # 6. Engine selection is deterministic: unsupported engines are rejected before a run exists.
        ws, conv = await _new_conversation(client)
        for bad in ("legacy", "ODR", ""):
            r = await _submit_research(client, ws, conv, "x", engine=bad)
            assert r.status_code == 422 and r.json()["detail"] == "unsupported_research_engine"

        # 1-5, 8: a real run completes with persisted report, provenance and a single terminal state/event.
        r = await _submit_research(client, ws, conv, "Using current web sources, explain in two sentences what retrieval-augmented generation is, and cite the URLs.", engine=engine)
        assert r.status_code == 202, r.text
        turn = r.json()
        run_id = turn["research_run_id"]
        stop, terminal_events = asyncio.Event(), []
        listener = asyncio.create_task(_collect_terminal_events(run_id, stop, terminal_events))

        done = await _wait_turn(client, ws, conv, turn["turn_id"], timeout_s=COMPLETION_TIMEOUT_S[engine])
        await asyncio.sleep(3)  # let the final publish land
        stop.set()
        await listener

        assert done["status"] == "completed", done
        assert await _scalar(db, "select engine from research_runs where run_id=:r", r=run_id) == engine
        assert await _scalar(db, "select status from research_runs where run_id=:r", r=run_id) == "completed"

        # 2. Events reached the canonical event stream (persisted chat events for the turn).
        event_types = [row[0] for row in await _rows(
            db, "select event_type from chat_events where turn_id=:t order by sequence", t=turn["turn_id"])]
        assert "turn.research_started" in event_types and "turn.synthesizing" in event_types, event_types

        # 3. Evidence retains provenance. Whether the model searches is its own decision, so the gate ties the
        #    check to recorded search calls: every search must produce evidence, and all evidence has provenance.
        searches = await _scalar(db, "select coalesce(max(search_calls), 0) from research_usages where run_id=:r", r=run_id)
        evidence = await _rows(db, "select locator, provenance from research_evidence where run_id=:r", r=run_id)
        if engine != "open_deep_research":
            assert evidence, f"{engine} always searches, but no evidence was persisted"  # STORM / GPT-Researcher search by design
        elif searches:
            assert evidence, f"{searches} search call(s) recorded but no evidence persisted"
        else:
            import warnings
            warnings.warn("model answered without searching; evidence/provenance check is vacuous for this run")
        assert all(loc and prov and prov.get("url") for loc, prov in evidence)

        # 4. The conversational answer is persisted on the turn (Chapter 6: no per-turn ResearchReport).
        assert done["assistant_message"], done
        assert await _scalar(db, "select count(*) from research_reports where run_id=:r", r=run_id) == 0
        attempts = await _rows(db, "select engine, trigger, status from research_engine_attempts where run_id=:r", r=run_id)
        assert attempts == [(engine, "explicit", "answered")], attempts

        # 5. Research-derived material does not become Ground evidence: an ordinary turn creates no candidate, and
        #    nothing was promoted into workspace sources or knowledge memories.
        assert await _scalar(db, "select count(*) from research_artifacts where run_id=:r", r=run_id) == 0
        assert await _scalar(db, "select count(*) from sources where workspace_id=:w", w=ws) == 0
        assert await _scalar(db, "select count(*) from knowledge_memories where workspace_id=:w", w=ws) == 0

        # 8. Exactly one terminal run state and no duplicate terminal event.
        assert terminal_events == ["completed"], terminal_events
        terminal_turn = [e for e in event_types if e in TERMINAL_TURN_EVENTS]
        assert terminal_turn == ["turn.completed", "done"], terminal_turn

        # 7. Cancellation does not leave a running/stuck run.
        ws2, conv2 = await _new_conversation(client)
        r = await _submit_research(client, ws2, conv2,
                                   "Write a detailed history of semiconductor lithography from 1960 to 2025.", engine=engine)
        assert r.status_code == 202, r.text
        turn2 = r.json()
        await asyncio.sleep(10)
        cancel = await client.post(f"/workspaces/{ws2}/conversations/{conv2}/turns/{turn2['turn_id']}/cancel")
        assert cancel.status_code == 200, cancel.text
        done2 = await _wait_turn(client, ws2, conv2, turn2["turn_id"], timeout_s=90)
        assert done2["status"] == "cancelled"

        run2 = turn2["research_run_id"]
        for _ in range(20):  # the worker must observe the cancel and stop; the run must end terminal
            status2 = await _scalar(db, "select status from research_runs where run_id=:r", r=run2)
            if status2 in TERMINAL:
                break
            await asyncio.sleep(3)
        assert status2 == "cancelled", status2
        assert await _scalar(db, "select count(*) from research_reports where run_id=:r", r=run2) == 0
        types2 = [row[0] for row in await _rows(
            db, "select event_type from chat_events where turn_id=:t order by sequence", t=turn2["turn_id"])]
        assert [e for e in types2 if e in TERMINAL_TURN_EVENTS] == ["turn.cancelled", "done"], types2

    await db.dispose()
