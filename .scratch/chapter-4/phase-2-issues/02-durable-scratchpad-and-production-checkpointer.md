# 02: Durable Scratchpad State & Production Checkpointer Contract

**What to build:**
A first-class, durable PostgreSQL working-state layer (Scratchpad) that allows researchers to create, inspect, update, dismiss, and workspace-pin research observations and hypotheses. In addition, establish a resilient checkpointer lifecycle that mandates persistent `AsyncPostgresSaver` in production and fails fast upon database connection failure, while safely permitting `MemorySaver` in development and test environments.

**Blocked by:** 01: Baseline Seam Closure & Context Policy Boundary (Ground Isolation)

**Status:** closed-done

- [x] SQLAlchemy model `ScratchpadEntry` created in `app/models/scratchpad.py` with foreign keys to `workspaces`, `conversations`, `conversation_turns`, and `research_runs`
- [x] Database migration generated and applied for `scratchpad_entries` with indexes on `(workspace_id, lifecycle)`, `(conversation_id, lifecycle)`, and `(workspace_id, is_pinned_to_workspace)`
- [x] `ScratchpadRepository` implemented in `app/repositories/scratchpad.py` supporting `active`, `promoted`, `dismissed`, `superseded`, and workspace pinning
- [x] REST API routes implemented in `app/api/routes/scratchpad.py` (`POST /conversations/{id}/scratchpad`, `GET /conversations/{id}/scratchpad`, `PATCH /scratchpad/{id}`) with workspace tenant isolation
- [x] `ENVIRONMENT: str = "development"` configured in `app/core/config.py`
- [x] `get_checkpointer()` async factory implemented in `app/services/working_memory.py`
- [x] Production checkpointer validation: when `ENVIRONMENT == "production"`, `ASYNC_POSTGRES_SAVER_ENABLED=True` is enforced and failure to connect raises a fatal `RuntimeError` during startup
- [x] Ephemeral `MemorySaver` is permitted only when `ENVIRONMENT in ("development", "test")`
- [x] Startup validation hooks registered in `app/main.py` and `app/workers/settings.py`
- [x] Integration tests in `tests/unit/memory/test_scratchpad.py` and `tests/unit/memory/test_checkpointer.py` pass cleanly
