"""
Ground turns through the real ChatService + OpenNotebookGroundEngine + Postgres. Only the Open Notebook HTTP client is a
stand-in (it records what it was asked and answers with Open Notebook's own `[source:<id>]` inline citation format).

Covers: unscoped and scoped requests (non-streaming and streaming, `source_scope` and its `selected_source_ids` alias),
canonical evidence resolution with stored metadata, unresolved citations, invalid/foreign scopes rejected before a turn
exists, upstream failure, unexpected upstream data, cancellation, concurrent submissions, retry on a lost session,
stale-turn recovery, and Ground isolation from Research material.
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import select, update

from app.core.database import async_session_maker
from app.integrations.open_notebook.ground_engine import OpenNotebookGroundEngine
from app.models.block import DocumentBlock
from app.models.conversation import ChatEvent, Conversation, ConversationTurn
from app.models.open_notebook_binding import OpenNotebookSourceBinding, OpenNotebookWorkspaceBinding
from app.models.research import ResearchEvidence, ResearchRun
from app.models.source import Source, SourceSnapshot
from app.models.workspace import Workspace
from app.schemas.chat import TurnCreate
from app.services.chat.service import ChatService

pytestmark = pytest.mark.integration
FACT = "The scaled dot-product attention score is softmax(QK^T / sqrt(d_k)) V."


class FakeON:
    def __init__(self):
        self.calls = []
        self.cite: list[str] = []  # upstream ids the next answer cites inline
        self.fail: Exception | None = None
        self.gate: asyncio.Event | None = None
        self.lose_session_once = False
        self.raw_answer = None
        self.search_hits: list = []
        self.sessions = 0

    async def create_chat_session(self, notebook_id):
        self.sessions += 1
        return f"chat_session:{uuid.uuid4().hex[:8]}"

    async def search(self, query, limit=100):
        return list(self.search_hits)

    def _answer(self):
        return self.raw_answer if self.raw_answer is not None else (
            "According to your notes, the score is softmax(QK^T / sqrt(d_k)) V " + " ".join(f"[{c}]" for c in self.cite) + ".")

    async def chat_execute(self, session_id, notebook_id, message, context_config=None):
        self.calls.append({"message": message, "context_config": context_config, "session_id": session_id})
        if self.lose_session_once:
            self.lose_session_once = False
            raise HTTPException(status_code=409, detail="session_state_lost")
        if self.gate is not None:
            await self.gate.wait()
        if self.fail:
            raise self.fail
        return {"answer": self._answer(), "evidence": []}

    async def chat_stream(self, session_id, notebook_id, message, context_config=None):
        self.calls.append({"message": message, "context_config": context_config, "session_id": session_id, "stream": True})
        if self.gate is not None:
            await self.gate.wait()
        if self.fail:
            raise self.fail
        for token in self._answer().split(" "):
            yield {"event": "token", "data": {"content": token + " "}}


async def _source(db, ws, owner, filename, text, on_id):
    src = Source(workspace_id=ws, owner_id=owner, processing_status="completed")
    db.add(src)
    await db.flush()
    snap = SourceSnapshot(source_id=src.source_id, file_uri="s3://x", filename=filename, size=1, checksum_sha256="0")
    db.add(snap)
    await db.flush()
    db.add(DocumentBlock(source_id=src.source_id, snapshot_id=snap.snapshot_id, block_type="text", sequence=1, text_or_ref=text))
    db.add(OpenNotebookSourceBinding(source_id=src.source_id, snapshot_id=snap.snapshot_id, checksum_sha256="0",
                                     open_notebook_source_id=on_id, projection_status="ACTIVE"))
    return src


@pytest.fixture
async def world(db_session):
    ws, owner, other_ws = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    db_session.add_all([Workspace(workspace_id=ws, owner_id=owner), Workspace(workspace_id=other_ws, owner_id=uuid.uuid4())])
    await db_session.flush()
    db_session.add(OpenNotebookWorkspaceBinding(workspace_id=ws, open_notebook_notebook_id=f"notebook:{uuid.uuid4().hex[:10]}"))
    conv = Conversation(workspace_id=ws, owner_id=owner)
    db_session.add(conv)
    tag = uuid.uuid4().hex[:8]
    notes = await _source(db_session, ws, owner, "attention-notes.txt", f"Lecture notes. {FACT} Positional encodings add order.", f"source:a{tag}")
    other = await _source(db_session, ws, owner, "rnn-notes.txt", "Recurrent networks process tokens sequentially.", f"source:b{tag}")
    foreign = await _source(db_session, other_ws, uuid.uuid4(), "attention-notes.txt", "Someone else's secret notes.", f"source:f{tag}")
    await db_session.commit()
    return {"ws": ws, "owner": owner, "conv": conv.conversation_id, "notes": notes, "other": other, "foreign": foreign,
            "on": {"notes": f"source:a{tag}", "other": f"source:b{tag}", "foreign": f"source:f{tag}"}}


def _service(fake: FakeON, session=None):
    from app.core.database import async_session_maker as _  # noqa: F401  (sessions come from the caller)
    db = session
    return ChatService(db=db, arq_redis=None, ground_engine=None, open_notebook_client=fake)


async def _turns(conv_id):
    async with async_session_maker() as s:
        return (await s.execute(select(ConversationTurn).where(ConversationTurn.conversation_id == conv_id)
                                .order_by(ConversationTurn.sequence))).scalars().all()


async def _terminal_events(turn_id):
    async with async_session_maker() as s:
        rows = (await s.execute(select(ChatEvent.event_type).where(ChatEvent.turn_id == turn_id).order_by(ChatEvent.sequence))).scalars().all()
    return [r for r in rows if r in ("done", "turn.cancelled", "turn.failed", "turn.completed")]


async def _submit(fake, w, message="What formula do my notes give for attention?", **create):
    async with async_session_maker() as s:
        return await _service(fake, s).submit_turn(w["ws"], w["conv"], w["owner"], TurnCreate(message=message, mode="ground", **create))


@pytest.mark.asyncio
async def test_unscoped_ground_answer_resolves_to_the_canonical_document(world):
    fake = FakeON()
    fake.cite = [world["on"]["notes"]]
    fake.search_hits = [{"id": world["on"]["foreign"], "title": "attention-notes.txt"}]  # instance-wide search: foreign hit
    turn = await _submit(fake, world)
    assert turn.status == "completed"
    assert turn.ground_evidence_refs == [str(world["notes"].source_id)]
    ev = turn.context_version["ground_evidence"]
    assert ev["provenance_status"] == "full" and ev["unresolved_citations"] == []
    [detail] = ev["evidence"]
    assert detail["source_id"] == str(world["notes"].source_id) and detail["title"] == "attention-notes.txt"
    assert FACT in detail["excerpt"] and detail["document_ref"].endswith(f"/sources/{world['notes'].source_id}/download")
    assert detail["cited_inline"] is True
    # Unscoped: Open Notebook was given exactly this workspace's projected sources - never the foreign one.
    sent = set(fake.calls[-1]["context_config"]["sources"])
    assert sent == {world["on"]["notes"], world["on"]["other"]}


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["source_scope", "selected_source_ids"])
async def test_scoped_ground_uses_only_the_selected_source(world, field):
    fake = FakeON()
    fake.cite = [world["on"]["notes"], world["on"]["other"]]  # the answer also cites a source outside the scope
    turn = await _submit(fake, world, **{field: [world["notes"].source_id]})
    assert turn.status == "completed"
    assert [str(x) for x in turn.source_scope] == [str(world["notes"].source_id)]  # the validated scope is persisted
    assert set(fake.calls[-1]["context_config"]["sources"]) == {world["on"]["notes"]}  # scope honoured upstream
    assert turn.ground_evidence_refs == [str(world["notes"].source_id)]
    ev = turn.context_version["ground_evidence"]
    assert ev["provenance_status"] == "partial"
    assert ev["unresolved_citations"] == [{"upstream_id": world["on"]["other"], "source_id": str(world["other"].source_id),
                                           "reason": "outside the selected source scope"}]


@pytest.mark.asyncio
async def test_scoped_streaming_ground_uses_the_scope_and_resolves_evidence(world):
    fake = FakeON()
    fake.cite = [world["on"]["notes"]]
    async with async_session_maker() as s:
        svc = _service(fake, s)
        gen = await svc.stream_turn(world["ws"], world["conv"], world["owner"],
                                    TurnCreate(message="What formula?", mode="ground", source_scope=[world["notes"].source_id]))
        frames = [f async for f in gen]
    assert any("event: done" in f for f in frames)
    [turn] = await _turns(world["conv"])
    assert turn.status == "completed" and turn.ground_evidence_refs == [str(world["notes"].source_id)]
    assert set(fake.calls[-1]["context_config"]["sources"]) == {world["on"]["notes"]}  # was ignored before the fix
    assert turn.context_version["ground_evidence"]["evidence"][0]["title"] == "attention-notes.txt"
    assert await _terminal_events(turn.turn_id) == ["done"]


@pytest.mark.asyncio
async def test_invalid_or_foreign_scope_is_rejected_before_any_turn_exists(world):
    fake = FakeON()
    with pytest.raises(HTTPException) as e:
        await _submit(fake, world, source_scope=[world["foreign"].source_id])
    assert e.value.status_code == 400
    with pytest.raises(HTTPException):
        await _submit(fake, world, source_scope=[uuid.uuid4()])
    assert await _turns(world["conv"]) == []  # nothing left behind to lock the conversation
    fake.cite = [world["on"]["notes"]]
    assert (await _submit(fake, world)).status == "completed"


@pytest.mark.asyncio
async def test_unresolved_citations_fail_closed_and_the_conversation_stays_usable(world):
    fake = FakeON()
    fake.cite = ["source:doesnotexist", world["on"]["foreign"]]
    with pytest.raises(HTTPException) as e:
        await _submit(fake, world)
    assert e.value.status_code == 422 and "source:doesnotexist" in e.value.detail and world["on"]["foreign"] in e.value.detail
    [failed] = await _turns(world["conv"])
    assert failed.status == "failed" and failed.ground_evidence_refs == []
    fake.cite = [world["on"]["notes"]]
    assert (await _submit(fake, world)).status == "completed"


@pytest.mark.asyncio
async def test_uncited_answer_is_kept_but_never_presented_as_verified(world):
    fake = FakeON()
    fake.raw_answer = "Attention weighs tokens."  # no citation at all
    turn = await _submit(fake, world)
    assert turn.status == "completed" and turn.ground_evidence_refs == []
    ev = turn.context_version["ground_evidence"]
    assert ev["provenance_status"] == "none" and ev["evidence"] == [] and ev["unresolved_citations"] == []


@pytest.mark.asyncio
async def test_upstream_failure_and_unexpected_data_close_the_turn(world):
    fake = FakeON()
    fake.fail = RuntimeError("open notebook exploded")
    with pytest.raises(HTTPException):
        await _submit(fake, world)
    fake.fail = None
    fake.raw_answer = {"not": "a string"}  # unexpected upstream data
    with pytest.raises(HTTPException):
        await _submit(fake, world)
    turns = await _turns(world["conv"])
    assert [t.status for t in turns] == ["failed", "failed"]
    for t in turns:
        assert await _terminal_events(t.turn_id) == ["done"]  # exactly one terminal event each
    fake.raw_answer, fake.cite = None, [world["on"]["notes"]]
    assert (await _submit(fake, world)).status == "completed"


@pytest.mark.asyncio
async def test_lost_upstream_session_is_retried_once(world):
    fake = FakeON()
    fake.cite, fake.lose_session_once = [world["on"]["notes"]], True
    turn = await _submit(fake, world)
    assert turn.status == "completed" and fake.sessions == 2 and len(fake.calls) == 2


@pytest.mark.asyncio
async def test_concurrent_submissions_get_one_409_and_the_conversation_recovers(world):
    fake = FakeON()
    fake.cite, fake.gate = [world["on"]["notes"]], asyncio.Event()
    first = asyncio.create_task(_submit(fake, world))
    for _ in range(100):
        if fake.calls:
            break
        await asyncio.sleep(0.05)
    with pytest.raises(HTTPException) as e:
        await _submit(fake, world, message="second, concurrent")
    assert e.value.status_code == 409 and e.value.detail == "conversation_turn_in_progress"  # protection preserved
    fake.gate.set()
    assert (await first).status == "completed"
    fake.gate = None
    assert (await _submit(fake, world, message="after")).status == "completed"


@pytest.mark.asyncio
async def test_cancelling_a_streaming_ground_turn_closes_it_once(world):
    fake = FakeON()
    fake.cite, fake.gate = [world["on"]["notes"]], asyncio.Event()
    async with async_session_maker() as s:
        svc = _service(fake, s)
        gen = await svc.stream_turn(world["ws"], world["conv"], world["owner"], TurnCreate(message="What formula?", mode="ground"))
        for _ in range(100):
            if fake.calls:
                break
            await asyncio.sleep(0.05)
        [turn] = await _turns(world["conv"])
        async with async_session_maker() as s2:
            await _service(fake, s2).cancel_turn(world["ws"], world["conv"], turn.turn_id, world["owner"])
        frames = [f async for f in gen]
    assert any("cancel" in f for f in frames)
    [turn] = await _turns(world["conv"])
    assert turn.status == "cancelled"
    assert (await _terminal_events(turn.turn_id)).count("done") == 1
    fake.gate = None
    assert (await _submit(fake, world)).status == "completed"


@pytest.mark.asyncio
async def test_cancelled_non_streaming_request_does_not_lock_the_conversation(world):
    fake = FakeON()
    fake.cite, fake.gate = [world["on"]["notes"]], asyncio.Event()
    task = asyncio.create_task(_submit(fake, world))  # e.g. the HTTP request is cancelled mid-call
    for _ in range(100):
        if fake.calls:
            break
        await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    [turn] = await _turns(world["conv"])
    assert turn.status == "cancelled" and turn.error_code == "turn_cancelled"
    fake.gate = None
    assert (await _submit(fake, world)).status == "completed"


@pytest.mark.asyncio
async def test_only_provably_dead_turns_are_recovered(world, db_session):
    fake = FakeON()
    fake.cite = [world["on"]["notes"]]
    stuck = ConversationTurn(conversation_id=world["conv"], workspace_id=world["ws"], owner_id=world["owner"], sequence=1,
                             mode="ground", user_message="crashed", status="running", started_at=datetime.now(timezone.utc))
    db_session.add(stuck)
    await db_session.execute(update(Conversation).where(Conversation.conversation_id == world["conv"]).values(last_turn_sequence=1))
    await db_session.commit()
    with pytest.raises(HTTPException) as e:  # a fresh running turn may still be executing elsewhere: keep the 409
        await _submit(fake, world)
    assert e.value.status_code == 409
    await db_session.execute(update(ConversationTurn).where(ConversationTurn.turn_id == stuck.turn_id)
                             .values(started_at=datetime.now(timezone.utc) - timedelta(hours=1)))
    await db_session.commit()
    assert (await _submit(fake, world)).status == "completed"  # the dead one was recovered first
    statuses = {t.user_message: (t.status, t.error_code) for t in await _turns(world["conv"])}
    assert statuses["crashed"] == ("failed", "stale_turn_recovered")


@pytest.mark.asyncio
async def test_ground_never_uses_research_material(world, db_session):
    run = ResearchRun(workspace_id=world["ws"], owner_id=world["owner"], objective="r", engine="open_deep_research",
                      status="completed", conversation_id=world["conv"])
    db_session.add(run)
    await db_session.flush()
    db_session.add(ResearchEvidence(run_id=run.run_id, content="research-only content", locator="https://research.example/x",
                                    provenance={"url": "https://research.example/x", "title": "Research"}))
    db_session.add(ConversationTurn(conversation_id=world["conv"], workspace_id=world["ws"], owner_id=world["owner"], sequence=1,
                                    mode="research", user_message="research q", assistant_message="RESEARCH ANSWER TEXT",
                                    status="completed", research_run_id=run.run_id))
    await db_session.execute(update(Conversation).where(Conversation.conversation_id == world["conv"]).values(last_turn_sequence=1))
    await db_session.commit()
    fake = FakeON()
    fake.cite = [world["on"]["notes"]]
    turn = await _submit(fake, world)
    sent = repr(fake.calls[-1])
    assert "research.example" not in sent and "RESEARCH ANSWER TEXT" not in sent
    assert set(fake.calls[-1]["context_config"]["sources"]) == {world["on"]["notes"], world["on"]["other"]}
    assert all("research.example" not in repr(d) for d in turn.context_version["ground_evidence"]["evidence"])
    history = turn.context_version["ground_context"].get("ground_history") or turn.context_version["ground_context"].get("history") or []
    assert "RESEARCH ANSWER TEXT" not in repr(history)
