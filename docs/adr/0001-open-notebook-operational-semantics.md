# Open Notebook Operational Semantics

The Open Notebook Ground engine integration introduces a boundary between canonical Neosis state (in Postgres) and the execution state inside the isolated Open Notebook microservice. This ADR locks in the handling of connection pooling, cache invalidation, deletion reconciliation, and session state loss.

## Status

Accepted

## Implementation Decisions

### 1. Connection Pooling: FastAPI Lifespan Context
We use a shared `httpx.AsyncClient` created during the FastAPI application lifespan (startup) and cleanly closed during shutdown. It is injected into the `OpenNotebookClient` dependencies.
**Why**: Avoids TCP port exhaustion caused by per-request instantiation and prevents zombie connections associated with import-time globals.

### 2. Cache Invalidation: Workspace Version Counter
We introduce a canonical `WorkspaceVersion` counter (integer or hash) that increments whenever the Ground-visible source set changes (e.g., projection activation or deletion).
**Why**: Allows `query_hash + workspace_id + version` to act as an implicit cache buster. Relying on a simple timestamp is unreliable for distributed workers, and this enforces cache safety for Ground even if full caching isn't built yet.

### 3. Deletion Terminal State: Dead-Letter Queue (ORPHANED_UPSTREAM)
Canonical Neosis deletion succeeds immediately and synchronously. The background worker attempts to clean up the Open Notebook projection asynchronously. After bounded retries, failed cleanups are marked `ORPHANED_UPSTREAM` or `MANUAL_INTERVENTION_REQUIRED` in the DB.
**Why**: Upstream unavailability must not block the user from deleting a file in Neosis. Silently dropping the cleanup task leaks memory upstream. An explicit terminal DB status makes it operationally visible for sweeper scripts.

### 4. Session State Loss: Hard Error (409)
If a `GroundConversation`'s mapped Open Notebook session no longer exists upstream (e.g., SurrealDB crash), the backend returns a hard `409 Conflict` (Session State Lost) error.
**Why**: "Automatic replay/rehydration is not part of this migration." Silently recreating the session causes hallucinations because the LLM context window is wiped. An explicit error forces the frontend/user to handle the boundary explicitly by starting a new chat.
