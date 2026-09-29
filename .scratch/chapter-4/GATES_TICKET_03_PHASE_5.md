# Gates: Chapter 4 Phase 5 - Ticket 03 (Observability Audit, Structured Telemetry & Production Startup Hardening)

Scope: Audit and harden structured telemetry across all turn, research, worker, and promotion lifecycles with standard correlation IDs (workspace_id, conversation_id, turn_id, run_id, timeline_epoch). Implement log secret sanitization and harden production lifespan startup to fail fast on missing AsyncPostgresSaver, unreachable database/Redis, or missing critical production configurations.

- [x] G1: Telemetry correlation ID propagation verified across services and events
  CHECK: pytest tests/unit/test_structured_telemetry.py -k test_correlation_id_propagation -v
  EXPECT: passed
  EVIDENCE: `test_correlation_id_propagation_in_chat_events` and `test_correlation_id_in_promotion_decision_telemetry` passed cleanly. Verified `workspace_id`, `conversation_id`, `turn_id`, `run_id`, and `timeline_epoch` are propagated in event payloads, and promotion decisions emit structured JSON audit logs.

- [x] G2: Structured log sanitizer prevents credential and secret leakage
  CHECK: pytest tests/unit/test_structured_telemetry.py -k test_log_sanitizer_redacts_secrets -v
  EXPECT: passed
  EVIDENCE: `test_log_sanitizer_redacts_secrets` and `test_secret_sanitizing_filter_intercepts_log_records` passed cleanly. Verified Bearer tokens, DB connection string passwords, JWT tokens, and API key parameters are sanitized before log emission.

- [x] G3: Production startup fails fast when AsyncPostgresSaver is absent in production
  CHECK: pytest tests/unit/services/test_production_startup.py -k test_production_fails_fast_on_ephemeral_checkpointer -v
  EXPECT: passed
  EVIDENCE: `test_production_fails_fast_on_ephemeral_checkpointer` passed cleanly. Verified `validate_production_startup("production")` raises `RuntimeError` when `ASYNC_POSTGRES_SAVER_ENABLED=False`.

- [x] G4: Production startup verifies database and Redis connectivity and fails fast if unreachable
  CHECK: pytest tests/unit/services/test_production_startup.py -k test_production_fails_fast_on_unreachable_infra -v
  EXPECT: passed
  EVIDENCE: `test_production_fails_fast_on_unreachable_infra` passed cleanly. Verified `RuntimeError` raised on database connection refusal and Redis connection refusal.

- [x] G5: Production startup validates critical configuration and rejects default insecure secrets
  CHECK: pytest tests/unit/services/test_production_startup.py -k test_production_fails_fast_on_missing_or_default_secret -v
  EXPECT: passed
  EVIDENCE: `test_production_fails_fast_on_missing_or_default_secret` passed cleanly. Verified `RuntimeError` raised when `SUPABASE_JWT_SECRET` is empty or matches insecure dev defaults.

- [x] G6: Development and testing modes allow MemorySaver and local developer fallbacks
  CHECK: pytest tests/unit/services/test_production_startup.py -k test_dev_mode_permits_ephemeral_checkpointer -v
  EXPECT: passed
  EVIDENCE: `test_dev_mode_permits_ephemeral_checkpointer` passed cleanly. Verified development and test environments execute cleanly without exceptions.

- [x] G7: Secret leak detection scan across codebase passes cleanly with 0 sensitive credentials exposed
  CHECK: python scripts/scan_secrets.py
  EXPECT: passed
  EVIDENCE: `python scripts/scan_secrets.py` passed with exit code 0; scanned 174 files across `app/`, `scripts/`, `alembic/`, `docs/`; zero sensitive credentials detected.

- [x] G8: Full multi-phase combined regression suite remains green with 0 regressions
  CHECK: pytest tests/unit/ tests/e2e/ tests/test_workspaces.py tests/test_async_sse.py
  EXPECT: passed
  EVIDENCE: Full combined regression suite executed cleanly: **184 passed, 0 failures in 57.26s**.

- [x] G9: Codebase knowledge graph updated
  CHECK: graphify update .
  EXPECT: Code graph updated
  EVIDENCE: `graphify update .` completed with exit code 0; updated 1237 nodes, 3109 edges, 49 communities in `graphify-out`.
