"""
Live Ground <-> Research study session (opt-in; real API, worker, MinIO, Open Notebook, LLM gateway, Tavily):

    RUN_REAL_PROVIDER_SMOKE=1 pytest tests/smoke/test_study_session_live.py -q -p no:cacheprovider -s

upload a document -> Ground question -> two Research questions -> Ground again -> Research again
-> "Compile everything we've discussed into a research paper" -> fetch the saved paper.
"""
import asyncio
import json
import re

import httpx
import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from tests.smoke.test_real_provider import API, _new_conversation, _rows, _scalar, _token, _wait_turn, pytestmark  # noqa: F401

DOCUMENT = """Lecture notes: Attention and Transformers

Self-attention lets every token weigh every other token using query, key and value projections.
The scaled dot-product attention score is softmax(QK^T / sqrt(d_k)) V.
Multi-head attention runs several attention functions in parallel so the model can attend to different relationships.
Transformers replaced recurrence with attention, which allows parallel training over a whole sequence.
Positional encodings are added because attention by itself has no notion of token order.
"""


async def _turn(client, ws, conv, message, mode, timeout_s=1200, **opts):
    body = {"message": message, "mode": mode, **opts}
    r = await client.post(f"/workspaces/{ws}/conversations/{conv}/turns", params={"stream": "false"}, json=body)
    assert r.status_code in (200, 201, 202), r.text
    turn = r.json()
    done = turn if turn["status"] in ("completed", "failed") else await _wait_turn(client, ws, conv, turn["turn_id"], timeout_s)
    print(f"\n[{mode}] {message[:60]} -> {done['status']} {done.get('error_code') or ''}\n   "
          + (done.get("assistant_message") or "")[:260].replace("\n", " "))
    return done


@pytest.mark.asyncio
async def test_live_study_session_workflow():
    db = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    async with httpx.AsyncClient(base_url=API, headers={"Authorization": f"Bearer {_token()}"}, timeout=300,
                                 limits=httpx.Limits(max_keepalive_connections=0)) as client:
        ws, conv = await _new_conversation(client)

        # 1. Upload a canonical source and wait for parsing + Open Notebook projection.
        up = await client.post(f"/workspaces/{ws}/files", files={"file": ("attention-notes.txt", DOCUMENT.encode(), "text/plain")})
        assert up.status_code == 202, up.text
        source_id = up.json()["source_id"]
        for _ in range(120):
            parsed = (await client.get(f"/workspaces/{ws}/sources/{source_id}/status")).json()["status"]
            projected = await _scalar(db, "select projection_status from open_notebook_source_bindings where source_id=cast(:s as uuid)", s=source_id)
            if parsed == "completed" and str(projected or "").upper() in ("PROJECTED", "COMPLETED", "ACTIVE", "READY", "INDEXED"):
                break
            await asyncio.sleep(5)
        print("source:", parsed, projected)
        assert parsed == "completed", parsed

        # 2. Ground answer grounded in the document.
        g1 = await _turn(client, ws, conv, "According to my notes, why do transformers need positional encodings?", "ground")
        assert g1["status"] == "completed", g1
        assert source_id in json.dumps(g1["ground_evidence_refs"])

        # 3-4. Research turns in the same conversation.
        r1 = await _turn(client, ws, conv, "What is multi-head attention used for in large language models today?", "research",
                         research_options={"routing_mode": "auto"})
        r2 = await _turn(client, ws, conv, "How does that relate to the context window limits of those models?", "research",
                         research_options={"routing_mode": "auto"})
        assert r1["status"] == "completed" and r2["status"] == "completed"

        # 5-6. Back to Ground: still only the canonical source.
        g2 = await _turn(client, ws, conv, "What formula do my notes give for scaled dot-product attention?", "ground")
        assert g2["status"] == "completed", g2
        refs = g2["ground_evidence_refs"]
        assert refs and all(str(r) == source_id or (isinstance(r, dict) and str(r.get("source_id")) == source_id) for r in refs), refs
        research_urls = [row[0] for row in await _rows(
            db, "select e.locator from research_evidence e join research_runs r on r.run_id=e.run_id where r.conversation_id=cast(:c as uuid)", c=conv)]
        assert research_urls, "research turns collected no evidence"
        assert not any(u and u in (g2["assistant_message"] or "") for u in research_urls)  # no research URL in a Ground answer

        # 7. Research continues.
        r3 = await _turn(client, ws, conv, "Which techniques extend transformer context windows efficiently?", "research",
                         research_options={"routing_mode": "auto"})
        assert r3["status"] == "completed"

        # 8. Explicit compilation.
        paper = await _turn(client, ws, conv, "Compile everything we've discussed into a research paper", "research", timeout_s=600)
        assert paper["status"] == "completed", paper
        assert paper["research_run_id"] is None
        report_id = paper["context_version"]["study_report"]["report_id"]

        # 9. Retrieve and inspect the saved paper.
        got = (await client.get(f"/workspaces/{ws}/conversations/{conv}/study-reports/{report_id}")).json()
        content = got["content"]
        print("\nPAPER (head):\n", content[:1500], "\n...\nREFERENCES:\n", content.split("## References")[-1][:1500])
        print("claims:", json.dumps((got.get("citations") or {}).get("claims"), default=str)[:600], "| warnings:", got.get("warnings"))
        refs_section = content.split("## References")[-1]
        assert "## References" in content
        for ev_id in re.findall(r"research evidence ([0-9a-f-]{36})", refs_section):
            assert await _scalar(db, "select count(*) from research_evidence e join research_runs r on r.run_id=e.run_id "
                                     "where e.evidence_id=cast(:e as uuid) and r.conversation_id=cast(:c as uuid)", e=ev_id, c=conv) == 1
        for src in re.findall(r"uploaded workspace source ([0-9a-f-]{36})", refs_section):
            assert src == source_id
        assert await _scalar(db, "select count(*) from knowledge_memories where workspace_id=cast(:w as uuid)", w=ws) == 0
        assert await _scalar(db, "select count(*) from sources where workspace_id=cast(:w as uuid)", w=ws) == 1
    await db.dispose()
