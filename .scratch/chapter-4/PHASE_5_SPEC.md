# Chapter 4 Phase 5 Specification: Verification, Migration, Production Readiness & Chapter 5 Handoff

## Problem Statement

Across Phases 1 through 4 of Chapter 4, the Neosis backend implemented unified conversational turns, mode-specific context assembly, immutable research candidate generation, human-governed candidate review/promotion, workspace commit versioning, worker event bridging, and cooperative cancellation.

However, prior to handing the backend off to frontend engineers in Chapter 5 and deploying into production, the backend faces critical operational and integration risks:
1. Historical workspaces and legacy records (such as pre-Chapter 4 Ground memory writes, unlinked research runs, and legacy conversation bindings) may cause data corruption or break invariants if not safely reconciled.
2. Under concurrent operations (such as racing candidate accept/reject actions, duplicate turn requests, active worker streams during workspace rollbacks, and unexpected network disconnects during SSE streaming), race conditions could violate state invariants.
3. Database migrations spanning 18 revisions must be verified for forward and downgrade reliability, foreign key constraints, indexes, and nullability to ensure zero downtime.
4. Missing structured telemetry across turn lifecycles, research runs, and promotion events risks operational blindness in production.
5. In development, permissive fallbacks (such as in-memory state savers) exist; in production, strict fail-fast validation must prevent unapproved configurations from booting.
6. Frontend developers lack a unified, frozen API contract with concrete schemas, event catalogs, lifecycle state machines, and sequence diagrams, forcing them to inspect complex backend code.

Without a rigorous hardening, reconciliation, and handoff phase, the backend cannot guarantee production reliability or seamless frontend development.

---

## Solution

Phase 5 delivers the final backend hardening, validation, and contract freeze phase for Chapter 4 without modifying the underlying execution architectures (ODR, Open Notebook, retrievers, PostgreSQL, or Neo4j):
1. **Full Multi-Phase Regression Audit**: Execute and verify zero regressions across Chapter 3, Phase 1, Phase 2, Phase 3, and Phase 4 test suites while preserving all core invariants.
2. **Dual-Mode Alembic Migration Validation**: Implement static DAG linearity checks and dynamic schema roundtrip verification to guarantee migration safety and zero data loss.
3. **Idempotent Historical State Reconciliation**: Provide `scripts/reconcile_chapter4_state.py` to reconcile legacy conversation records, safely quarantine legacy Ground memory records in-place with audit metadata, link legacy research runs, and generate comprehensive audit reports.
4. **Structured Observability Audit & Startup Hardening**: Audit telemetry fields (`workspace_id`, `conversation_id`, `turn_id`, `run_id`, `mode`, `engine`, `candidate_id`, `promotion_decision`, `timeline_epoch`) across loggers and event streams, and enforce fail-fast startup checks for production checkpointer requirements.
5. **High-Fidelity Concurrency & Failure Verification Suite**: Test simultaneous turn submissions, candidate review races with row locks (`with_for_update`), worker crash recoveries, client SSE disconnects and replay from durable cursors, and active rollback fencing.
6. **API Contract Freeze & Deprecation Cleanup**: Validate OpenAPI schemas, attach RFC 8288 deprecation headers with runtime warnings to legacy paths, and retire genuinely dead code.
7. **Comprehensive Chapter 5 Frontend Handoff**: Author complete, concrete handoff documentation with TypeScript interfaces, interaction state machines, sequence diagrams, and event catalogs.

---

## User Stories

1. As a platform engineer, I want all Chapter 3 and Chapter 4 test suites to pass without regressions, so that I can be confident new conversation features have not broken existing research and retrieval machinery.
2. As a database administrator, I want Alembic migrations to be verified for both upgrade and downgrade paths, so that future schema updates in production can be deployed and rolled back without downtime or data corruption.
3. As a database administrator, I want all foreign key relationships, indexes, and nullability constraints validated, so that orphaned records and full table scans are prevented.
4. As an operator running a migration, I want an idempotent reconciliation script with `--dry-run` and `--apply` modes, so that I can preview changes before mutating historical records.
5. As an operator running a migration, I want legacy Ground memory rows to be quarantined in-place with clear audit metadata rather than deleted, so that historical information is preserved without leaking into current Ground context.
6. As a researcher, I want legacy research runs to be linked to canonical conversation turns where possible, so that historical research can be viewed seamlessly in the unified conversation UI.
7. As an SRE, I want every API request, turn event, and worker execution to emit consistent structured identifiers (`workspace_id`, `conversation_id`, `turn_id`, `run_id`, `timeline_epoch`), so that incidents can be traced end-to-end across services.
8. As an SRE, I want the backend to fail fast on startup if production checkpointer configuration is missing or misconfigured, so that transient in-memory checkpointers never run in production environments.
9. As a researcher submitting turns, I want duplicate rapid-fire turn submissions on the same conversation to be handled gracefully without corrupting turn sequencing or launching duplicate runs.
10. As a researcher collaborating with a teammate, I want concurrent candidate review actions (e.g. simultaneous accept and reject on the same candidate) to be guarded by database row locks, so that exactly one terminal decision succeeds and duplicates are rejected.
11. As a web client user with an unstable network connection, I want to disconnect and reconnect to the turn SSE stream using a durable event cursor, so that I receive all missed events without duplicate entries or dropped messages.
12. As a researcher whose workspace was rolled back during an active research run, I want in-flight worker tasks to be fenced out immediately by the timeline epoch check, so that rolled-back workspace state is never corrupted by stale background jobs.
13. As a researcher whose worker process crashed, I want the system to cleanly mark the turn as failed or allow safe retry, so that conversations do not remain stuck in perpetual running states.
14. As a frontend engineer, I want frozen, type-safe API contracts for Conversation, Turn, ChatEvent, PromotionCandidate, and Scratchpad, so that I can develop UI components without unexpected schema changes.
15. As a frontend engineer, I want a complete SSE event catalog with exact event types, payloads, and heartbeat intervals, so that I can build robust streaming UI listeners.
16. As a frontend engineer, I want complete TypeScript interface definitions and state machine diagrams, so that I do not have to inspect backend Python source code to understand frontend requirements.
17. As an API consumer using legacy endpoints, I want backward-compatible responses along with RFC 8288 deprecation headers, so that my legacy integrations continue working while signaling the migration path.
18. As a security auditor, I want to verify that no API tokens, database credentials, or secret keys are exposed in logs, error payloads, or test outputs, so that production security compliance is maintained.

---

## Implementation Decisions

### 1. Dual-Mode Migration Verification
- Static DAG verification: Inspects all Alembic revision modules using `alembic.script.ScriptDirectory` to verify linear revision history, non-null migration IDs, and the existence of valid `upgrade()` and `downgrade()` functions.
- Dynamic Schema verification: If PostgreSQL is reachable, executes forward migration to head, tests schema constraints and table reflections, tests rollback downgrade, and reapplies upgrade head.

### 2. Historical State Reconciliation Engine
- Implemented as a standalone script: `scripts/reconcile_chapter4_state.py`.
- Arguments: `--dry-run` (default, read-only audit) and `--apply` (transactional commit).
- Legacy `GroundConversation` records without canonical representation are migrated 1-to-1 into canonical `Conversation` records preserving IDs.
- Legacy `KnowledgeMemory` rows created under Ground mode pre-Chapter 4 are updated in-place with `quarantined_from_ground: true` in metadata and explicitly excluded by `MemoryPolicy`.
- Unlinked `ResearchRun` records are associated with synthetic or mapped conversation turns where conversation metadata exists.
- Outputs a structured JSON reconciliation summary with counts for: `processed`, `updated`, `quarantined`, `skipped`, and `errors`.

### 3. Production Readiness and Startup Guards
- Startup lifespan validator: Validates database connectivity, Redis connection, and mandatory production variables.
- When `NEOSIS_ENV == "production"` or `ENVIRONMENT == "production"`, validates that `AsyncPostgresSaver` is configured and accessible; aborts startup with exit code 1 if missing.
- Telemetry validator: Ensures standard logging context formatters include `workspace_id`, `conversation_id`, `turn_id`, `run_id`, `mode`, and `timeline_epoch`.

### 4. Concurrency & Failure Test Harness
- Placed in `tests/integration/test_concurrency_and_failures.py`.
- Tests concurrency safety using `asyncio.gather` against transactional sessions:
  - Parallel turn submission with sequence integrity.
  - Competing promotion decisions using database row locking (`with_for_update`) to assert idempotency and rejection of conflicting decisions.
  - SSE generator interruption and reconnection using `Last-Event-ID` / sequence cursor catchup.
  - Worker epoch fence trigger during active simulation, confirming transition to `aborted_by_timeline_fence`.

### 5. Deprecation Policy & Compatibility
- Legacy route handlers in `app/api/routes/workspaces.py` emit RFC 8288 `Deprecation: true` and `Link` successor-version headers.
- Legacy classes `GroundModeOrchestrator` and `ResearchModeOrchestrator` emit runtime `DeprecationWarning` upon initialization while delegating execution to canonical adapters.
- Retire dead internal helper functions that have zero call sites across the codebase.

### 6. Chapter 5 Frontend Handoff Documentation Suite
- Four dedicated documentation artifacts created in `docs/`:
  - `docs/chapter4-api-contract.md`: Endpoints, methods, query parameters, request/response JSON schemas, and standard error envelopes.
  - `docs/chapter4-state-model.md`: Domain entity ERD, state transitions for Conversation, Turn, ResearchRun, Candidate, ScratchpadEntry, and WorkspaceCommit.
  - `docs/chapter4-event-catalog.md`: SSE event taxonomy, payload schemas, sequence order guarantees, and reconnect protocol.
  - `docs/chapter4-ui-handoff.md`: TypeScript contracts, client state machines, React hook recipes, and sequence diagrams for Ground and Research workflows.

---

## Testing Decisions

- **Testing Principles**: Tests must verify external behavior and system invariants, not internal private helpers.
- **Seams Tested**:
  - High-level API Seam: FastAPI endpoint execution via ASGI test client for turn creation, streaming, cancellation, and promotion.
  - Service Layer Seam: `ChatService`, `PromotionService`, and `MemoryRouter` integration.
  - Worker & Event Broker Seam: `TurnEventBroker` in-memory and Redis pub/sub channels.
  - Schema & Migration Seam: Alembic DAG and migration runners.
- **Prior Art**: Builds upon patterns established in `tests/unit/chat/test_turn_cancellation.py`, `tests/e2e/test_research_promotion.py`, and `tests/unit/workspace/test_rollback_epoch.py`.

---

## Out of Scope

- Modifying upstream Open Deep Research LangGraph internal topology or nodes.
- Modifying Open Notebook internal engine or SurrealDB schema.
- Creating a secondary database or alternative graph database.
- Building frontend UI components or React pages (strictly reserved for Chapter 5).
- Conducting massive distributed multi-node load benchmarks (focus is purely on correctness under concurrency).

---

## Further Notes

All work in Phase 5 adheres strictly to ADR-0004 and the core Chapter 4 invariant:
*"Conversation history is canonical product state; Ground evidence remains canonical source state; Research memory/derived knowledge is a separate state class and is never promoted into Ground evidence."*
