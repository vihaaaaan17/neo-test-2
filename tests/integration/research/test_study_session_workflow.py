"""
Full Ground <-> Research study session, through the real ChatService, admission, research worker job, EngineRouter and
StudyReportCompiler against Postgres. Only the external runtimes are stand-ins: the Ground engine (Open Notebook) and the
research adapters (no network). Checks continuity, Ground isolation, explicit compilation, retrieval and authorization.

    ground -> research -> research -> ground -> research -> "compile everything ..." -> GET report
"""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from sqlalchemy import select

from app.integrations.research_engine import router as router_module
from app.integrations.research_engine.engine import ResearchEngine, turn_response
from app.integrations.research_engine.evidence import record_sources_as_evidence
from app.models.block import DocumentBlock
from app.models.conversation import Conversation, ConversationTurn
from app.models.knowledge import KnowledgeMemory
from app.models.research import ResearchArtifact, ResearchEngineAttempt, ResearchEvidence, ResearchReport, ResearchRun
from app.models.source import Source, SourceSnapshot
from app.models.workspace import Workspace
from app.schemas.chat import TurnCreate
from app.services.chat.service import ChatService
from app.services.research.admission import ResearchAdmissionController
from app.services.research.quota import ResearchQuotaService
from app.repositories.research import ResearchRepository
from app.workers.tasks import run_research_agent_job

pytestmark = pytest.mark.integration

RESEARCH_URLS = ["https://research.example.org/rag", "https://papers.example.net/grounding"]


class FakeGround:
    """Stands in for Open Notebook: answers only from canonical sources and records what it was given."""

    def __init__(self, source_id):
        self.source_id = source_id
        self.calls = []

    async def run(self, workspace_id, query, ground_context=None, source_scope=None, **kwargs):
        self.calls.append({"query": query, "ground_context": ground_context.model_dump(mode="json") if ground_context else None,
                           "source_scope": source_scope})
        return {"is_grounded": True, "answer": f"According to the uploaded notes, self-attention weighs tokens. ({query[:30]})",
                "evidence": [str(self.source_id)], "provenance_status": "fully_grounded"}


class FakeResearchAdapter(ResearchEngine):
    """Stands in for ODR: persists real evidence through Neosis and records the context it received."""

    received = []

    def __init__(self, profile):
        self.profile = profile

    async def astream_events(self, run_id, workspace_id, objective, research_context=None, **kwargs):
        FakeResearchAdapter.received.append({"objective": objective, "context": json.dumps(research_context or {}),
                                             "profile": self.profile})
        yield {"status": "executing", "message": "searching"}
        await record_sources_as_evidence(
            workspace_id=workspace_id, run_id=run_id, retriever="tavily_web_search", provider="tavily", query=objective,
            sources=[{"url": u, "title": f"Source on {objective[:20]}",
                      "content": "Retrieval-augmented generation grounds answers in retrieved documents and reduces hallucinations."}
                     for u in RESEARCH_URLS],
        )
        answer = (f"Retrieval-augmented generation grounds answers in retrieved documents, which reduces hallucinations "
                  f"because the model can cite them [source]({RESEARCH_URLS[0]}). " + "It helps answer: " + objective + " "
                  + " ".join(["Grounding retrieved documents keeps answers verifiable and current for learners."] * 8)
                  + f" See also [paper]({RESEARCH_URLS[1]}).")
        yield turn_response(answer)

    async def cancel(self):
        pass


async def _seed(db):
    ws, owner, intruder = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    other_ws = uuid.uuid4()
    db.add_all([Workspace(workspace_id=ws, owner_id=owner), Workspace(workspace_id=other_ws, owner_id=intruder)])
    await db.flush()
    conv = Conversation(workspace_id=ws, owner_id=owner)
    db.add(conv)
    src = Source(workspace_id=ws, owner_id=owner, processing_status="completed")
    foreign = Source(workspace_id=other_ws, owner_id=intruder, processing_status="completed")
    db.add_all([src, foreign])
    await db.flush()
    snap = SourceSnapshot(source_id=src.source_id, file_uri="s3://x", filename="transformer-notes.pdf", size=1, checksum_sha256="0")
    db.add(snap)
    await db.flush()
    db.add(DocumentBlock(source_id=src.source_id, snapshot_id=snap.snapshot_id, block_type="text", sequence=1,
                         text_or_ref="Self-attention weighs tokens by learned relevance scores between queries and keys."))
    await db.commit()
    return ws, owner, intruder, conv, src, foreign


@pytest.mark.asyncio
async def test_ground_research_study_session_end_to_end(db_session, monkeypatch):
    ws, owner, intruder, conv, src, foreign = await _seed(db_session)
    cid = conv.conversation_id
    FakeResearchAdapter.received = []
    ground = FakeGround(src.source_id)

    limiter = MagicMock()
    limiter.enforce_rate_limit = AsyncMock(return_value=True)
    repo = ResearchRepository(db_session)
    chat = ChatService(db=db_session, ground_engine=ground, arq_redis=None,
                       admission_controller=ResearchAdmissionController(ResearchQuotaService(repo), limiter, repo))

    async def compile_llm(prompt):
        return json.dumps({"title": "Grounding and Attention", "sections": [{"heading": "Findings", "statements": [
            {"text": "Self-attention weighs tokens by learned relevance scores.", "kind": "finding", "citations": [1]},
            {"text": "Retrieval-augmented generation grounds answers in retrieved documents.", "kind": "finding", "citations": [2]},
            {"text": "Grounding eliminates every hallucination.", "kind": "finding", "citations": [9]},
        ]}]})
    chat.study_report_llm = compile_llm

    # Specialists not installed in CI: auto routing must still work (ODR) and say why specialists were not used.
    async def readiness(engine):
        state = "eligible" if engine == "open_deep_research" else "unavailable"
        return {"engine": engine, "state": state, "eligible": state == "eligible", "gate": "auto", "checks": {}, "reason": state}
    monkeypatch.setattr(router_module, "engine_readiness", readiness)
    monkeypatch.setattr(router_module, "_default_factory", lambda engine, redis, profile, token_ceiling=None: FakeResearchAdapter(profile))

    async def ground_turn(message, scope=None):
        turn = await chat.submit_turn(ws, cid, owner, TurnCreate(message=message, mode="ground", source_scope=scope))
        assert turn.status == "completed", (turn.error_code, turn.error_message)
        return turn

    async def research_turn(message):
        turn = await chat.submit_turn(ws, cid, owner, TurnCreate(message=message, mode="research",
                                                                 research_options={"routing_mode": "auto"}))
        turn_id, run_id = turn.turn_id, turn.research_run_id
        assert run_id is not None
        result = await run_research_agent_job({"job_id": f"job-{uuid.uuid4()}", "redis": None}, workspace_id=str(ws),
                                              objective=message, run_id=str(run_id))
        assert result["status"] == "completed", result
        db_session.expire_all()
        row = (await db_session.execute(select(ConversationTurn).where(ConversationTurn.turn_id == turn_id))).scalar_one()
        return {"status": row.status, "assistant_message": row.assistant_message, "research_run_id": row.research_run_id}

    # 1-2. Ground answer grounded in the uploaded document, with an explicit source scope.
    g1 = await ground_turn("What do my notes say about self-attention?", scope=[src.source_id])
    assert g1.ground_evidence_refs == [str(src.source_id)]

    # Ground fails closed on a source from another workspace (adversarial scope).
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        await chat.submit_turn(ws, cid, owner, TurnCreate(message="Leak?", mode="ground", source_scope=[foreign.source_id]))

    # 3-4. Research turns: conversational answers with evidence; continuity across turns via the research context.
    r1 = await research_turn("What is retrieval-augmented generation?")
    r2 = await research_turn("How does it reduce hallucinations compared with fine-tuning?")
    assert r1["assistant_message"].startswith("Retrieval-augmented generation") and r2["status"] == "completed"
    assert "What is retrieval-augmented generation?" in FakeResearchAdapter.received[1]["context"]  # continuity
    assert [x["profile"] for x in FakeResearchAdapter.received] == ["low", "balanced"]  # simple -> low, normal -> balanced
    run1 = (await db_session.execute(select(ResearchRun).where(ResearchRun.run_id == r1["research_run_id"]))).scalar_one()
    assert run1.routing_mode == "auto" and run1.engine == "open_deep_research"
    attempts = (await db_session.execute(select(ResearchEngineAttempt).where(ResearchEngineAttempt.run_id == r1["research_run_id"]))).scalars().all()
    assert [(a.engine, a.routing_mode, a.preferred_engine, a.status) for a in attempts] == [("open_deep_research", "auto", "open_deep_research", "answered")]
    assert (await db_session.execute(select(ResearchReport).where(ResearchReport.run_id == r1["research_run_id"]))).scalars().all() == []

    # 5-6. Back to Ground: it sees only Ground history and canonical sources - no research material.
    await ground_turn("Summarise my notes on attention again.")
    last = json.dumps(ground.calls[-1])
    for leaked in RESEARCH_URLS + ["retrieval-augmented generation?", "fine-tuning"]:
        assert leaked not in last, f"research material reached Ground: {leaked}"
    history = ground.calls[-1]["ground_context"]
    assert all("Retrieval-augmented generation grounds" not in json.dumps(h) for h in history.values() if h)

    # 7. Research continues.
    await research_turn("Which evaluation metrics measure groundedness of RAG answers?")

    # 8. Explicit compilation through chat.
    paper_turn = await chat.submit_turn(ws, cid, owner, TurnCreate(message="Compile everything we've discussed into a research paper",
                                                                   mode="research"))
    assert paper_turn.status == "completed" and paper_turn.research_run_id is None  # no research was run
    report_id = paper_turn.context_version["study_report"]["report_id"]
    content = paper_turn.assistant_message
    assert "learned relevance scores. [1]" in content and "retrieved documents. [2]" in content
    assert "*[Unsupported by the collected evidence]* Grounding eliminates every hallucination." in content
    refs = content.split("## References")[-1]
    assert f"transformer-notes.pdf (uploaded workspace source {src.source_id})" in refs
    assert "research evidence " in refs and RESEARCH_URLS[0] in refs

    # Every research reference is real evidence collected by THIS conversation.
    import re
    for ev_id in re.findall(r"research evidence ([0-9a-f-]{36})", refs):
        row = (await db_session.execute(select(ResearchEvidence, ResearchRun.conversation_id)
                                        .join(ResearchRun, ResearchRun.run_id == ResearchEvidence.run_id)
                                        .where(ResearchEvidence.evidence_id == uuid.UUID(ev_id)))).first()
        assert row is not None and row[1] == cid

    # 9. Retrieve the saved paper over the API; another user cannot read or compile it.
    from app.api.deps.auth import get_current_user
    from app.main import app

    async def as_user(user):
        app.dependency_overrides[get_current_user] = lambda: user
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test/api/v1")

    try:
        async with await as_user(owner) as client:
            listed = (await client.get(f"/workspaces/{ws}/conversations/{cid}/study-reports")).json()["items"]
            assert [r["report_id"] for r in listed] == [report_id]
            one = await client.get(f"/workspaces/{ws}/conversations/{cid}/study-reports/{report_id}")
            assert one.status_code == 200 and one.json()["content"] == content and one.json()["version"] == "1"
        async with await as_user(intruder) as client:
            assert (await client.get(f"/workspaces/{ws}/conversations/{cid}/study-reports/{report_id}")).status_code == 404
            assert (await client.post(f"/workspaces/{ws}/conversations/{cid}/study-report", json={})).status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    # Nothing became canonical: one uploaded source, no knowledge memories, research evidence never linked to a source.
    assert len((await db_session.execute(select(Source).where(Source.workspace_id == ws))).scalars().all()) == 1
    assert (await db_session.execute(select(KnowledgeMemory).where(KnowledgeMemory.workspace_id == ws))).scalars().all() == []
    run_ids = (await db_session.execute(select(ResearchRun.run_id).where(ResearchRun.conversation_id == cid))).scalars().all()
    assert len(run_ids) == 3
    evid = (await db_session.execute(select(ResearchEvidence).where(ResearchEvidence.run_id.in_(run_ids)))).scalars().all()
    assert evid and all(e.source_id is None for e in evid)
    cands = (await db_session.execute(select(ResearchArtifact).where(ResearchArtifact.workspace_id == ws))).scalars().all()
    assert [(c.promotion_status, c.run_id) for c in cands] == [("pending_review", None)]  # only the explicit paper's candidate
