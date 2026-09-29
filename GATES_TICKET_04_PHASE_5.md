# GATES — Phase 5, Ticket 04
## Concurrency, Race Condition & Network Failure Resilience Verification Suite

**Status:** ✅ COMPLETE — All gates passed  
**Date:** 2026-09-29

---

## Deliverables

### 1. Test Suite Created
- **File:** `tests/integration/test_concurrency_and_failures.py`
- **Tests:** 10 integration tests
- **Result:** 10/10 PASS (with live PostgreSQL)

### 2. Production Bugs Found and Fixed

#### Bug A: `PromotionService.accept_candidate` — Concurrent double-materialization race
- **Location:** `app/services/research/promotion.py`
- **Problem:** `accept_candidate` read `ResearchArtifact` without `FOR UPDATE`. Two concurrent callers
  both saw `pending_review`, both proceeded to `materialize_memory_candidate`, creating 2 `KnowledgeMemory` rows.
- **Fix:** `get_candidate(for_update=True)` adds `SELECT FOR UPDATE` on the artifact row in `accept_candidate`
  and `reject_candidate`, serializing transitions through PostgreSQL row locking.

#### Bug B: `ChatEventRepository.append_event` — Concurrent sequence allocation race
- **Location:** `app/services/chat/events.py`
- **Problem:** `SELECT MAX(sequence)` + `INSERT` without a lock. Two concurrent sessions both read the same
  max sequence and both tried to INSERT with the same sequence, violating `uq_chat_event_sequence`.
- **Fix:** Acquires `SELECT FOR UPDATE` on the parent `ConversationTurn` row before reading `MAX(sequence)`,
  serializing all concurrent event appenders for the same turn.

---

## Test Inventory

| # | Test | Invariant Verified |
|---|------|--------------------|
| 1 | `test_concurrent_turn_submission_monotonic_sequences` | 8 parallel submissions → unique contiguous sequences, no gaps |
| 2 | `test_concurrent_candidate_review_row_lock` | Double accept → exactly 1 KnowledgeMemory row |
| 3 | `test_concurrent_candidate_accept_reject_race` | Accept vs reject race → unambiguous final state, no contradictory write |
| 4 | `test_sse_client_disconnect_and_resume` | Reconnect with `after_sequence` → zero dropped or duplicate events |
| 5 | `test_worker_crash_and_retry_recovery` | Worker crash → turn not permanently stuck in 'running', done event persisted |
| 6 | `test_rollback_epoch_fence_during_active_research` | Epoch increment → stale worker rejected, turn.cancelled + fence event emitted |
| 7 | `test_zero_cross_workspace_data_leakage_concurrent_turns` | Concurrent cross-workspace turns → zero row bleed |
| 8 | `test_idempotent_turn_via_client_request_id` | Same client_request_id submitted twice → 1 turn, counter not double-incremented |
| 9 | `test_turn_event_broker_concurrent_publishers` | 3 concurrent publishers × 20 events → subscriber receives all 60, zero loss |
| 10 | `test_chat_event_repository_monotonic_sequences` | 12 concurrent event appends → unique contiguous sequences |

---

## Checklist (from ticket spec)

- [x] Create `tests/integration/test_concurrency_and_failures.py`
- [x] Concurrent turn submission test verifying monotonic turn sequencing under `asyncio.gather` — PASS
- [x] Simultaneous candidate review race test verifying PostgreSQL row locking prevents duplicate promotion — PASS
- [x] SSE disconnect and resume test verifying event catchup via sequence cursor — PASS
- [x] Concurrent rollback fence test verifying stale background workers cannot write to a post-rollback workspace — PASS
- [x] Zero cross-workspace data leakage when multiple workspaces execute turns concurrently — PASS

---

## Regression Impact

- Full integration suite: **59 passed, 1 skipped**
- Pre-existing failures (Redis/Open Notebook not running in CI): 21 (unchanged from baseline)
- New regressions introduced: **0**
