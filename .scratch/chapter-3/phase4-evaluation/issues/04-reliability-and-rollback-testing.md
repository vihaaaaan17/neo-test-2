# 04: Reliability & Rollback Testing

**What to build:** Centralize engine resolution behind an `ACTIVE_RESEARCH_ENGINE` feature flag in `ResearchEngineFactory`. Write a `test_rollback.py` integration test to validate the safety of switching engines. Add a reliability test suite to simulate worker restarts, budget exhaustion, and upstream timeouts, ensuring partial runs resolve safely without corrupting canonical state.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] Introduce `ACTIVE_RESEARCH_ENGINE` configuration logic in `ResearchEngineFactory`.
- [x] Write `test_rollback.py` to simulate a legacy run, flip the flag, run an ODR run, and flip back, verifying data integrity.
- [x] Write reliability tests proving that worker aborts or `ResearchBudgetExceeded` properly transition runs to `partial` or `failed` without hanging.
