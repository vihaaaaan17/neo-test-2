# Ticket 13: Database Hardening (Pool, Indexes, Echo)

## User Story
As a platform engineer, I want the database layer to handle 1000 concurrent users without connection exhaustion, stale connections, or full table scans, so that the system remains responsive under real production load.

## Scope
Fix the 5 most immediate database-layer scalability failures identified in the scalability audit.

## Tasks

### 1. Configure Connection Pool (`app/core/database.py`)
- Set `pool_size=20`, `max_overflow=30`, `pool_timeout=30`, `pool_recycle=1800`, `pool_pre_ping=True`.
- Add `DEBUG_SQL: bool = False` to `Settings` in `app/core/config.py`.
- Change `echo=True` to `echo=settings.DEBUG_SQL`.

### 2. Add Missing Indexes (new Alembic migration)
Create a single migration adding composite indexes on all read-hot paths:
- `ix_workspaces_owner_id` on `workspaces(owner_id)`
- `ix_workspaces_owner_status` on `workspaces(owner_id, status)`
- `ix_document_blocks_source_sequence` on `document_blocks(source_id, sequence)`
- `ix_source_snapshots_source_id` on `source_snapshots(source_id)`
- `ix_knowledge_memories_workspace_id` on `knowledge_memories(workspace_id)`
- `ix_episodic_memories_workspace_id` on `episodic_memories(workspace_id)`

### 3. Switch WorkingMemory to AsyncPostgresSaver (`app/services/working_memory.py`)
- Replace `MemorySaver()` with `AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL)`.
- This eliminates the in-process singleton that causes cross-worker amnesia and OOM.

## Acceptance Criteria
- [ ] `pool_size` and `max_overflow` are explicitly set.
- [ ] `echo` defaults to `False` and is controlled by `DEBUG_SQL`.
- [ ] All 6 composite indexes exist in a new Alembic migration.
- [ ] `WorkingMemory` uses `AsyncPostgresSaver`, not `MemorySaver`.
- [ ] Existing tests still pass.

## Estimated Effort
~1 hour
