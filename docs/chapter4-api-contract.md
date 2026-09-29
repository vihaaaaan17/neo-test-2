# Chapter 4: Canonical API Contract Specification

**Version:** 1.0.0 (Frozen)  
**Status:** Canonical (Chapter 4 Backend Freeze / Chapter 5 Frontend Handoff)  
**Base URL:** `/api/v1`  
**Authentication:** HTTP Bearer token via `Authorization: Bearer <user_id_or_token>` header on all endpoints.

---

## 1. Overview & Architectural Principles

NeosisLM Chapter 4 exposes a unified conversational fabric across two execution paradigms:
1. **Ground Persona**: Synchronous / low-latency grounded question answering backed by Open Notebook / Hybrid Retrieval (Vector + Keyword BM25) with citation anchors.
2. **Research Persona**: Asynchronous multi-step deep research orchestrated via Open Deep Research (ODR) with background ARQ workers, streaming SSE progress events, hypothesis generation in the scratchpad, and human-in-the-loop candidate promotion into the canonical knowledge graph.

### Standard Error Envelope

All error responses from NeosisLM adhere to the standardized FastAPI error envelope:

```json
{
  "detail": "Descriptive human-readable error message"
}
```

For validation errors (HTTP 422 Unprocessable Entity):
```json
{
  "detail": [
    {
      "loc": ["body", "message"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Standard Status Codes
- `200 OK`: Request succeeded, returns requested entity or list.
- `201 Created`: Entity successfully created.
- `202 Accepted`: Asynchronous task queued / turn execution accepted (e.g., research turns, file uploads).
- `204 No Content`: Successful deletion, no body returned.
- `400 Bad Request`: Invalid transition, invalid parameters, or payload violation.
- `401 Unauthorized`: Missing or invalid Bearer token.
- `403 Forbidden`: Access denied (caller does not own resource).
- `404 Not Found`: Workspace, conversation, turn, or artifact not found.
- `409 Conflict`: Concurrency conflict, idempotency duplicate, or state transition violation.
- `422 Unprocessable Entity`: Request body validation failed.
- `500 Internal Server Error`: Unhandled server exception.

---

## 2. Workspaces API (`/api/v1/workspaces`)

### 2.1 Create Workspace
- **Method:** `POST /api/v1/workspaces/`
- **Status:** `201 Created`
- **Request Body (`WorkspaceCreate`):**
  ```json
  {
    "name": "Quantum Materials Research",
    "description": "Exploration of room-temperature superconductors",
    "research_engine": "open_deep_research"
  }
  ```
- **Response Body (`WorkspaceResponse`):**
  ```json
  {
    "workspace_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Quantum Materials Research",
    "description": "Exploration of room-temperature superconductors",
    "owner_id": "7fa85f64-5717-4562-b3fc-2c963f66afa6",
    "status": "active",
    "active_commit_id": null,
    "ground_version": 1,
    "timeline_epoch": 1,
    "research_engine": "open_deep_research",
    "created_at": "2026-09-29T12:00:00Z",
    "updated_at": "2026-09-29T12:00:00Z"
  }
  ```

### 2.2 Get Workspace
- **Method:** `GET /api/v1/workspaces/{workspace_id}`
- **Status:** `200 OK`
- **Response Body:** `WorkspaceResponse`

### 2.3 Update Workspace
- **Method:** `PATCH /api/v1/workspaces/{workspace_id}`
- **Status:** `200 OK`
- **Request Body (`WorkspaceUpdate`):**
  ```json
  {
    "name": "Quantum Materials (Archived)",
    "description": "Updated description",
    "research_engine": "open_deep_research"
  }
  ```
- **Response Body:** `WorkspaceResponse`

### 2.4 Delete Workspace
- **Method:** `DELETE /api/v1/workspaces/{workspace_id}`
- **Status:** `204 No Content`
- **Description:** Initiates soft-deletion with background tombstone cleanup.

### 2.5 Upload Source File
- **Method:** `POST /api/v1/workspaces/{workspace_id}/files`
- **Content-Type:** `multipart/form-data`
- **Status:** `202 Accepted`
- **Form Data:** `file: UploadFile`
- **Response Body (`SourceResponse`):**
  ```json
  {
    "source_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "workspace_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "filename": "superconductor_paper.pdf",
    "size": 1048576,
    "checksum_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "processing_status": "pending",
    "created_at": "2026-09-29T12:00:00Z"
  }
  ```

### 2.6 Get Source Processing Status
- **Method:** `GET /api/v1/workspaces/{workspace_id}/sources/{source_id}/status`
- **Status:** `200 OK`
- **Response Body:**
  ```json
  {
    "status": "completed"
  }
  ```
  *(Statuses: `pending`, `processing`, `completed`, `failed`)*

### 2.7 Get Projection Status
- **Method:** `GET /api/v1/workspaces/{workspace_id}/projection-status`
- **Status:** `200 OK`
- **Response Body:**
  ```json
  {
    "status": {
      "projected": 5,
      "pending": 0,
      "failed": 0
    }
  }
  ```

### 2.8 Get Output Knowledge Graph
- **Method:** `GET /api/v1/workspaces/{workspace_id}/graph`
- **Status:** `200 OK`
- **Response Body (`OutputGraph`):**
  ```json
  {
    "nodes": [
      {
        "id": "node-101",
        "label": "Material",
        "properties": {
          "name": "YBCO",
          "transition_temperature": "93K"
        },
        "provenance": {
          "derived_from_refs": ["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
          "calculation": "Derived from extraction pipeline",
          "verification_status": "verified"
        }
      }
    ],
    "edges": [
      {
        "source_id": "node-101",
        "target_id": "node-102",
        "type": "EXHIBITS_PROPERTY",
        "properties": {
          "confidence": 0.95
        }
      }
    ]
  }
  ```

### 2.9 Commit Workspace State
- **Method:** `POST /api/v1/workspaces/{workspace_id}/commits`
- **Status:** `201 Created`
- **Response Body (`WorkspaceCommitResponse`):**
  ```json
  {
    "commit_id": "4fa85f64-5717-4562-b3fc-2c963f66afa6",
    "workspace_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "parent_id": null,
    "manifest": {
      "schema_version": 1,
      "active_knowledge_ids": ["5fa85f64-5717-4562-b3fc-2c963f66afa6"],
      "accepted_artifact_ids": ["6fa85f64-5717-4562-b3fc-2c963f66afa6"],
      "output_graph_version": "1",
      "active_hypothesis_ids": ["7fa85f64-5717-4562-b3fc-2c963f66afa6"],
      "base_research_run_ids": ["8fa85f64-5717-4562-b3fc-2c963f66afa6"]
    },
    "created_at": "2026-09-29T12:00:00Z"
  }
  ```

### 2.10 Rollback Workspace State
- **Method:** `POST /api/v1/workspaces/{workspace_id}/rollback`
- **Status:** `200 OK`
- **Request Body (`RollbackRequest`):**
  ```json
  {
    "commit_id": "4fa85f64-5717-4562-b3fc-2c963f66afa6"
  }
  ```
- **Response Body (`WorkspaceResponse`):** Updated workspace with incremented `timeline_epoch`.

---

## 3. Conversations & Turns API (`/api/v1/workspaces/{workspace_id}/conversations`)

### 3.1 Create Conversation
- **Method:** `POST /api/v1/workspaces/{workspace_id}/conversations`
- **Status:** `201 Created`
- **Request Body (`ConversationCreate`):**
  ```json
  {
    "title": "Superconductor Exploration",
    "mode": "hybrid"
  }
  ```
- **Response Body (`ConversationResponse`):**
  ```json
  {
    "conversation_id": "2fa85f64-5717-4562-b3fc-2c963f66afa6",
    "workspace_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "owner_id": "7fa85f64-5717-4562-b3fc-2c963f66afa6",
    "title": "Superconductor Exploration",
    "status": "active",
    "last_turn_sequence": 0,
    "created_at": "2026-09-29T12:00:00Z",
    "updated_at": "2026-09-29T12:00:00Z"
  }
  ```

### 3.2 List Conversations
- **Method:** `GET /api/v1/workspaces/{workspace_id}/conversations`
- **Query Parameters:**
  - `status` (string, optional): `"active"` or `"archived"` (default: `"active"`)
  - `limit` (int, optional): `1` to `100` (default: `50`)
  - `offset` (int, optional): `>= 0` (default: `0`)
- **Status:** `200 OK`
- **Response Body (`ConversationListResponse`):**
  ```json
  {
    "conversations": [ ... ],
    "total": 1,
    "limit": 50,
    "offset": 0
  }
  ```

### 3.3 Get Conversation
- **Method:** `GET /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}`
- **Status:** `200 OK`
- **Response Body:** `ConversationResponse`

### 3.4 Update Conversation
- **Method:** `PATCH /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}`
- **Status:** `200 OK`
- **Request Body (`ConversationUpdate`):**
  ```json
  {
    "title": "Renamed Title",
    "status": "archived"
  }
  ```
- **Response Body:** `ConversationResponse`

### 3.5 Submit Turn (Execute Ground or Research)
- **Method:** `POST /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns`
- **Query Parameters:**
  - `stream` (bool, optional, default: `false`): If `true`, returns SSE `text/event-stream`.
- **Request Body (`TurnCreate`):**
  ```json
  {
    "message": "What is the critical temperature of YBCO and how was it discovered?",
    "mode": "ground",
    "client_request_id": "idem-key-9817234",
    "source_scope": ["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    "selected_source_ids": ["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    "research_options": {
      "engine": "open_deep_research",
      "engine_revision": "v1.2",
      "max_iterations": 3
    }
  }
  ```
- **Responses:**
  - **Ground Turn (Non-streaming):** `200 OK` returning `TurnResponse`
  - **Research Turn (Non-streaming):** `202 Accepted` returning `TurnResponse` (with `status: "running"` and `research_run_id`)
  - **Streaming Mode (`stream=true`):** `200 OK` with `Content-Type: text/event-stream` yielding SSE formatted events.
- **Response Body (`TurnResponse`):**
  ```json
  {
    "turn_id": "1fa85f64-5717-4562-b3fc-2c963f66afa6",
    "conversation_id": "2fa85f64-5717-4562-b3fc-2c963f66afa6",
    "sequence": 1,
    "mode": "ground",
    "status": "done",
    "user_message": "What is the critical temperature of YBCO?",
    "assistant_message": "The critical temperature of YBCO is 93 K.",
    "research_run_id": null,
    "client_request_id": "idem-key-9817234",
    "source_scope": ["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    "ground_evidence_refs": ["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    "context_version": {
      "ground_version": 1,
      "timeline_epoch": 1
    },
    "error_code": null,
    "error_message": null,
    "created_at": "2026-09-29T12:00:00Z",
    "started_at": "2026-09-29T12:00:01Z",
    "completed_at": "2026-09-29T12:00:03Z"
  }
  ```

### 3.6 List Conversation Turns
- **Method:** `GET /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns`
- **Query Parameters:**
  - `limit` (int, default: `50`)
  - `offset` (int, default: `0`)
- **Status:** `200 OK`
- **Response Body (`TurnListResponse`):**
  ```json
  {
    "turns": [ ... ],
    "total": 1
  }
  ```

### 3.7 Get Turn
- **Method:** `GET /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}`
- **Status:** `200 OK`
- **Response Body:** `TurnResponse`

### 3.8 List Turn Events / Replay Events
- **Method:** `GET /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}/events`
- **Query Parameters:**
  - `after_sequence` (int, default: `0`): Retrieve events strictly after this sequence index.
  - `stream` (bool, default: `false`): If `true`, stream events as SSE `text/event-stream`.
- **Status:** `200 OK`
- **Response Body (`ChatEventListResponse` when `stream=false`):**
  ```json
  {
    "events": [
      {
        "event_id": "8fa85f64-5717-4562-b3fc-2c963f66afa6",
        "turn_id": "1fa85f64-5717-4562-b3fc-2c963f66afa6",
        "sequence": 1,
        "event_type": "token",
        "payload": {
          "delta": "The ",
          "accumulated": "The "
        },
        "created_at": "2026-09-29T12:00:01Z"
      }
    ],
    "total": 1
  }
  ```

### 3.9 Cancel Turn
- **Method:** `POST /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}/cancel`
- **Status:** `200 OK`
- **Response Body:** `TurnResponse` (with `status: "cancelled"`)

---

## 4. Candidate Promotion API (`/api/v1/workspaces/{workspace_id}/promotions`)

### 4.1 List Promotion Candidates
- **Method:** `GET /api/v1/workspaces/{workspace_id}/promotions`
- **Query Parameters:**
  - `status` (string, optional): `"pending_review"`, `"accepted"`, `"rejected"` (default: `"pending_review"`)
  - `run_id` (UUID, optional): Filter by source ResearchRun ID.
- **Status:** `200 OK`
- **Response Body:** `List[PromotionCandidateResponse]`
  ```json
  [
    {
      "artifact_id": "6fa85f64-5717-4562-b3fc-2c963f66afa6",
      "run_id": "8fa85f64-5717-4562-b3fc-2c963f66afa6",
      "artifact_type": "knowledge_memory",
      "promotion_status": "pending_review",
      "payload": {
        "text": "YBCO exhibits high-Tc superconductivity up to 93 K.",
        "confidence": 0.98,
        "provenance": {
          "sources": ["paper-1.pdf"],
          "run_id": "8fa85f64-5717-4562-b3fc-2c963f66afa6"
        }
      },
      "created_at": "2026-09-29T12:05:00Z"
    }
  ]
  ```

### 4.2 Get Promotion Candidate
- **Method:** `GET /api/v1/workspaces/{workspace_id}/promotions/{artifact_id}`
- **Status:** `200 OK`
- **Response Body:** `PromotionCandidateResponse`

### 4.3 Accept Promotion Candidate
- **Method:** `POST /api/v1/workspaces/{workspace_id}/promotions/{artifact_id}/accept`
- **Status:** `200 OK`
- **Request Body (`PromotionReviewRequest`):**
  ```json
  {
    "notes": "Verified experimentally with citation ref"
  }
  ```
- **Response Body (`PromotionReviewResponse`):**
  ```json
  {
    "artifact_id": "6fa85f64-5717-4562-b3fc-2c963f66afa6",
    "promotion_status": "accepted",
    "promoted_entity_id": "5fa85f64-5717-4562-b3fc-2c963f66afa6",
    "reviewed_at": "2026-09-29T12:10:00Z",
    "reviewer_notes": "Verified experimentally with citation ref"
  }
  ```

### 4.4 Reject Promotion Candidate
- **Method:** `POST /api/v1/workspaces/{workspace_id}/promotions/{artifact_id}/reject`
- **Status:** `200 OK`
- **Request Body (`PromotionReviewRequest`):**
  ```json
  {
    "notes": "Insufficient sample size reported in paper"
  }
  ```
- **Response Body (`PromotionReviewResponse`):**
  ```json
  {
    "artifact_id": "6fa85f64-5717-4562-b3fc-2c963f66afa6",
    "promotion_status": "rejected",
    "promoted_entity_id": null,
    "reviewed_at": "2026-09-29T12:10:00Z",
    "reviewer_notes": "Insufficient sample size reported in paper"
  }
  ```

---

## 5. Scratchpad API (`/api/v1/workspaces/{workspace_id}`)

### 5.1 Create Scratchpad Entry
- **Method:** `POST /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/scratchpad`
- **Status:** `201 Created`
- **Request Body (`ScratchpadEntryCreate`):**
  ```json
  {
    "title": "Hypothesis: Oxygen stoichiometry shift",
    "entry_type": "hypothesis",
    "content": "Transition temperature drops if oxygen content falls below 6.93",
    "pinned": true,
    "tags": ["oxygen", "stoichiometry"]
  }
  ```
- **Response Body (`ScratchpadEntryResponse`):**
  ```json
  {
    "entry_id": "7fa85f64-5717-4562-b3fc-2c963f66afa6",
    "workspace_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "conversation_id": "2fa85f64-5717-4562-b3fc-2c963f66afa6",
    "turn_id": null,
    "title": "Hypothesis: Oxygen stoichiometry shift",
    "entry_type": "hypothesis",
    "content": "Transition temperature drops if oxygen content falls below 6.93",
    "pinned": true,
    "lifecycle": "active",
    "tags": ["oxygen", "stoichiometry"],
    "created_at": "2026-09-29T12:02:00Z",
    "updated_at": "2026-09-29T12:02:00Z"
  }
  ```

### 5.2 List Scratchpad Entries for Conversation
- **Method:** `GET /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/scratchpad`
- **Query Parameters:**
  - `lifecycle` (string, optional): `"active"`, `"promoted"`, `"dismissed"`, `"superseded"`
  - `pinned_only` (bool, optional, default: `false`)
- **Status:** `200 OK`
- **Response Body (`ScratchpadEntryListResponse`):**
  ```json
  {
    "entries": [ ... ],
    "total": 1
  }
  ```

### 5.3 Get Scratchpad Entry
- **Method:** `GET /api/v1/workspaces/{workspace_id}/scratchpad/{entry_id}`
- **Status:** `200 OK`
- **Response Body:** `ScratchpadEntryResponse`

### 5.4 Update Scratchpad Entry
- **Method:** `PATCH /api/v1/workspaces/{workspace_id}/scratchpad/{entry_id}`
- **Status:** `200 OK`
- **Request Body (`ScratchpadEntryUpdate`):**
  ```json
  {
    "title": "Refined Hypothesis: O6.95",
    "content": "Updated content with confirmed measurement",
    "pinned": true,
    "lifecycle": "active"
  }
  ```
- **Response Body:** `ScratchpadEntryResponse`

---

## 6. Research Queue Status (`/api/v1/workspaces/{workspace_id}/research`)

### 6.1 Get Research Queue Status
- **Method:** `GET /api/v1/workspaces/{workspace_id}/research/queue-status`
- **Status:** `200 OK`
- **Response Body:**
  ```json
  {
    "active_runs": 1,
    "queued_runs": 0,
    "concurrency_limit": 5,
    "provider_rate_limits": {
      "tavily": { "remaining": 98, "limit": 100 },
      "open_ai": { "remaining": 490, "limit": 500 }
    }
  }
  ```

---

## 7. Deprecated Compatibility Routes (RFC 8288 Headers)

All legacy Chapter 3 / early Chapter 4 routes are preserved as backward-compatible shims. Each route automatically delegates execution to the canonical `ChatService` and returns standard RFC 8288 deprecation response headers:

- **`Deprecation: true`**
- **`Link: </api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns>; rel="successor-version"`**

| Legacy Route | Successor Canonical Endpoint | Behavior |
|:---|:---|:---|
| `POST /api/v1/workspaces/{workspace_id}/ask` | `POST /api/v1/workspaces/{workspace_id}/conversations/{conv_id}/turns` with `mode: "ground"` | Resolves or creates conversation, creates ground turn, returns `AskResponse`. |
| `POST /api/v1/workspaces/{workspace_id}/ask-ground-mode` | Same as above | Same as above. |
| `POST /api/v1/workspaces/{workspace_id}/ask/stream` | `POST .../turns?stream=true` with `mode: "ground"` | Replays SSE token stream. |
| `POST /api/v1/workspaces/{workspace_id}/chat` | `POST /api/v1/workspaces/{workspace_id}/conversations/{conv_id}/turns` | Auto-detects ground/research and delegates to canonical turn. |
| `POST /api/v1/workspaces/{workspace_id}/chat-ground-mode` | `POST .../turns` with `mode: "ground"` | Delegates to ground turn. |
| `POST /api/v1/workspaces/{workspace_id}/research` | `POST .../turns` with `mode: "research"` | Creates research turn, queues background job, returns `ResearchRunResponse`. |
