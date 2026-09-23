# NeosisLM Chapter 2 — Phase 3 Specification
**Phase 3: PROVENANCE, CHAT, RELIABILITY, OBSERVABILITY**

## 1. Objective
Make the Phase 2 Open Notebook integration production-grade by establishing bulletproof provenance, conversational integration, robust failure recovery, observability, and tenant safety. Open Notebook remains the execution engine, but Neosis enforces the architectural boundary and shields users from internal failures.

## 2. Core Decisions & Invariants

### 2.1 Provenance Hardening
- **Partial Provenance:** Allowed. If Open Notebook returns an answer mapped partially to canonical evidence, the answer is returned to the user with a `provenance_status = "partial"` flag (and warning), stripping raw upstream IDs.
- **Zero Evidence Rejection:** If an answer returns with *zero* canonical mapped evidence, it violates the Ground mode contract. The response must fail gracefully (controlled provenance failure) and not return the hallucinated answer.

### 2.2 Chat & Session Identity
- **Canonical Model:** Introduce `GroundConversation` in Neosis to own authorization, workspace boundaries, and metadata.
- **Binding:** Introduce `OpenNotebookConversationBinding` linking `Neosis conversation_id` -> `Open Notebook session_id`.
- **Failure:** Open Notebook owns the actual context window. If Open Notebook loses the session (404), do not silently rehydrate. Fail the request explicitly with `conversation_session_expired`.

### 2.3 Projection Idempotency & Lifecycle
- **Canonical Bindings:** Standard idempotency relies on `OpenNotebookSourceBinding` states.
- **Reconciliation:** We will not check upstream list endpoints on every projection retry. Instead, implement background reconciliation loops for ambiguous external mutations (e.g., HTTP timeouts, worker crashes).
- **Deletion Tombstones:** Introduce a `DeletionTombstone` table. When Neosis deletes a workspace/source, canonical data is deleted instantly. The tombstone guarantees eventual cleanup intent against Open Notebook without blocking the user.

### 2.4 Streaming (SSE)
- **Dedicated Route:** Introduce `POST /api/v1/workspaces/{workspace_id}/ask/stream` (or similar depending on standard API routing) to translate Open Notebook streaming tokens into Neosis SSE conventions (e.g., `answer.started`, `answer.delta`, `answer.completed`).

### 2.5 Observability
- **Primary:** Rely on standard OpenTelemetry context propagation (W3C headers).
- **Supplemental:** Explicitly inject `X-Neosis-Run-ID`, `X-Neosis-Task-ID`, and `X-Neosis-Request-ID` into `OpenNotebookClient` requests for domain-level log correlation.

### 2.6 Circuit Breaking & Outage Handling
- **Circuit Breaker:** Implement an in-memory Circuit Breaker in `OpenNotebookClient` that trips on network/5xx transport failures. When OPEN, `/ask` requests immediately return `503 Service Unavailable` without exhaustively consuming the worker thread pool.
- **No Hidden Fallback:** Do not fallback to legacy RAG if the breaker trips.

### 2.7 Error Translation
- **Strict Domain Mapping:** Upstream 4xx/5xx responses must be trapped and translated to standard Neosis HTTP domain errors (e.g., `ground_validation_error` -> 400, `ground_dependency_unavailable` -> 503).
- **Masking:** Raw Open Notebook messages (SurrealDB queries, stack traces) must be strictly scrubbed from the API response and restricted to internal telemetry/logs.

### 2.8 Backpressure & Concurrency
- **Bounded Queue:** Introduce a dedicated Arq queue with a bounded concurrency limit specifically for Open Notebook source projection jobs to prevent batch uploads from DDoSing the upstream container.
- **429 Safeguard:** Implement exponential backoff in the worker to handle upstream throttling explicitly. 

### 2.9 Cache & Derived-State Safety
- **Strict Isolation:** If any response caching is implemented (present or future), the cache key must explicitly incorporate: `query_hash` + `workspace_id` + `active_commit_id`.
- **Staleness Protection:** Changing evidence (advancing the active commit) must explicitly bust/miss the cache.
