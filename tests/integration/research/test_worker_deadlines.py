"""
Worker + EngineRouter + Postgres under deadline pressure, cancellation and redelivery (fake engines, no network):
  * deadline exhausted in the initial attempt   -> run/turn failed, attempt 'timeout', exactly one terminal event;
  * deadline exhausted during escalation        -> ODR answer kept (completed), specialist attempt 'timeout';
  * cancellation during an upstream call        -> run/turn cancelled, attempt 'cancelled', engine stopped;
  * answer just before the deadline             -> completed and persisted;
  * redelivered job for a finished run          -> no-op, no second terminal event.
"""
import asyncio
import json
import uuid

import pytest
from sqlalchemy import select

from app.integrations.research_engine import router as router_module
from app.integrations.research_engine.engine import ResearchEngine, turn_response
from app.integrations.research_engine.evidence import record_sources_as_evidence
from app.integrations.research_engine.router import EngineRouter
from app.models.conversation import ChatEvent, Conversation, ConversationTurn
from app.models.research import ResearchEngineAttempt, ResearchRun
from app.models.workspace import Workspace
from app.workers import tasks as worker_tasks
from app.workers.tasks import run_research_agent_job

pytestmark = pytest.mark.integration
TERMINAL_TURN = {"turn.completed", "turn.failed", "turn.cancelled", "turn.partial", "done"}


class Engine(ResearchEngine):
    def __init__(self, name, delay=0.0, hang=False, short=False, evidence=True):
        self.name, self.delay, self.hang, self.short, self.with_evidence = name, delay, hang, short, evidence
        self.cancelled = False
        self.stopped = False

    async def astream_events(self, run_id, workspace_id, objective, research_context=None, **kwargs):
        try:
            yield {"status": "executing", "message": f"{self.name} working"}
            if self.hang:
                await asyncio.sleep(60)
            await asyncio.sleep(self.delay)
            if self.with_evidence:
                await record_sources_as_evidence(workspace_id=workspace_id, run_id=run_id, retriever="t", provider="t", query=objective,
                                                 sources=[{"url": f"https://{self.name}{i}.example/doc", "title": "T",
                                                           "content": "retrieval-augmented generation reduces hallucinations"} for i in range(2)])
            text = "Short answer [1]." if self.short else ("Retrieval-augmented generation reduces hallucinations because "
                                                         "answers are grounded in retrieved documents. " * 12)
            yield turn_response(text)
        finally:
            self.stopped = True

    async def cancel(self):
        self.cancelled = True


class FakeRedis:
    """publish + pubsub (for the worker's cancellation listener)."""

    def __init__(self):
        self.published = []
        self.cancel = asyncio.Event()

    async def publish(self, channel, payload):
        self.published.append((channel, json.loads(payload)))

    def pubsub(self):
        redis = self

        class PS:
            async def subscribe(self, channel):
                return None

            async def listen(self):
                await redis.cancel.wait()
                yield {"type": "message", "data": "cancel"}

        return PS()


async def _seed(db, engine_name=None, routing_mode="auto"):
    ws, owner = uuid.uuid4(), uuid.uuid4()
    db.add(Workspace(workspace_id=ws, owner_id=owner))
    await db.flush()
    conv = Conversation(workspace_id=ws, owner_id=owner)
    db.add(conv)
    await db.flush()
    turn = ConversationTurn(conversation_id=conv.conversation_id, workspace_id=ws, owner_id=owner, sequence=1, mode="research",
                            user_message="Explain how retrieval-augmented generation reduces hallucinations.", status="running")
    db.add(turn)
    await db.flush()
    run = ResearchRun(workspace_id=ws, owner_id=owner, objective=turn.user_message, engine=engine_name, routing_mode=routing_mode,
                      status="pending", conversation_id=conv.conversation_id, turn_id=turn.turn_id)
    db.add(run)
    await db.flush()
    turn.research_run_id = run.run_id
    await db.commit()
    return ws, run.run_id, turn.turn_id


def _use_router(monkeypatch, engines: dict, deadline: float, min_specialist: float = 0.1, timeouts=None):
    made = []

    def factory(name, redis, profile, token_ceiling=None):
        made.append(engines[name])
        return engines[name]

    async def readiness(engine):
        return {"engine": engine, "state": "eligible", "eligible": True, "gate": "auto", "checks": {}, "reason": "test"}

    async def prereq(engine):
        return {"runtime": True}

    def build(routing_mode, engine_name, redis_client):
        return EngineRouter(routing_mode=routing_mode, engine=engine_name, redis_client=redis_client, engine_factory=factory,
                            readiness=readiness, prerequisites=prereq, turn_deadline_s=deadline,
                            min_specialist_time_s=min_specialist, timeouts=timeouts or {"open_deep_research": 30, "storm": 30, "gpt_researcher": 30})

    monkeypatch.setattr(worker_tasks, "build_research_engine", build)
    return made


async def _state(db, run_id, turn_id):
    db.expire_all()
    run = (await db.execute(select(ResearchRun).where(ResearchRun.run_id == run_id))).scalar_one()
    turn = (await db.execute(select(ConversationTurn).where(ConversationTurn.turn_id == turn_id))).scalar_one()
    attempts = (await db.execute(select(ResearchEngineAttempt).where(ResearchEngineAttempt.run_id == run_id)
                                 .order_by(ResearchEngineAttempt.sequence))).scalars().all()
    events = [e.event_type for e in (await db.execute(select(ChatEvent).where(ChatEvent.turn_id == turn_id)
                                                      .order_by(ChatEvent.sequence))).scalars().all()]
    return run, turn, attempts, [e for e in events if e in TERMINAL_TURN]


def _job(ws, run_id, redis=None):
    return run_research_agent_job({"job_id": f"j-{uuid.uuid4()}", "redis": redis}, workspace_id=str(ws),
                                  objective="Explain how retrieval-augmented generation reduces hallucinations.", run_id=str(run_id))


@pytest.mark.asyncio
async def test_deadline_exhausted_in_the_initial_attempt(db_session, monkeypatch):
    ws, run_id, turn_id = await _seed(db_session)
    odr = Engine("open_deep_research", hang=True)
    _use_router(monkeypatch, {"open_deep_research": odr}, deadline=1.0)
    result = await asyncio.wait_for(_job(ws, run_id), timeout=20)
    run, turn, attempts, terminal = await _state(db_session, run_id, turn_id)
    assert result["status"] == "failed" and run.status == "failed" and turn.status == "failed"
    assert [(a.engine, a.status) for a in attempts] == [("open_deep_research", "timeout")]
    assert odr.cancelled and odr.stopped
    assert terminal == ["turn.failed", "done"]


@pytest.mark.asyncio
async def test_deadline_exhausted_during_escalation_keeps_the_initial_answer(db_session, monkeypatch):
    ws, run_id, turn_id = await _seed(db_session)
    odr = Engine("open_deep_research", delay=0.3, short=True)
    storm = Engine("storm", hang=True)
    _use_router(monkeypatch, {"open_deep_research": odr, "storm": storm}, deadline=1.5)
    result = await asyncio.wait_for(_job(ws, run_id), timeout=20)
    run, turn, attempts, terminal = await _state(db_session, run_id, turn_id)
    assert result["status"] == "completed" and turn.status == "completed" and turn.assistant_message == "Short answer [1]."
    assert [(a.engine, a.status, a.trigger) for a in attempts] == [("open_deep_research", "answered", "initial"),
                                                                   ("storm", "timeout", "escalation")]
    assert run.engine == "open_deep_research" and storm.cancelled and storm.stopped
    assert terminal == ["turn.completed", "done"]


@pytest.mark.asyncio
async def test_cancellation_during_an_upstream_call(db_session, monkeypatch):
    ws, run_id, turn_id = await _seed(db_session)
    odr = Engine("open_deep_research", hang=True)
    _use_router(monkeypatch, {"open_deep_research": odr}, deadline=60)
    redis = FakeRedis()

    async def cancel_soon():
        await asyncio.sleep(0.8)
        redis.cancel.set()

    canceller = asyncio.create_task(cancel_soon())
    result = await asyncio.wait_for(_job(ws, run_id, redis), timeout=20)
    await canceller
    run, turn, attempts, terminal = await _state(db_session, run_id, turn_id)
    assert result["status"] == "cancelled" and run.status == "cancelled" and turn.status == "cancelled"
    assert [a.status for a in attempts] == ["cancelled"] and odr.stopped
    assert terminal == ["turn.cancelled", "done"]
    assert [p["status"] for c, p in redis.published if c == f"research_events:{run_id}" and p.get("status") in
            ("completed", "failed", "cancelled", "partial")] == ["cancelled"]  # exactly one terminal run event


@pytest.mark.asyncio
async def test_answer_just_before_the_deadline_is_finalized(db_session, monkeypatch):
    ws, run_id, turn_id = await _seed(db_session)
    _use_router(monkeypatch, {"open_deep_research": Engine("open_deep_research", delay=0.7)}, deadline=1.0)
    result = await asyncio.wait_for(_job(ws, run_id), timeout=20)
    run, turn, attempts, terminal = await _state(db_session, run_id, turn_id)
    assert result["status"] == "completed" and turn.status == "completed" and turn.assistant_message
    assert attempts[0].status == "answered" and terminal == ["turn.completed", "done"]


@pytest.mark.asyncio
async def test_redelivered_job_for_a_finished_run_is_a_no_op(db_session, monkeypatch):
    ws, run_id, turn_id = await _seed(db_session)
    made = _use_router(monkeypatch, {"open_deep_research": Engine("open_deep_research")}, deadline=30)
    first = await _job(ws, run_id)
    second = await _job(ws, run_id)  # ARQ redelivery
    run, turn, attempts, terminal = await _state(db_session, run_id, turn_id)
    assert first["status"] == "completed" and second.get("redelivered") is True
    assert len(made) == 1 and len(attempts) == 1 and terminal == ["turn.completed", "done"]
