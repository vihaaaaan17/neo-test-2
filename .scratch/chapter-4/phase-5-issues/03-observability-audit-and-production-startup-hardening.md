# 03: Observability Audit, Structured Telemetry & Production Startup Hardening

**What to build:**
A full observability audit and production startup hardening verification across the backend:
1. **Observability & Correlation IDs**:
   - Audit all critical service and worker paths to ensure structured logs, spans, and `ChatEvent` payloads consistently carry contextual correlation identifiers: `workspace_id`, `conversation_id`, `turn_id`, `run_id`, `mode`, `engine`, `candidate_id` / `artifact_id` (where applicable), `promotion_decision` (where applicable), and `timeline_epoch` (where applicable).
   - Ensure telemetry covers: turn lifecycle (`pending`, `running`, `completed`, `cancelled`, `failed`), research run milestones, scratchpad updates, promotion decisions, verification runs, rollback events, worker retries, and SSE stream reconnections.
   - Strictly prohibit adding a second observability framework; leverage existing logging, OpenTelemetry spans, and Redis/ChatEvent publishing.
2. **Production Startup Hardening & Fail-Fast Guards**:
   - Enforce that when `NEOSIS_ENV == "production"` or `ENVIRONMENT == "production"`:
     - Checkpointer strictly requires `AsyncPostgresSaver`; in-memory `MemorySaver` fallback is blocked and terminates process with exit code 1.
     - Database and Redis connectivity are verified during lifespan startup.
     - Critical secrets and environment variables are validated.
     - Zero credentials, tokens, or private keys are emitted in log statements or test outputs.

**Blocked by:** 02: Alembic Migration Integrity Audit & Historical State Reconciliation Engine

**Status:** ready-for-agent

- [ ] Audit and verify structured logging and event payloads in `ChatService`, `ResearchEventBroker`, `PromotionService`, and worker tasks.
- [ ] Ensure `workspace_id`, `conversation_id`, `turn_id`, `run_id`, and `timeline_epoch` are present in relevant event and log contexts.
- [ ] Add unit and startup tests in `tests/unit/services/test_production_startup.py` verifying fail-fast shutdown in production when `AsyncPostgresSaver` or critical environment configs are missing.
- [ ] Verify `MemorySaver` remains allowed in development/testing mode without leaking into production.
- [ ] Run secret leak detection across code and test fixtures to ensure no credentials or sensitive tokens are exposed.
