# Phase 1 Baseline (ticket 01)

Recorded 2026-10-07 on the working tree **before any cutover change** (only the earlier bug fixes were applied; no Chapter 5 code changes).
Live stack: Postgres, Redis, Neo4j, MinIO, Open Notebook, freellmapi, API + worker running.

"Suite passes" for Phase 1 means **no new failures versus this file**. Tests of deleted code are deleted, not left failing.
Pre-existing failures below are documented, not fixed in Phase 1.

## How it was run

Per target (a single full `pytest tests` run stalls on a known hang, see below). Slow imports make some targets take 30–60s even for one
test, so timeouts at a 45s cap were re-run in one process with `-v` and a longer cap.

## Results by target

| Target | Result |
|---|---|
| `tests/unit` | 216 passed |
| `tests/e2e` | 18 passed |
| `tests/integration/memory` | 5 passed |
| `tests/integration/research` | 6 passed |
| `tests/integration/benchmark` | 15 passed |
| `tests/integration/test_concurrency_and_failures.py` | 10 passed |
| `tests/integration/test_open_notebook_binding.py` | 4 passed |
| `tests/integration/test_open_notebook_provenance.py` | 4 passed |
| `tests/test_chunking.py`, `test_db.py`, `test_episodic.py`, `test_export.py`, `test_graph_sync.py`, `test_ground_mode.py`, `test_health.py`, `test_hybrid_retrieval.py`, `test_knowledge.py`, `test_memory_router.py`, `test_output_graph.py`, `test_parsing.py`, `test_quota.py`, `test_research_agent.py`, `test_working_memory.py` | all passed |
| Batch: `tests/integration/chat`, `test_chat_identity.py`, `test_open_notebook_cutover.py`, `test_open_notebook_health.py`, `test_open_notebook_jobs.py`, `test_phase4_evaluation.py`, `tests/test_async_sse.py`, `test_ground_mode_api.py`, `test_tasks_export.py`, `test_versioning.py`, `test_workspaces.py` (one test deselected, see below) | 46 passed, 5 failed (150s) |
| `tests/integration/test_open_notebook_smoke.py` | 1 failed |

## Known hang (excluded from the baseline run)

- `tests/integration/chat/test_events.py::test_research_turn_sse_streaming_redis_bridge` — hangs indefinitely (it stalled the first full run).
  Deselected from every baseline run; it must stay deselected (or be recorded as hanging) when comparing.

## Pre-existing failures (fail before any Chapter 5 change)

Verified in isolation unless noted:

1. `tests/integration/chat/test_turns.py::test_monotonic_sequence_allocation` — `assert 409 == 200`.
2. `tests/integration/test_chat_identity.py::test_chat_existing_conversation` — `AssertionError: expected call not found`.
3. `tests/test_async_sse.py::test_async_sse_research_flow` — `sqlalchemy.exc.IntegrityError`.
4. `tests/test_workspaces.py::test_start_research` — `RuntimeError: Task ... starlette.middleware.base.BaseHTTPMiddleware`.
5. `tests/integration/test_open_notebook_smoke.py::test_open_notebook_ingestion_and_search` — "Source upload failed" (422 validation error from the upload route).

## Order-dependent (not a regression signal)

- `tests/test_ground_mode_api.py::test_ask_ground_mode_endpoint` fails (DBAPIError) only when run in the same process as other DB-heavy tests;
  it passes when run alone or with `test_workspaces.py` / `test_async_sse.py`. Compare it per target, not inside the large batch.

## Comparing after a ticket

Re-run the same targets; a ticket regresses only if a test that passed here now fails (excluding the order-dependent one when run in the big batch),
or a new failure appears outside the five listed above.

## Fast way to run the suite (added 2026-10-07)

A single process is much faster than per-target runs (startup/imports dominate): about 80 seconds for the whole suite.

    pytest tests -q -p no:cacheprovider

Expected result before/after each ticket: only the pre-existing failures listed above (the five plus `test_open_notebook_smoke`, and
`test_ground_mode_api` when run in the big batch).

## Update (2026-10-07, after tickets 06-08)

The known hang is fixed: `tests/integration/chat/test_events.py::test_research_turn_sse_streaming_redis_bridge` was stale. The SSE stream subscribes to `turn_events:{turn_id}`
(the worker is the sole creator of research ChatEvents, ADR 0004), but the test published on `research_events:{run_id}`; its `MockArqRedis` also lacked the sorted-set methods the ODR
rate limiter calls. The test now records events through `ChatEventService` like the worker does. No `--deselect` is needed any more; the full suite runs in about a minute.

Current expected result of the full suite: 364 passed, 6 failed - exactly the pre-existing failures listed above.

## Update (2026-10-07, after tickets 09-11)

Full suite: 390 passed, 1 skipped (opt-in real-provider smoke gate), 6 failed - still exactly the pre-existing failures above.

## Update (2026-10-07): pre-existing failures fixed

All six were stale tests; no application code changed:
1. `test_turns.py::test_monotonic_sequence_allocation` - posted a Ground turn while the research turn was still running (the service correctly
   returns 409 `conversation_turn_in_progress`); the test now marks the research turn completed first, as the worker would.
2. `test_chat_identity.py::test_chat_existing_conversation` - the Ground engine now always passes `context_config`; assertion updated.
3. `test_open_notebook_smoke.py` - Open Notebook 1.14 requires the `type` form field on `/api/sources`; the test sends `type=upload` like our client.
4. `test_async_sse.py::test_async_sse_research_flow` and 5. `test_workspaces.py::test_start_research` - the legacy `/research` route delegates to
   `ChatService`, which writes real rows, so the tests now use a real workspace row (and an async client on the test loop) instead of mocked repos.
6. `test_ground_mode_api.py::test_ask_ground_mode_endpoint` - not broken itself: test 4 leaked a mocked workspace repository override when it failed.
   Test 4 now cleans its overrides in `finally`.

Full suite now: **396 passed, 1 skipped (opt-in smoke gate), 0 failed** in about a minute.
