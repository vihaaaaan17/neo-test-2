# 08: Worker Owns Terminal State and Cancellation

**What to build:**
The worker becomes the only writer of terminal run state and the only publisher of terminal events. Engines raise on
failure instead of yielding terminal statuses. Cancellation runs through a worker-owned child task and the normal
finalization path.

**Blocked by:** 07

**Status:** done (2026-10-07)

- [x] Engine contract: `astream_events` yields only progress events and one `final_report`; it raises on failure.
      Remove the engine's `except` blocks that yield `failed`, `partial`, `cancelled`, and its `aborted_by_timeline_fence` yield.
      `ResearchBudgetExceeded` and `asyncio.CancelledError` propagate; other exceptions propagate unchanged.
- [x] Worker status mapping (single place): `ResearchBudgetExceeded` → `partial`; `asyncio.CancelledError` → `cancelled`;
      any other exception → `failed`; stream ends with a `final_report` → `completed`; stream ends without one → `failed` with
      reason `engine_finished_without_report`. `partial` is terminal with no salvage report; the turn message states the reason.
- [x] Exactly one terminal event is published on `research_events:{run_id}` and one terminal chat event/`done` on the turn;
      engine events are never re-published as terminal events.
- [x] Cancellation: run `engine.astream_events` consumption in a child `asyncio.Task` owned by the worker. On the Redis
      `research_cancellation:{run_id}` message the worker cancels that task, catches the resulting `CancelledError` itself and
      runs finalization (usage flush, state transition, turn finalization). `engine.cancel()` stays on the `ResearchEngine`
      interface; the ODR implementation no longer cancels `asyncio.current_task()` (remove `_current_task`).
- [x] The API (`ChatService.cancel_turn`) still writes `cancelled` for user cancels; the worker treats `InvalidTransitionError`
      from `lifecycle.transition_run` as "already terminal" and does not publish a second terminal event.
- [x] Timeline fence stays in the worker only (existing block); the worker emits one `aborted_by_timeline_fence` terminal.
- [x] Unit/e2e tests with a stub engine (not a mock of the worker): failure mapping for each exception type; no-report →
      `failed`; double-terminal prevented when the API already cancelled; cancel mid-stream ends terminal with finalization;
      no stuck `running` run after any path.
- [x] Suite shows no new failures versus the ticket-01 baseline.

## Notes (2026-10-07, implemented together with 06 and 07)

- Engine: removed all terminal-status yields and the `_current_task` self-cancel; failures propagate. `cancel()` is a no-op for ODR.
- Worker: the engine stream runs in a child task (`_consume_engine`). Mapping: `ResearchBudgetExceeded` -> `partial`; `CancelledError` -> `cancelled`; other exceptions -> `failed`;
  a stream that ends without `final_report` -> `failed` / `engine_finished_without_report`. Terminal-status events yielded by an engine are logged and ignored.
- The Redis cancel signal cancels the child task and calls `engine.cancel()`; the worker then finalizes normally. `InvalidTransitionError` (run already terminal, e.g. the API cancelled it)
  returns without a second terminal event. Turns without a report get a reason message for `failed`/`partial` (`_terminal_turn_message`).
- Tests: `tests/unit/workers/test_research_worker_terminal_state.py` (8 tests: completed, no report, exception, budget, ignored engine terminals, Redis cancel, already-terminal, message helper).
- Live check against the running stack: normal run completed (report, one memory_candidate in pending_review, no graph_candidate, one `turn.completed` + `done`);
  cancelled run ended `cancelled` with one `turn.cancelled` + `done` and no report.
