"""
Real-provider smoke gate for Chapter 6 (opt-in, live stack: API + ARQ worker + Postgres + Redis + LLM gateway + Tavily).

    RUN_REAL_PROVIDER_SMOKE=1 pytest tests/smoke/test_conversational_routing_smoke.py -q -p no:cacheprovider

1. An auto-routed Research turn returns a conversational answer + evidence; no ResearchReport / candidate is created;
   every engine attempt is recorded, attempts are strictly sequential, and the run records the answering engine.
2. A second turn in the same conversation, then an explicit "compile" turn: a study-session paper is persisted with a
   pending_review candidate; its References cite only evidence that exists for this conversation; nothing is promoted.
"""
import re

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


async def _research(client, ws, conv, message):
    r = await client.post(f"/workspaces/{ws}/conversations/{conv}/turns", params={"stream": "false"},
                          json={"message": message, "mode": "research", "research_options": {"routing_mode": "auto"}})
    assert r.status_code == 202, r.text
    return r.json()


@pytest.mark.asyncio
async def test_auto_routed_conversational_turns_and_explicit_study_report():
    db = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    headers = {"Authorization": f"Bearer {_token()}"}
    async with httpx.AsyncClient(base_url=API, headers=headers, timeout=600,
                                 limits=httpx.Limits(max_keepalive_connections=0)) as client:
        ws, conv = await _new_conversation(client)

        # "auto" is a routing mode, never an engine name.
        bad = await client.post(f"/workspaces/{ws}/conversations/{conv}/turns", params={"stream": "false"},
                                json={"message": "x", "mode": "research", "research_options": {"engine": "auto"}})
        assert bad.status_code == 422 and bad.json()["detail"] == "unsupported_research_engine"

        # ---- 1. auto-routed conversational turn -------------------------------------------------------------------
        turn = await _research(client, ws, conv, "What is retrieval-augmented generation? Cite current web sources.")
        done = await _wait_turn(client, ws, conv, turn["turn_id"], timeout_s=900)
        assert done["status"] == "completed", done
        assert done["assistant_message"] and len(done["assistant_message"]) > 40
        run_id = turn["research_run_id"]

        assert await _scalar(db, "select routing_mode from research_runs where run_id=:r", r=run_id) == "auto"
        assert await _scalar(db, "select count(*) from research_reports where run_id=:r", r=run_id) == 0
        assert await _scalar(db, "select count(*) from research_artifacts where run_id=:r", r=run_id) == 0

        attempts = await _rows(db, "select sequence, engine, trigger, status, started_at, finished_at, attempt_id "
                                   "from research_engine_attempts where run_id=:r order by sequence", r=run_id)
        assert 1 <= len(attempts) <= 2, attempts
        assert attempts[0][1] in ("open_deep_research", "storm", "gpt_researcher")
        if len(attempts) == 2:
            assert attempts[1][4] >= attempts[0][5], "attempts overlapped"  # sequential
        answered = [a for a in attempts if a[3] == "answered"]
        assert answered
        run_engine = await _scalar(db, "select engine from research_runs where run_id=:r", r=run_id)
        current = await _scalar(db, "select current_attempt_id from research_runs where run_id=:r", r=run_id)
        assert run_engine == [a[1] for a in attempts if a[6] == current][0]

        events = await _rows(db, "select event_type, payload from chat_events where turn_id=:t order by sequence", t=turn["turn_id"])
        types = [e[0] for e in events]
        assert [t for t in types if t in TERMINAL_TURN_EVENTS] == ["turn.completed", "done"], types
        completed = [p for t, p in events if t == "turn.completed"][0]
        assert completed["routing"]["answered_by"] == run_engine
        assert all(e.get("url") for e in completed["evidence"])
        for e in completed["evidence"]:
            assert await _scalar(db, "select count(*) from research_evidence where evidence_id=cast(:e as uuid) and run_id=:r",
                                 e=e["evidence_id"], r=run_id) == 1

        # ---- 2. follow-up turn, then explicit compile request -------------------------------------------------------
        turn2 = await _research(client, ws, conv, "How does RAG reduce hallucinations compared to fine-tuning?")
        done2 = await _wait_turn(client, ws, conv, turn2["turn_id"], timeout_s=900)
        assert done2["status"] == "completed", done2

        r = await client.post(f"/workspaces/{ws}/conversations/{conv}/turns", params={"stream": "false"},
                              json={"message": "Compile everything we've discussed into a research paper", "mode": "research"})
        assert r.status_code in (200, 201, 202), r.text
        paper_turn = r.json()
        paper_done = await _wait_turn(client, ws, conv, paper_turn["turn_id"], timeout_s=600)
        assert paper_done["status"] == "completed", paper_done
        assert paper_done["research_run_id"] is None  # the compiler launched no research
        assert "## References" in paper_done["assistant_message"]

        report_id = paper_done["context_version"]["study_report"]["report_id"]
        row = (await _rows(db, "select scope, run_id, conversation_id, content from research_reports where report_id=:i", i=report_id))[0]
        assert row[0] == "study_session" and row[1] is None and str(row[2]) == conv
        refs = row[3].split("## References")[-1]
        for ev_id in re.findall(r"research evidence ([0-9a-f-]{36})", refs):
            assert await _scalar(db, "select count(*) from research_evidence e join research_runs r on r.run_id=e.run_id "
                                     "where e.evidence_id=cast(:e as uuid) and r.conversation_id=cast(:c as uuid)", e=ev_id, c=conv) == 1
        cand = await _rows(db, "select promotion_status from research_artifacts where conversation_id=cast(:c as uuid)", c=conv)
        assert cand == [("pending_review",)]
        assert await _scalar(db, "select count(*) from knowledge_memories where workspace_id=:w", w=ws) == 0
        assert await _scalar(db, "select count(*) from sources where workspace_id=:w", w=ws) == 0

    await db.dispose()
