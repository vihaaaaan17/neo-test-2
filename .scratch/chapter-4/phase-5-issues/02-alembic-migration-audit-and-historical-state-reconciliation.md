# 02: Alembic Migration Integrity Audit & Historical State Reconciliation Engine

**What to build:**
A robust dual-mode migration verification harness and an idempotent historical state reconciliation engine for Chapter 4:
1. **Migration Verification Harness (`scripts/validate_migrations.py` and `tests/unit/test_migrations.py`)**:
   - Statically audits all 18 Alembic revisions to ensure strict DAG linearity (single head, no forks, no missing down-revisions), existence of non-empty `upgrade()` and `downgrade()` functions, and presence of foreign key definitions, indexes, and primary keys on all tables (`conversations`, `conversation_turns`, `chat_events`, `scratchpad_entries`, `research_runs`, `workspace_commits`, `open_notebook_bindings`).
   - Dynamically executes forward migration (`alembic upgrade head`), transactional downgrade, and re-upgrade whenever a PostgreSQL instance is available.
2. **Historical State Reconciliation Script (`scripts/reconcile_chapter4_state.py`)**:
   - An idempotent, non-destructive CLI script supporting `--dry-run` and `--apply` flags.
   - Reconciles orphaned `GroundConversation` records by creating corresponding canonical `Conversation` records preserving original UUIDs.
   - Reconciles Open Notebook bindings to point to canonical conversation records.
   - Quarantines legacy Ground `KnowledgeMemory` records in place with metadata `{"legacy_origin": "ground_mode_pre_ch4", "quarantined_from_ground": true, "reconciled_at": "<timestamp>"}` so historical data is never deleted while ensuring `MemoryPolicy` excludes them from Ground context.
   - Links unlinked historical `ResearchRun` records to conversation turns where metadata exists.
   - Outputs a structured JSON report detailing counts for: `processed`, `updated`, `quarantined`, `skipped`, and `errors`.

**Blocked by:** 01: Full Multi-Phase Regression Audit & Invariant Hardening

**Status:** ready-for-agent

- [ ] Implement `scripts/validate_migrations.py` auditing Alembic revision DAG linearity, head consistency, and downgrade functions.
- [ ] Add unit test `tests/unit/test_migrations.py` verifying schema integrity, column nullability, foreign keys, and indexes across all models.
- [ ] Implement `scripts/reconcile_chapter4_state.py` supporting `--dry-run` and `--apply` modes.
- [ ] Verify in-place quarantine of legacy Ground `KnowledgeMemory` rows without deleting data.
- [ ] Verify reconciliation maps legacy `GroundConversation` and Open Notebook bindings to canonical `Conversation` records.
- [ ] Verify reconciliation script is strictly idempotent (running twice produces 0 further mutations).
- [ ] Provide test suite `tests/unit/test_reconciliation.py` validating the reconciliation engine on mock legacy database state.
