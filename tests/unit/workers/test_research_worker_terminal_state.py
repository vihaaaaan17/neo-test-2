"""
The worker is the only owner of terminal run state and terminal events (Chapter 5, Phase 1):
  * engines yield progress + one `turn_response`; failures are raised;
  * `completed` requires an answer, otherwise `failed` / engine_finished_without_response;
  * an ordinary turn creates no ResearchReport and no promotion candidate (Chapter 6);
  * budget exhaustion -> partial, other exceptions -> failed, cancellation -> cancelled (with finalization);
  * exactly one terminal event is published, and an already-terminal run (API cancelled it) is a no-op.
"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.integrations.research_engine.budget import ResearchBudgetExceeded
from app.models.workspace import Workspace
from app.services.research.lifecycle import InvalidTransitionError
from app.workers.tasks import _terminal_turn_message, run_research_agent_job

TERMINAL = {"completed", "failed", "partial", "cancelled", "aborted_by_timeline_fence"}


class _Harness:
    def __init__(self):
        self.workspace_id = uuid4()
        self.run_id = uuid4()
        self.user_id = uuid4()
        self.redis = MagicMock()
        self.redis.publish = AsyncMock()
        self.lifecycle = None
        self.finalize = None

    def terminal_events(self):
        events = []
        for call in self.redis.publish.await_args_list:
            channel, payload = call.args[0], call.args[1]
            if channel == f"research_events:{self.run_id}":
                data = json.loads(payload)
                if data.get("status") in TERMINAL:
                    events.append(data)
        return events

    async def run(self, stream, run_status="pending", transition_side_effect=None, current_run_status="pending"):
        mock_run = MagicMock()
        mock_run.workspace_id = self.workspace_id
        mock_run.run_id = self.run_id
        mock_run.owner_id = self.user_id
        mock_run.engine = "open_deep_research"
        mock_run.conversation_id = None
        mock_run.turn_id = None
        mock_run.status = current_run_status
        mock_ws = Workspace(workspace_id=self.workspace_id, owner_id=self.user_id)

        engine = MagicMock()
        engine.astream_events = stream
        engine.cancel = AsyncMock()
        self.engine = engine

        ctx = {"job_id": "job", "redis": self.redis, "llm_call": AsyncMock(return_value="mock")}

        with patch("app.workers.tasks.async_session_maker") as session_cls, \
             patch("app.workers.tasks.build_research_engine", return_value=engine), \
             patch("app.services.research.lifecycle.ResearchLifecycleService") as lifecycle_cls, \
             patch("app.repositories.research.ResearchRepository") as repo_cls:
            self.lifecycle = lifecycle_cls.return_value
            self.lifecycle.transition_run = AsyncMock(side_effect=transition_side_effect)

            repo = repo_cls.return_value
            repo.get_run = AsyncMock(return_value=mock_run)
            repo.list_candidates_by_status = AsyncMock(return_value=[])
            repo.list_evidence_for_run = AsyncMock(return_value=[])
            repo.create_report = AsyncMock()
            repo.create_artifact = AsyncMock()
            self.finalize = repo.create_report  # must never be called for an ordinary turn
            self.create_artifact = repo.create_artifact

            session = AsyncMock()
            session_cls.return_value.__aenter__.return_value = session
            exec_res = MagicMock()
            exec_res.scalars.return_value.first.side_effect = [mock_ws, mock_run, mock_run]
            session.execute = AsyncMock(return_value=exec_res)

            return await run_research_agent_job(
                ctx,
                workspace_id=str(self.workspace_id),
                objective="Objective",
                run_id=str(self.run_id),
                research_context={"query": "Objective"},
            )

    def final_transition(self):
        return self.lifecycle.transition_run.await_args_list[-1]


@pytest.mark.asyncio
async def test_completed_requires_an_answer_and_creates_no_report_or_candidate():
    h = _Harness()

    async def stream(*args, **kwargs):
        yield {"status": "planning", "message": "p"}
        yield {"status": "turn_response", "text": "The report"}

    result = await h.run(stream)

    assert result["status"] == "completed"
    h.finalize.assert_not_awaited()
    h.create_artifact.assert_not_awaited()
    assert h.final_transition().args[2] == "completed"
    terminals = h.terminal_events()
    assert [t["status"] for t in terminals] == ["completed"]  # exactly one terminal event
    # The answer travels as data: it is never republished as a progress event.
    assert all("text" not in json.loads(c.args[1]) for c in h.redis.publish.await_args_list)


@pytest.mark.asyncio
async def test_no_answer_means_failed():
    h = _Harness()

    async def stream(*args, **kwargs):
        yield {"status": "planning", "message": "p"}

    result = await h.run(stream)

    assert result["status"] == "failed"
    h.finalize.assert_not_awaited()
    last = h.final_transition()
    assert last.args[2] == "failed"
    assert last.args[3] == {"reason": "engine_finished_without_response"}
    assert [t["status"] for t in h.terminal_events()] == ["failed"]


@pytest.mark.asyncio
async def test_engine_exception_maps_to_failed():
    h = _Harness()

    async def stream(*args, **kwargs):
        yield {"status": "planning", "message": "p"}
        raise RuntimeError("upstream exploded")

    result = await h.run(stream)

    assert result["status"] == "failed"
    h.finalize.assert_not_awaited()
    assert "upstream exploded" in h.final_transition().args[3]["reason"]
    assert [t["status"] for t in h.terminal_events()] == ["failed"]


@pytest.mark.asyncio
async def test_budget_exceeded_maps_to_partial_without_report():
    h = _Harness()

    async def stream(*args, **kwargs):
        yield {"status": "executing", "message": "e"}
        raise ResearchBudgetExceeded("token budget exhausted")

    result = await h.run(stream)

    assert result["status"] == "partial"
    h.finalize.assert_not_awaited()  # no salvage report
    assert h.final_transition().args[2] == "partial"
    assert [t["status"] for t in h.terminal_events()] == ["partial"]


@pytest.mark.asyncio
async def test_engine_yielded_terminal_statuses_are_ignored_not_republished():
    h = _Harness()

    async def stream(*args, **kwargs):
        yield {"status": "failed", "message": "legacy-style engine failure"}
        yield {"status": "cancelled", "message": "legacy-style cancel"}
        yield {"status": "turn_response", "text": "The report"}
        yield {"status": "completed", "message": "legacy-style done"}

    result = await h.run(stream)

    assert result["status"] == "completed"
    assert [t["status"] for t in h.terminal_events()] == ["completed"]  # only the worker's own terminal event


@pytest.mark.asyncio
async def test_redis_cancel_signal_cancels_child_task_and_finalizes_as_cancelled():
    h = _Harness()
    trigger = asyncio.Event()

    class FakePubSub:
        async def subscribe(self, channel):
            return None

        async def listen(self):
            await trigger.wait()
            yield {"type": "message", "data": "cancel"}

    h.redis.pubsub = lambda: FakePubSub()
    engine_cancelled = {"flag": False}

    async def stream(*args, **kwargs):
        yield {"status": "planning", "message": "p"}
        trigger.set()
        try:
            await asyncio.sleep(30)  # would hang the job if cancellation did not stop the engine stream
        except asyncio.CancelledError:
            engine_cancelled["flag"] = True
            raise
        yield {"status": "turn_response", "text": "never reached"}  # pragma: no cover

    result = await asyncio.wait_for(h.run(stream), timeout=10)

    assert engine_cancelled["flag"] is True
    assert result["status"] == "cancelled"
    h.finalize.assert_not_awaited()
    assert h.final_transition().args[2] == "cancelled"  # worker finalization ran (no stuck 'running' run)
    assert [t["status"] for t in h.terminal_events()] == ["cancelled"]
    h.engine.cancel.assert_awaited()


@pytest.mark.asyncio
async def test_already_terminal_run_is_a_noop_with_no_second_terminal_event():
    """The API may have already cancelled the run; the worker must not publish another terminal event."""
    h = _Harness()

    async def stream(*args, **kwargs):
        yield {"status": "turn_response", "text": "The report"}

    result = await h.run(
        stream,
        transition_side_effect=InvalidTransitionError("Run is in terminal state 'cancelled'"),
        current_run_status="cancelled",
    )

    assert result["status"] == "cancelled"
    assert h.terminal_events() == []


def test_terminal_turn_message():
    assert _terminal_turn_message("failed", "boom") == "Research run failed: boom"
    assert _terminal_turn_message("partial", "Execution halted: budget") == "Research run halted: Execution halted: budget"
    assert _terminal_turn_message("completed", "ok") is None
    assert _terminal_turn_message("cancelled", "x") is None
