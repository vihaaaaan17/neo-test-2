"""
Live Ground checks (opt-in; real API + worker + MinIO + Open Notebook + LLM gateway):

    PYTHONUTF8=1 RUN_REAL_PROVIDER_SMOKE=1 pytest tests/smoke/test_ground_live.py -q -p no:cacheprovider -s

Uploads a document with known facts, then asks Ground questions unscoped, scoped (non-streaming and streaming SSE) and
with an invalid scope, verifying the evidence resolves to that document's canonical source record and that no request
leaves the conversation locked.
"""
import asyncio
import json
import uuid

import httpx
import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from tests.smoke.test_real_provider import API, _new_conversation, _scalar, _token, pytestmark  # noqa: F401

DOC = """Field notes on the fictional Vellmar Observatory.
The Vellmar Observatory was founded in 1931 by astronomer Ilse Marrow.
Its main telescope has a 2.4 metre primary mirror made of fused silica.
The observatory sits at an altitude of 3,150 metres on Mount Keldt.
"""
OTHER = """Recipe notes. Sourdough bread needs flour, water, salt and an active starter. Bake at 230 degrees Celsius."""


async def _upload(client, db, ws, name, text):
    up = await client.post(f"/workspaces/{ws}/files", files={"file": (name, text.encode(), "text/plain")})
    assert up.status_code == 202, up.text
    sid = up.json()["source_id"]
    for _ in range(120):
        parsed = (await client.get(f"/workspaces/{ws}/sources/{sid}/status")).json()["status"]
        projected = await _scalar(db, "select projection_status from open_notebook_source_bindings where source_id=cast(:s as uuid)", s=sid)
        if parsed == "completed" and str(projected or "").upper() == "ACTIVE":
            return sid
        await asyncio.sleep(5)
    raise AssertionError(f"{name} not ready: {parsed} / {projected}")


async def _ground(client, ws, conv, message, scope=None, stream=False):
    body = {"message": message, "mode": "ground"}
    if scope:
        body["source_scope"] = scope
    if not stream:
        r = await client.post(f"/workspaces/{ws}/conversations/{conv}/turns", params={"stream": "false"}, json=body)
        return r
    async with client.stream("POST", f"/workspaces/{ws}/conversations/{conv}/turns", params={"stream": "true"}, json=body) as r:
        assert r.status_code == 200, await r.aread()
        async for line in r.aiter_lines():
            if line.startswith("event: done"):
                break
    turns = (await client.get(f"/workspaces/{ws}/conversations/{conv}/turns")).json()["turns"]
    return max(turns, key=lambda t: t["sequence"])


def _show(label, turn):
    ev = (turn.get("context_version") or {}).get("ground_evidence") or {}
    print(f"\n[{label}] status={turn['status']} refs={turn.get('ground_evidence_refs')} provenance={ev.get('provenance_status')}"
          f" unresolved={ev.get('unresolved_citations')}\n   answer: {(turn.get('assistant_message') or '')[:220]}"
          f"\n   evidence: {json.dumps([{k: d.get(k) for k in ('title', 'excerpt', 'cited_inline')} for d in ev.get('evidence', [])])[:400]}")
    return ev


@pytest.mark.asyncio
async def test_live_ground_scoping_and_canonical_evidence():
    db = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    async with httpx.AsyncClient(base_url=API, headers={"Authorization": f"Bearer {_token()}"}, timeout=300,
                                 limits=httpx.Limits(max_keepalive_connections=0)) as client:
        ws, conv = await _new_conversation(client)
        vellmar = await _upload(client, db, ws, "vellmar-notes.txt", DOC)
        bread = await _upload(client, db, ws, "bread-notes.txt", OTHER)

        # 1. Unscoped.
        r = await _ground(client, ws, conv, "According to my notes, who founded the Vellmar Observatory and in what year?")
        assert r.status_code == 200, r.text
        t1 = r.json()
        ev = _show("unscoped", t1)
        assert t1["status"] == "completed" and vellmar in t1["ground_evidence_refs"]
        detail = next(d for d in ev["evidence"] if d["source_id"] == vellmar)
        assert detail["title"] == "vellmar-notes.txt" and detail["excerpt"] and "1931" in detail["excerpt"]

        # 2. Scoped, non-streaming: only the selected document.
        r = await _ground(client, ws, conv, "How large is the observatory's primary mirror?", scope=[vellmar])
        assert r.status_code == 200, r.text
        t2 = r.json()
        ev2 = _show("scoped", t2)
        assert t2["status"] == "completed" and t2["ground_evidence_refs"] == [vellmar]
        assert bread not in json.dumps(ev2)

        # 3. Invalid / foreign scope: rejected up front, conversation not locked.
        r = await _ground(client, ws, conv, "anything", scope=[str(uuid.uuid4())])
        assert r.status_code == 400, r.text

        # 4. Scoped, streaming (the UI's default path) - this path used to ignore the scope.
        t4 = await _ground(client, ws, conv, "At what altitude is the observatory?", scope=[vellmar], stream=True)
        ev4 = _show("scoped-stream", t4)
        assert t4["status"] == "completed" and t4["ground_evidence_refs"] == [vellmar], t4
        assert [str(s) for s in t4["source_scope"]] == [vellmar]

        # 5. The conversation is still usable after everything above.
        r = await _ground(client, ws, conv, "What is the mirror made of, according to my notes?")
        assert r.status_code == 200 and r.json()["status"] == "completed", r.text
        _show("after", r.json())
        assert await _scalar(db, "select count(*) from conversation_turns where conversation_id=cast(:c as uuid) and status in ('pending','running')", c=conv) == 0
    await db.dispose()
