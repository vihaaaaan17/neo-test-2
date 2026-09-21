# 06: Operationalization & Final Cutover

**What to build:** Finalize structured logging in `tasks.py` and `engine.py` for operational observability. Complete `docs/CH3_RESEARCH_MIGRATION_RUNBOOK.md` with explicit operational queries, dashboards, and rollback guides. Mark the legacy `ResearchModeOrchestrator` as deprecated. Finally, check off the Final Phase 4 Exit Gate and execute cutover by flipping the default flag to ODR.

**Blocked by:** 02-provenance-audit-and-isolation-testing, 04-reliability-and-rollback-testing, 05-odr-optimization

**Status:** ready-for-agent

- [x] Ensure structured JSON logging covers run start, completion, failure, duration, and cost.
- [x] Write `docs/CH3_RESEARCH_MIGRATION_RUNBOOK.md` with health checks, incident procedures, and metric queries.
- [x] Decorate `ResearchModeOrchestrator` and related legacy logic with `@deprecated`.
- [x] Set `ACTIVE_RESEARCH_ENGINE=odr` as the production default.
- [x] Check off all items in the Phase 4 Exit Gate checklist.
