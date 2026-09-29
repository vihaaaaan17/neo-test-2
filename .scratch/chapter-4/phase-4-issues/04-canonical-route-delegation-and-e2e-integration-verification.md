# Ticket 04: Canonical Route Delegation & End-to-End Integration Verification

**What to build:**
Delegate all legacy and duplicate endpoints (`POST /workspaces/{id}/research`, `POST /workspaces/{id}/ask`, etc.) to canonical `ChatService` with deprecation headers; retire orphaned execution helpers; and implement the comprehensive Phase 4 end-to-end test suite (`test_ground_research_ground.py`, `test_research_promotion.py`, `test_unified_turn_stream.py`, `test_cancellation_and_fence.py`) followed by full regression verification.

**Blocked by:** Ticket 01, Ticket 02, Ticket 03.

**Status:** ready-for-agent

## Scope & Changes
1. **Legacy Route Delegation & Cleanup (`app/api/routes/workspaces.py` & `app/api/routes/research.py`)**:
   - `POST /workspaces/{workspace_id}/research`: Ensure it looks up active conversation, delegates to `ChatService.submit_turn(mode="research")`, attaches `Deprecation: true` and `Link: </api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns>; rel="successor-version"`, and returns backward-compatible `{job_id, run_id, turn_id, status}`.
   - `POST /workspaces/{workspace_id}/ask`: Delegates to `ChatService.submit_turn(mode="ground")` with deprecation headers.
   - Remove orphaned/dead `enqueue_research_job()` from `app/api/routes/research.py`.

2. **Phase 4 End-to-End Integration Test Suite**:
   - `tests/e2e/test_ground_research_ground.py`:
     - Multi-turn conversation: Turn 1 = Ground, Turn 2 = Research, Turn 3 = Ground.
     - Verify Turn 3's Ground context contains ONLY current query, prior Ground conversation, and canonical source scope.
     - Verify ZERO research evidence, research report, or scratchpad content leaks into Turn 3 Ground evidence.
   - `tests/e2e/test_research_promotion.py`:
     - Research turn completes -> candidate enters `pending_review` -> acceptance materializes `KnowledgeMemory` -> subsequent Research turn ingests approved memory.
     - Rejection preserves audit history without materialization.
   - `tests/e2e/test_unified_turn_stream.py`:
     - SSE stream on `/turns/{turn_id}/events` delivers unified event sequences for both Ground and Research turns.
     - Event replay from PostgreSQL matches live broadcast.
   - `tests/e2e/test_cancellation_and_fence.py`:
     - Cancellation of turn aborts execution and marks turn `cancelled`.
     - Timeline epoch increment fences out stale worker finalization.

3. **Codebase Knowledge Graph & Gate Ledgers**:
   - Run `graphify update .` to keep knowledge graph current.
   - Write Phase 4 gate ledgers in `.scratch/chapter-4/GATES_PHASE_4.md`.

## Acceptance Criteria
- [ ] Legacy routes delegate 100% of execution to canonical `ChatService` with deprecation headers.
- [ ] Dead placeholder paths (`enqueue_research_job`) removed.
- [ ] Ground -> Research -> Ground E2E test proves strict Ground isolation after research.
- [ ] Research -> promotion -> Research E2E test proves user-gated memory continuity.
- [ ] Unified SSE streaming and event replay pass cleanly.
- [ ] Cancellation and timeline fence E2E tests pass cleanly.
- [ ] Entire repository test suite passes with 0 regressions.
