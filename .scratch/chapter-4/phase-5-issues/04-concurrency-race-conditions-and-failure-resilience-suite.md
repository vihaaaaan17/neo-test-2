# 04: Concurrency, Race Condition & Network Failure Resilience Verification Suite

**What to build:**
A dedicated integration test suite (`tests/integration/test_concurrency_and_failures.py`) proving backend resilience and invariant preservation under race conditions and system failures:
1. **Duplicate Turn Submission & Sequence Concurrency**:
   - Rapid parallel turn submissions on the same conversation execute concurrently without duplicate sequence IDs or corrupted turn history.
2. **Concurrent Candidate Review & Row-Locking**:
   - Simultaneous conflicting review calls (`accept` vs `reject`, or double `accept`) on the same `PromotionCandidate` use row-level locking (`with_for_update`).
   - Exactly one transition succeeds; the competing call receives HTTP 400/409 without double materialization of `KnowledgeMemory` or duplicate Output KG nodes.
3. **Client Disconnection & Resilient SSE Reconnection**:
   - Simulated client network disconnect mid-stream during an active Research run.
   - Client reconnects with `Last-Event-ID` / `after_sequence` and receives the remainder of events in strict order, with zero dropped or duplicate messages.
4. **Worker Crash & Retry Recovery**:
   - In-flight worker failure or retry preserves consistent database state; turn does not stay permanently stuck in running status.
5. **Rollback During Active Research (Timeline Epoch Fence)**:
   - Workspace rollback occurs while a worker is actively processing an ODR research run.
   - The worker's subsequent state finalization detects `expected_epoch != current_epoch`, aborts immediately, emits `turn.cancelled` and `workspace.rollback.fence_triggered`, and leaves rolled-back workspace state untainted.

**Blocked by:** 03: Observability Audit, Structured Telemetry & Production Startup Hardening

**Status:** ready-for-agent

- [ ] Create `tests/integration/test_concurrency_and_failures.py`.
- [ ] Implement and pass concurrent turn submission test verifying monotonic turn sequencing under `asyncio.gather`.
- [ ] Implement and pass simultaneous candidate review race test verifying PostgreSQL row locking prevents duplicate promotion.
- [ ] Implement and pass SSE disconnect and resume test verifying event catchup via sequence cursor.
- [ ] Implement and pass concurrent rollback fence test verifying stale background workers cannot write to a post-rollback workspace.
- [ ] Verify zero cross-workspace data leakage when multiple workspaces execute turns concurrently.
