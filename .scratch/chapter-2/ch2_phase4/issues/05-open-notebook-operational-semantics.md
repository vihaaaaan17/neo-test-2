## Problem Statement

During the Chapter 2 Phase 4 migration to the Open Notebook Ground execution substrate, we identified a few remaining operational edge cases that must be stabilized. Specifically, the network layer creates per-request HTTP clients (risking TCP exhaustion), caching lacks a deterministic workspace-versioning boundary, external deletion failures block or leak silently, and Open Notebook session state loss causes hallucination instead of explicit failure. We need to implement these final architectural semantics to ensure the integration is resilient, operationally safe, and completely isolated from upstream crashes.

## Solution

We will enforce the final operational invariants agreed upon in ADR 0001:
1. Move the `OpenNotebookClient` HTTP connection pool into a FastAPI Lifespan context.
2. Implement a `ground_version` / workspace version counter to safely bust the Ground response cache.
3. Decouple upstream cleanup into a Dead-Letter Queue (ORPHANED_UPSTREAM) so canonical Neosis deletions succeed instantly while tracking failed upstream cleanup.
4. Catch `404` errors for missing upstream Open Notebook sessions and translate them into a hard `409 Session State Lost` to prevent silent rehydration bugs.

## User Stories

1. As an operator scaling NeosisLM, I want the backend to reuse HTTP connections to Open Notebook via a Lifespan connection pool, so that we don't exhaust TCP ports under high query volume.
2. As a user querying my workspace, I want my Ground answers to be cached, but immediately invalidated if I add or delete a PDF, so that I don't receive stale semantic answers.
3. As a developer debugging caching, I want the cache keys to include an explicit `workspace_version` integer/hash, so that I don't have to rely on imprecise timestamps to invalidate cache entries.
4. As a user managing files, I want my canonical file deletions to succeed instantly in Neosis, even if Open Notebook is currently offline, so my workflow is not blocked.
5. As a system administrator, I want failed upstream Open Notebook deletions to eventually land in an `ORPHANED_UPSTREAM` state after retries, so that I can sweep and hard-delete them manually when the upstream service recovers.
6. As a user engaging in a Ground chat, I want an explicit error if the upstream engine crashes and loses my session memory, so that I know to start a new chat instead of getting hallucinatory, context-free answers.

## Implementation Decisions

- **Client Connection Pool**: We will modify `app/integrations/open_notebook/client.py` and `app/main.py` (or dependency injection) to attach an `httpx.AsyncClient` to the FastAPI app state during startup and close it during shutdown. The `OpenNotebookClient` will accept this shared pool rather than instantiating its own.
- **Cache Safety (Workspace Version)**: We will add a `ground_version` integer column to the Workspace or WorkspaceBinding schema. This version will increment whenever a background source projection marks a source as `ACTIVE` or `DELETED`. This version integer will be appended to any future Ground cache keys.
- **Terminal Deletion State**: We will modify the Arq reconciliation worker. If an upstream deletion fails beyond the configured `failure_threshold`, we will update the binding status in Postgres to `ORPHANED_UPSTREAM` and gracefully acknowledge the Arq task instead of throwing an infinite exception.
- **Session State Loss**: We will add a specific error mapping in `app/integrations/open_notebook/client.py`. If Open Notebook returns a 404 for a session ID during chat, we will raise an `HTTPException(status_code=409, detail="session_state_lost")`.

## Testing Decisions

- We will write an integration test verifying that a simulated 404 from the upstream chat session correctly raises a `409 Conflict`.
- We will unit test the FastAPI Lifespan to ensure the `httpx.AsyncClient` is properly injected into the router dependencies without memory leaks.
- We will mock the Arq worker and `httpx` to trigger 5 consecutive timeout failures during an upstream deletion, verifying that the database status correctly lands on `ORPHANED_UPSTREAM`.
- We will verify that deleting a Canonical Neosis source completes synchronously with a 204 or 200, without waiting for the background Open Notebook HTTP calls to finish.

## Out of Scope

- Implementing the actual Redis response caching layer (we are only building the `workspace_version` variable necessary for cache safety, to unblock the caching team in Chapter 3).
- Building an automated UI/Admin dashboard for `ORPHANED_UPSTREAM` (it is sufficient to just leave the rows in the database for DBA sweeps right now).
- Automatic replay/rehydration of lost chat history (Chapter 3 will tackle full history replay).

## Further Notes

- Reference `docs/adr/0001-open-notebook-operational-semantics.md` for the original architectural reasoning.
