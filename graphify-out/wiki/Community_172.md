# Community 172

> 18 nodes · cohesion 0.18

## Key Concepts

- **test_startup_migration_retry.py** (9 connections) — `references/open-notebook/tests/test_startup_migration_retry.py`
- **lifespan()** (7 connections) — `references/open-notebook/api/main.py`
- **_run_database_migrations()** (7 connections) — `references/open-notebook/api/main.py`
- **FakeMigrationManager** (6 connections) — `references/open-notebook/tests/test_startup_migration_retry.py`
- **_wait_for_database()** (4 connections) — `references/open-notebook/api/main.py`
- **asyncio** (4 connections)
- **test_database_reachable_on_first_probe_runs_migrations_once()** (4 connections) — `references/open-notebook/tests/test_startup_migration_retry.py`
- **test_database_retry_succeeds_after_initial_probe_failures()** (4 connections) — `references/open-notebook/tests/test_startup_migration_retry.py`
- **test_lifespan_does_not_retry_real_migration_errors()** (4 connections) — `references/open-notebook/tests/test_startup_migration_retry.py`
- **test_lifespan_raises_after_database_retry_budget_exhausted()** (4 connections) — `references/open-notebook/tests/test_startup_migration_retry.py`
- **FastAPI** (2 connections)
- **no_retry_delay()** (2 connections) — `references/open-notebook/tests/test_startup_migration_retry.py`
- **Wait for SurrealDB to accept connections before running migrations. Docker…** (1 connections) — `references/open-notebook/api/main.py`
- **Run startup database migrations after SurrealDB is reachable.** (1 connections) — `references/open-notebook/api/main.py`
- **Lifespan event handler for the FastAPI application. Runs database migrations…** (1 connections) — `references/open-notebook/api/main.py`
- **.__init__()** (1 connections) — `references/open-notebook/tests/test_startup_migration_retry.py`
- **fixture** (1 connections)
- **Tests for API startup migration retry behavior.** (1 connections) — `references/open-notebook/tests/test_startup_migration_retry.py`

## Relationships

- [Community 1](Community_1.md) (5 shared connections)
- [Community 174](Community_174.md) (2 shared connections)
- [Community 88](Community_88.md) (1 shared connections)
- [Community 181](Community_181.md) (1 shared connections)

## Source Files

- `references/open-notebook/api/main.py`
- `references/open-notebook/tests/test_startup_migration_retry.py`

## Audit Trail

- EXTRACTED: 35 (97%)
- INFERRED: 1 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*