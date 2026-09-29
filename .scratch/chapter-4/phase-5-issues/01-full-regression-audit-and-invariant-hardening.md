# 01: Full Multi-Phase Regression Audit & Invariant Hardening

**What to build:**
A comprehensive regression audit and verification harness that runs and validates all unit, integration, and end-to-end test suites across Chapter 3 and Chapter 4 Phases 1–4. The audit proves that all core system invariants remain strictly intact without regressions:
1. Ground context isolation (zero research data, memory, or report contamination).
2. Production checkpointer requirement (`AsyncPostgresSaver` strictly required in production; fails fast).
3. Candidate promotion idempotency (explicit user review required; zero automatic promotion).
4. Provenance fail-closed isolation (invalid or cross-workspace provenance rejected).
5. Timeline epoch fencing (stale workers aborted upon rollback).
6. Canonical ConversationTurn usage across all Ground and Research dispatches.

The audit records executed tests, passing counts, failures (if any), warnings, and root causes in an auditable ledger.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Execute full test suite across unit, integration, and e2e directories (`pytest tests/unit/ tests/integration/ tests/e2e/ -v`).
- [ ] Verify Chapter 3 baseline acceptance tests and Phase 1–4 tests pass cleanly.
- [ ] Audit and document all pytest warnings (deprecation, Pydantic, SQLAlchemy warnings) and verify no silent failures or memory leaks.
- [ ] Verify core invariants are verified by dedicated assertions: Ground isolation, checkpointer guard, timeline fence, promotion review requirement.
- [ ] Record complete test execution ledger and baseline counts in `.scratch/chapter-4/GATES_PHASE_5.md`.
