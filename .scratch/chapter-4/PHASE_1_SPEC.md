# Chapter 4 Phase 1 Specification — Canonical Conversation and Turn Fabric

**Status:** ready-for-agent  
**Date:** 2026-09-24  
**Target:** Phase 1 Backend Implementation  
**Baseline Commit:** `061519f9067874cf69fed9a32a1e4dac2a6fa10b`  
**Parent Spec:** `.scratch/chapter-4/SPEC.md`  

---

## Problem Statement

In the existing architecture, the user interaction model is split across two incompatible operational paradigms:
1. **Asymmetric API Entry Points:** Ground Mode is exposed as `/ask-ground-mode` and `/chat-ground-mode`, while Research Mode is invoked via `/workspaces/{id}/research` or `/runs`. There is no single conversational container where a user can alternate between Ground and Research queries.
2. **Brittle Session Isolation:** Ground chat state is tracked via a localized `GroundConversation` tied directly to Open Notebook's internal session ID. If an upstream failure occurs or if the user wants to switch cognitive modes, the conversation cannot be continued in Research Mode.
3. **Inconsistent Transport & State Models:** Ground Mode yields streaming tokens or answers inline over HTTP, whereas Research Mode is an asynchronous background ARQ job. The client must maintain two completely different interaction models, polling schemes, and event parsing protocols.
4. **Lack of Idempotency on Turns:** Retrying a chat submission on a flaky network can trigger duplicate execution runs or double-billing on external LLM and search APIs.

---

## Solution

Phase 1 establishes the **Canonical Conversation and Turn Fabric**: a unified product-level conversational container in PostgreSQL that abstracts transport differences while enforcing identical, durable lifecycle states across both Ground and Research modes:
1. **Unified Entities:** A mode-agnostic `Conversation` model representing the session container, and a `ConversationTurn` model representing each prompt/response exchange with its own mode (`ground` | `research`), status (`pending` → `running` → `completed` | `partial` | `failed` | `cancelled`), and sequence number.
2. **Single Entry Point (`POST /turns`):** A unified endpoint that accepts `message`, `mode`, and an optional `client_request_id`.
3. **Option C Transport Handling:**
   - A canonical `ConversationTurn` row is always persisted in PostgreSQL first.
   - For `stream=true`: Ground streams Open Notebook tokens inline mapped to unified turn SSE; Research enqueues an ARQ job and bridges Redis Pub/Sub events into the SSE stream. If the client disconnects, execution continues durably in PostgreSQL.
   - For non-streaming: Returns `202 Accepted` with `turn_id` for pollable background execution.
4. **Canonical Event Streaming & Replay:** `ChatEvent` persisted in PostgreSQL for historical replay upon reconnect, paired with Redis Pub/Sub for live real-time distribution.
5. **Open Notebook Binding Migration:** Generalizes `OpenNotebookConversationBinding` so it maps a canonical Neosis `Conversation` to an upstream Open Notebook chat session, including transparent 1-time rehydration on `409 Conflict`.
6. **Backward Compatibility:** Deprecates legacy endpoints while delegating their internal execution to the new `ChatService`.

---

## User Stories

### Conversation Management
1. As an API client, I want to create a new conversation within a workspace, so that I have a distinct container for user interactions.
2. As an API client, I want to list all conversations in a workspace ordered by recency, so that the user can select previous investigation threads.
3. As an API client, I want to fetch a conversation by ID, so that I can inspect its status and last turn sequence.
4. As an API client, I want to archive a conversation, so that it is hidden from the active list while retaining audit history.
5. As a system administrator, I want conversation queries to strictly validate workspace ownership, so that cross-tenant access is impossible.

### Turn Submission & Execution
6. As a user, I want to submit a turn with `mode: "ground"`, so that the backend queries Open Notebook strictly against canonical sources.
7. As a user, I want to submit a turn with `mode: "research"`, so that the backend enqueues an autonomous research job.
8. As a user, I want to submit alternating Ground and Research turns in the same conversation, so that my investigation progresses naturally.
9. As an API client, I want to provide a `client_request_id` when submitting a turn, so that network retries return the existing turn idempotently without duplicate execution.
10. As an API client, I want turn sequence numbers to be monotonic and transaction-safe within a conversation, so that turn order is guaranteed.
11. As an API client, I want to specify an optional `source_scope` (list of `source_id`s) for a Ground turn, so that the answer is restricted to specific documents.
12. As a user, I want a Ground turn to complete and store `assistant_message` along with resolved `ground_evidence_refs`, so that every claim links back to canonical sources.
13. As a user, I want a Research turn to create a linked `ResearchRun` and return `status: "running"`, so that the background run can be tracked by run ID and turn ID.

### Streaming & Event Distribution
14. As a frontend client, I want to submit a turn with `stream=true`, so that I receive an immediate Server-Sent Events (SSE) stream.
15. As a frontend client, I want streaming Ground turns to emit incremental text tokens, strategy events, and final answer citations over SSE, so that the user sees real-time typing.
16. As a frontend client, I want streaming Research turns to bridge Redis Pub/Sub research events (planning, searching, synthesizing) into turn SSE events, so that the user sees live agent progress.
17. As a user, I want background execution to continue uninterrupted if my browser disconnects from the SSE stream, so that long-running turns are not lost.
18. As a frontend client, I want to reconnect to `GET /turns/{turn_id}/events?after_sequence={n}`, so that missed events are replayed from PostgreSQL in exact order.
19. As an API client, I want to submit a turn without `stream=true`, so that I receive an immediate `202 Accepted` response with the turn payload for polling.
20. As an API client, I want to poll `GET /turns/{turn_id}`, so that I can monitor turn status and retrieve the final assistant message asynchronously.

### Upstream Resilience & Compatibility
21. As a user, I want Ground Mode to transparently recreate its Open Notebook session on `409 session_state_lost` and retry once, so that container restarts do not break my conversation.
22. As an API client, I want legacy endpoints (`POST /ask-ground-mode`, `POST /chat-ground-mode`) to route through the canonical `ChatService`, so that existing frontend tests and clients continue working during migration.
23. As a developer, I want legacy routes to emit deprecation headers (`Deprecation: true`, `Link: </conversations/...>; rel="successor-version"`), so that consumers know to migrate to the canonical endpoints.

---

## Implementation Decisions

### 1. Data Models & Schemas
- **`Conversation` (`app/models/conversation.py`):**
  - `conversation_id`: UUID PK (v4)
  - `workspace_id`: UUID FK -> `workspaces.workspace_id` (CASCADE, Indexed)
  - `owner_id`: UUID (Indexed)
  - `title`: String(255) nullable
  - `status`: String(32) default `'active'` (`active`, `archived`)
  - `last_turn_sequence`: BigInteger default 0
  - `metadata_`: JSONB default `{}`
  - `created_at`: DateTime(timezone=True)
  - `updated_at`: DateTime(timezone=True)
  - *Constraints:* Index on `(workspace_id, updated_at.desc())`, `(workspace_id, owner_id)`.

- **`ConversationTurn` (`app/models/conversation.py`):**
  - `turn_id`: UUID PK (v4)
  - `conversation_id`: UUID FK -> `conversations.conversation_id` (CASCADE, Indexed)
  - `workspace_id`: UUID FK -> `workspaces.workspace_id` (CASCADE, Indexed)
  - `owner_id`: UUID
  - `sequence`: BigInteger (transactionally incremented per conversation)
  - `mode`: String(32) (`ground` | `research`)
  - `user_message`: Text
  - `assistant_message`: Text nullable
  - `status`: String(32) default `'pending'` (`pending`, `running`, `completed`, `partial`, `failed`, `cancelled`)
  - `research_run_id`: UUID nullable FK -> `research_runs.run_id` (Indexed)
  - `client_request_id`: String(255) nullable
  - `source_scope`: JSONB nullable (list of UUID strings)
  - `ground_evidence_refs`: JSONB default `[]`
  - `context_version`: JSONB default `{}`
  - `error_code`: String(64) nullable
  - `error_message`: Text nullable
  - `created_at`: DateTime(timezone=True)
  - `started_at`: DateTime(timezone=True) nullable
  - `completed_at`: DateTime(timezone=True) nullable
  - *Constraints:* Unique on `(conversation_id, sequence)`, Unique on `(conversation_id, client_request_id)` where not null.

- **`ChatEvent` (`app/models/conversation.py`):**
  - `event_id`: UUID PK (v4)
  - `turn_id`: UUID FK -> `conversation_turns.turn_id` (CASCADE, Indexed)
  - `sequence`: Integer (monotonic per turn)
  - `event_type`: String(64) (`status_change`, `token`, `strategy`, `citation`, `progress`, `error`, `done`)
  - `payload`: JSONB default `{}`
  - `created_at`: DateTime(timezone=True)
  - *Constraints:* Unique on `(turn_id, sequence)`.

- **`ResearchRun` Extension:**
  - Add `conversation_id` (UUID nullable FK) and `turn_id` (UUID nullable FK) to `research_runs` so background research links directly back to the triggering turn.

- **`OpenNotebookConversationBinding` Migration:**
  - Migrate `conversation_id` foreign key from `GroundConversation` to canonical `Conversation`. Keep `notebook_id` and `chat_session_id`.

### 2. Service Layer: `ChatService`
- **Location:** `app/services/chat/service.py`
- **Core Methods:**
  - `create_conversation(workspace_id, owner_id, title, metadata)`
  - `get_conversation(workspace_id, conversation_id)`
  - `list_conversations(workspace_id, owner_id, limit, offset)`
  - `submit_turn(workspace_id, conversation_id, owner_id, turn_create, stream)`
  - `_execute_ground_turn(workspace, conversation, turn, stream)`
  - `_execute_research_turn(workspace, conversation, turn, stream)`
  - `_rehydrate_open_notebook_session(workspace, conversation)`
  - `get_turn(workspace_id, conversation_id, turn_id)`
  - `list_turns(workspace_id, conversation_id, limit, offset)`
  - `get_turn_events(workspace_id, turn_id, after_sequence)`

### 3. Execution & Transport Dispatch Flow
```text
Client -> POST /conversations/{id}/turns?stream=true|false
   │
   ▼
1. Validate workspace_id & owner_id
2. If client_request_id provided, check existing turn (Idempotency) -> return if found
3. In PostgreSQL transaction:
   - SELECT last_turn_sequence FOR UPDATE on Conversation
   - Allocate sequence = last_turn_sequence + 1
   - INSERT ConversationTurn(status="pending", sequence=...)
   - UPDATE Conversation(last_turn_sequence = sequence, updated_at = now)
4. Dispatch by mode:
   ├── mode == "ground":
   │     Update Turn(status="running", started_at=now)
   │     If stream=true:
   │        Open streaming generator via OpenNotebookGroundEngine
   │        Record ChatEvents in DB & stream SSE to client
   │        On complete: Update Turn(status="completed", assistant_message=..., ground_evidence_refs=...)
   │     If stream=false:
   │        Execute ask_simple via OpenNotebookGroundEngine
   │        Update Turn(status="completed", assistant_message=...)
   │        Return HTTP 202 with TurnResponse
   │
   └── mode == "research":
         Admit via ResearchAdmissionController
         Create canonical ResearchRun(conversation_id=..., turn_id=...)
         Update Turn(status="running", research_run_id=run.run_id, started_at=now)
         Enqueue run_research_agent_job to ARQ queue "research-standard"
         If stream=true:
            Subscribe to Redis Pub/Sub channel "research_events:{run_id}"
            Bridge events into SSE format: event: progress, event: token, etc.
         If stream=false:
            Return HTTP 202 with TurnResponse (client polls /turns/{id})
```

### 4. Open Notebook 409 Transparent Recovery
- In `_execute_ground_turn`, if `open_notebook_client` raises `HTTPException(409, "session_state_lost")`:
  - Call `_rehydrate_open_notebook_session()`:
    1. Call `open_notebook_client.create_chat_session(notebook_id)` to obtain new `chat_session_id`.
    2. Update `OpenNotebookConversationBinding` with new session ID.
    3. Re-execute the turn against the new session once.
  - If it fails a second time, fail the turn with `error_code="upstream_ground_failure"`.

### 5. API Endpoints (`app/api/routes/chat.py`)
```text
POST   /api/v1/workspaces/{workspace_id}/conversations
GET    /api/v1/workspaces/{workspace_id}/conversations
GET    /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}
POST   /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns
GET    /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns
GET    /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}
GET    /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}/events
```

---

## Testing Decisions

### What Makes a Good Test
- Tests must execute through the top-level API router (`app/api/routes/chat.py`) using `httpx.AsyncClient` / FastAPI TestClient.
- Tests assert HTTP status codes, correct database mutations in PostgreSQL, monotonic sequences, SSE framing formatting (`data: {...}\n\n`), and idempotency.
- External dependencies (Open Notebook HTTP endpoints and ARQ enqueueing) are mocked via existing integration fixtures (`mock_open_notebook`, `mock_arq_redis`).

### Test Suites to Implement
1. `tests/integration/chat/test_conversation.py`:
   - Create, list, retrieve, archive conversations.
   - Tenant isolation: User B cannot access User A's conversation.
2. `tests/integration/chat/test_turns.py`:
   - Ground turn execution with mocked Open Notebook returning answer + citations.
   - Research turn submission: creates `ResearchRun`, enqueues ARQ job, returns 202.
   - Monotonic turn sequence ordering across concurrent submissions.
   - Idempotent deduplication with matching `client_request_id`.
   - Open Notebook 409 transparent session rehydration and retry.
3. `tests/integration/chat/test_events.py`:
   - SSE streaming for Ground turn (`event: token`, `event: done`).
   - SSE streaming bridge for Research turn via Redis pub/sub.
   - Event replay from database via `GET /turns/{id}/events?after_sequence=2`.

### Prior Art
- `tests/integration/test_ground_mode_api.py`: Tests SSE response streams and citation mapper.
- `tests/test_workspaces.py`: Tests workspace tenant validation and repository fixtures.

---

## Out of Scope

1. **Scratchpad & Working Memory Persistence:** Managed in Phase 2.
2. **Semantic Verifier & Critic Pipeline:** Managed in Phase 4 / Chapter 4.5.
3. **Candidate Review & Human-Controlled Promotion:** Managed in Phase 3.
4. **Workspace Rollback Fencing:** Managed in Phase 3.
5. **Frontend / UI Implementation:** Managed in Chapter 5.

---

## Further Notes

- Single Alembic migration for Phase 1: `add_chapter4_phase1_conversations.py`.
- Deprecate `/api/v1/workspaces/{id}/ask-ground-mode` and `/chat-ground-mode` with `Deprecation: true` response headers.
