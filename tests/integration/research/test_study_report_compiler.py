"""
StudyReportCompiler against Postgres: gathers only this conversation's material (Ground-cited canonical sources with
passages, its research runs' evidence, scratchpad notes), validates every claim's citations against the stored text,
persists a versioned study-session report plus one pending_review candidate, enforces owner/workspace scoping in the
service, and promotes nothing.
"""
import json
import uuid

import pytest
from sqlalchemy import select

from app.models.block import DocumentBlock
from app.models.conversation import Conversation, ConversationTurn
from app.models.knowledge import KnowledgeMemory
from app.models.research import ResearchArtifact, ResearchEvidence, ResearchReport, ResearchRun
from app.models.scratchpad import ScratchpadEntry
from app.models.source import Source, SourceSnapshot
from app.models.workspace import Workspace
from app.services.research.study_report import StudyReportCompiler, StudySessionEmpty, StudySessionNotFound

pytestmark = pytest.mark.integration


async def _source(db, ws, owner, filename, texts):
    src = Source(workspace_id=ws, owner_id=owner, processing_status="completed")
    db.add(src)
    await db.flush()
    snap = SourceSnapshot(source_id=src.source_id, file_uri="s3://x", filename=filename, size=1, checksum_sha256="0")
    db.add(snap)
    await db.flush()
    db.add_all([DocumentBlock(source_id=src.source_id, snapshot_id=snap.snapshot_id, block_type="text", sequence=i,
                              text_or_ref=t) for i, t in enumerate(texts, start=1)])
    return src


async def _seed(db):
    ws, owner = uuid.uuid4(), uuid.uuid4()
    other_ws, other_owner = uuid.uuid4(), uuid.uuid4()
    db.add_all([Workspace(workspace_id=ws, owner_id=owner), Workspace(workspace_id=other_ws, owner_id=other_owner)])
    await db.flush()
    conv, other_conv = Conversation(workspace_id=ws, owner_id=owner), Conversation(workspace_id=ws, owner_id=owner)
    db.add_all([conv, other_conv])
    await db.flush()

    src = await _source(db, ws, owner, "attention-notes.pdf",
                        ["Unrelated preface about the course schedule.",
                         "Self-attention computes weighted sums over token representations using query and key scores."])
    foreign_src = await _source(db, other_ws, other_owner, "someone-elses-secrets.pdf", ["Confidential foreign workspace text."])

    ground = ConversationTurn(conversation_id=conv.conversation_id, workspace_id=ws, owner_id=owner, sequence=1, mode="ground",
                              user_message="How does self-attention work?", assistant_message="It computes weighted sums of tokens.",
                              status="completed",
                              # A forged ref to another workspace's source must never become citable.
                              ground_evidence_refs=[str(src.source_id), str(foreign_src.source_id)])
    research = ConversationTurn(conversation_id=conv.conversation_id, workspace_id=ws, owner_id=owner, sequence=2, mode="research",
                                user_message="What is RAG?", assistant_message="RAG retrieves documents before generating.",
                                status="completed")
    db.add_all([ground, research])
    await db.flush()

    run = ResearchRun(workspace_id=ws, owner_id=owner, objective="What is RAG?", engine="open_deep_research",
                      conversation_id=conv.conversation_id, turn_id=research.turn_id, status="completed")
    other_run = ResearchRun(workspace_id=ws, owner_id=owner, objective="Other", engine="open_deep_research",
                            conversation_id=other_conv.conversation_id, status="completed")
    db.add_all([run, other_run])
    await db.flush()
    research.research_run_id = run.run_id
    rag_text = "Retrieval-augmented generation combines document retrieval with generation to ground answers."
    db.add_all([
        ResearchEvidence(run_id=run.run_id, content=rag_text, locator="https://example.org/rag",
                         provenance={"url": "https://example.org/rag", "title": "RAG overview"}),
        ResearchEvidence(run_id=run.run_id, content=rag_text, locator="https://example.org/rag",
                         provenance={"url": "https://example.org/rag", "title": "RAG overview"}),
        ResearchEvidence(run_id=other_run.run_id, content="Other conversation", locator="https://other.example/x",
                         provenance={"url": "https://other.example/x", "title": "Other"}),
    ])
    db.add(ScratchpadEntry(workspace_id=ws, conversation_id=conv.conversation_id, entry_type="hypothesis",
                           content="Retrieval may reduce hallucination."))
    await db.commit()
    return {"ws": ws, "owner": owner, "conv": conv, "other_conv": other_conv, "src": src, "foreign_src": foreign_src,
            "other_ws": other_ws, "other_owner": other_owner}


def _structured(statements):
    return json.dumps({"title": "Attention and Retrieval", "sections": [{"heading": "Findings", "statements": statements}]})


@pytest.mark.asyncio
async def test_compiler_cites_only_this_sessions_material_and_promotes_nothing(db_session):
    s = await _seed(db_session)
    prompts = []

    async def fake_llm(prompt):
        prompts.append(prompt)
        n_src = 1  # catalog order: workspace sources first, then research evidence
        return _structured([
            {"text": "Self-attention computes weighted sums over token representations.", "kind": "finding", "citations": [n_src],
             "support": [{"n": n_src, "quote": "Self-attention computes weighted sums over token representations"}]},
            {"text": "Retrieval-augmented generation grounds answers with document retrieval.", "kind": "finding", "citations": [2],
             "support": [{"n": 2, "quote": "combines document retrieval with generation to ground answers"}]},
            {"text": "Retrieval-augmented generation answers are grounded by document retrieval.", "kind": "finding",
             "citations": [2]},
            {"text": "Retrieval-augmented generation was invented in 1850.", "kind": "finding", "citations": [7]},
            {"text": "Retrieval may reduce hallucination.", "kind": "hypothesis", "citations": []},
        ])

    result = await StudyReportCompiler(db_session, llm=fake_llm).compile(
        s["ws"], s["conv"].conversation_id, "Create a paper from this study session", owner_id=s["owner"])

    assert len(prompts) == 1  # one bounded call, no research
    prompt = prompts[0]
    assert "How does self-attention work?" in prompt and "What is RAG?" in prompt
    assert "Retrieval may reduce hallucination." in prompt
    assert "Self-attention computes weighted sums" in prompt  # the relevant passage, not the preface
    assert "other.example" not in prompt  # another conversation's evidence is out of scope
    assert "someone-elses-secrets" not in prompt and "Confidential" not in prompt  # another workspace's source never leaks
    assert prompt.count("https://example.org/rag") == 1  # deduplicated by URL

    content = result["content"]
    assert result["structured"] and result["version"] == 1
    assert "weighted sums over token representations. [1]" in content and "with document retrieval. [2]" in content
    assert "*[Unsupported by the collected evidence]* Retrieval-augmented generation was invented in 1850." in content
    assert "*Hypothesis (not established):* Retrieval may reduce hallucination." in content
    refs = content.split("## References")[-1]
    assert f"attention-notes.pdf (uploaded workspace source {s['src'].source_id})" in refs
    assert "https://example.org/rag (research evidence " in refs and refs.count("https://example.org/rag") == 1

    report = (await db_session.execute(select(ResearchReport).where(ResearchReport.report_id == uuid.UUID(result["report_id"])))).scalar_one()
    assert report.scope == "study_session" and report.run_id is None and report.version == "1"
    assert report.workspace_id == s["ws"] and report.conversation_id == s["conv"].conversation_id
    assert report.source_summary["workspace_source_ids"] == [str(s["src"].source_id)]
    claims = report.citations["claims"]
    assert (claims["supported"], claims["weakly_supported"], claims["unsupported"]) == (2, 1, 1)
    assert "*[Related source cited; no supporting passage verified]* Retrieval-augmented generation answers" in content
    verified_quotes = [c["quote"] for r in claims["records"] for c in r["citations"] if c["quote_verified"]]
    assert verified_quotes == ["Self-attention computes weighted sums over token representations",
                               "combines document retrieval with generation to ground answers"]

    candidate = (await db_session.execute(select(ResearchArtifact).where(ResearchArtifact.artifact_id == uuid.UUID(result["candidate_id"])))).scalar_one()
    assert candidate.promotion_status == "pending_review" and candidate.run_id is None
    assert candidate.payload["report_id"] == result["report_id"]
    assert {"ref_type": "canonical_source", "ref_id": str(s["src"].source_id)} in candidate.payload["source_refs"]

    from app.repositories.research import ResearchRepository
    listed = await ResearchRepository(db_session).list_candidates_by_status(s["ws"], status="pending_review")
    assert candidate.artifact_id in [c.artifact_id for c in listed]
    other_listed = await ResearchRepository(db_session).list_candidates_by_status(s["other_ws"], status="pending_review")
    assert candidate.artifact_id not in [c.artifact_id for c in other_listed]  # not visible to another workspace

    assert (await db_session.execute(select(KnowledgeMemory).where(KnowledgeMemory.workspace_id == s["ws"]))).scalars().all() == []


@pytest.mark.asyncio
async def test_recompilation_creates_a_new_version_and_keeps_the_previous_one(db_session):
    s = await _seed(db_session)

    async def llm(prompt):
        return _structured([{"text": "Self-attention computes weighted sums over token representations.", "kind": "finding",
                             "citations": [1]}])

    first = await StudyReportCompiler(db_session, llm=llm).compile(s["ws"], s["conv"].conversation_id, "Compile this session", owner_id=s["owner"])
    second = await StudyReportCompiler(db_session, llm=llm).compile(s["ws"], s["conv"].conversation_id, "Compile this session again", owner_id=s["owner"])
    assert (first["version"], second["version"]) == (1, 2)
    assert second["source_summary"]["previous_report_id"] == first["report_id"]
    rows = (await db_session.execute(select(ResearchReport.version).where(ResearchReport.conversation_id == s["conv"].conversation_id))).scalars().all()
    assert sorted(rows) == ["1", "2"]


@pytest.mark.asyncio
async def test_compiler_enforces_owner_and_workspace_scoping(db_session):
    s = await _seed(db_session)

    async def never(prompt):  # pragma: no cover
        raise AssertionError("must not compile for an unauthorized caller")

    with pytest.raises(StudySessionNotFound):  # another user
        await StudyReportCompiler(db_session, llm=never).compile(s["ws"], s["conv"].conversation_id, "Compile", owner_id=s["other_owner"])
    with pytest.raises(StudySessionNotFound):  # right conversation, wrong workspace
        await StudyReportCompiler(db_session, llm=never).compile(s["other_ws"], s["conv"].conversation_id, "Compile", owner_id=s["owner"])


@pytest.mark.asyncio
async def test_compiler_refuses_an_empty_session(db_session):
    s = await _seed(db_session)

    async def never(prompt):  # pragma: no cover
        raise AssertionError("no LLM call for an empty session")

    with pytest.raises(StudySessionEmpty):
        await StudyReportCompiler(db_session, llm=never).compile(s["ws"], s["other_conv"].conversation_id, "Compile this session",
                                                                owner_id=s["owner"])
