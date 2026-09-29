# Chapter 4 — Phase 4 Specification
## Unified Execution & Chapter 3 Integration

**Repository:** `vihaaaaan17/neo-test-2`  
**Phase Baseline:** Phase 1, Phase 2, and Phase 3 completed (104/104 unit tests green)  
**Governing Rule:** *"Adapt interfaces. Do not redesign engines."*

---

## Problem Statement

While Chapter 4 has established canonical conversation turns, context assembly policies, durable working state, deterministic derivation verification, candidate promotion gating, and timeline fencing, the underlying execution engines (Open Notebook Ground engine and Open Deep Research) remain partially disconnected from this canonical layer. 

Currently:
1. `ChatService` contains a raw OpenAI client bypass for Ground streaming rather than delegating directly through the canonical Open Notebook engine.
2. The Open Deep Research (ODR) engine does not ingest the rich, token-budgeted `ResearchContext` assembled by Chapter 4, nor does it emit candidates in the normalized Phase 3 candidate envelope.
3. Background research execution emits `ResearchEvent` records that are not synchronously bridged into canonical `ChatEvent`s on `turn_events:{turn_id}`, preventing the frontend from observing a unified event stream.
4. Production checkpointer enforcement allows silent in-memory `MemorySaver` fallbacks.
5. Parallel and duplicate routes exist that bypass `ChatService` or generate unlinked execution state.

---

## Solution

Integrate existing Chapter 3 execution engines seamlessly behind the canonical Chapter 4 Conversation/Turn/Context/Promotion product model:
1. **Ground Execution Exclusively via OpenNotebookGroundEngine**: Route all Ground turns (unary and streaming) through `OpenNotebookGroundEngine`, passing the source-isolated `GroundContext` and mapping citations to canonical Neosis source UUIDs. Eliminate raw LLM client bypasses.
2. **ODR Adapter Context Ingestion**: Map the canonical `ResearchContext` snapshotted on `ConversationTurn.context_version` into the initial conversational message state of the ODR graph as a structured `RESEARCH CONTEXT AND WORKING STATE` system block without altering upstream LangGraph topology.
3. **Structured Candidate Emission**: Ensure ODR finalization emits normalized candidate artifacts (`memory_candidate`, `graph_candidate`) conforming to the Phase 3 candidate envelope in `pending_review` status without auto-promotion.
4. **Synchronous ResearchEvent to ChatEvent Bridge**: Persist execution lifecycle transitions into PostgreSQL `chat_events` and broadcast to `turn_events:{turn_id}` in real-time.
5. **Unified Cancellation**: Implement canonical turn cancellation endpoint `POST /turns/{turn_id}/cancel` cascading into underlying engine tasks.
6. **Production Checkpointer Guard**: Enforce `AsyncPostgresSaver` in `production` at FastAPI and ARQ startup; fail fast if unavailable.
7. **Retire Parallel Product Paths**: Delegate legacy routes (`/workspaces/{id}/research`, `/ask`, etc.) to canonical `ChatService` with deprecation headers.

---

## User Stories

1. As a researcher, I want to ask questions in Ground mode and receive answers strictly verified against my uploaded papers, so that I can trust no unverified research findings or hallucinations contaminate the response.
2. As a researcher, I want Ground mode streaming to stream tokens and citations directly from the canonical Open Notebook engine, so that the response behavior is fast and transparent.
3. As a researcher, I want to submit a Research turn in the same conversation, so that the research agent automatically ingests my conversation history, working memory, and active scratchpad entries.
4. As a researcher, I want to monitor research agent execution via a single unified event stream, so that I can see planning, sub-agent delegation, and synthesis progress in real-time.
5. As a researcher, I want completed research runs to emit structured promotion candidates in `pending_review` status, so that findings do not pollute my knowledge base until I explicitly accept them.
6. As a researcher, I want to cancel an in-flight research or ground turn at any time through a canonical endpoint, so that compute resources are freed immediately without leaving corrupted state.
7. As a system operator, I want production deployments to fail fast on startup if durable checkpointer storage is misconfigured, so that research runs never silently run on ephemeral in-memory storage in production.
8. As an API client, I want legacy endpoints like `POST /workspaces/{id}/research` to remain functional via transparent delegation to the canonical turn service, so that existing integrations do not break.
9. As a researcher, I want to ask a follow-up Ground question after a Research turn, so that the system references my uploaded documents without injecting unpromoted research findings into Ground evidence.

---

## Implementation Decisions (ADR-0004)

### 1. Ground Engine Boundary (`app/integrations/open_notebook/ground_engine.py`)
- Update `OpenNotebookGroundEngine` to accept `workspace_id`, `conversation_id`, `turn_id`, `query`, `source_scope`, and `GroundContext`.
- Add `astream()` generator method supporting token-by-token streaming from Open Notebook.
- In `app/services/chat/service.py`: Eliminate the direct OpenAI client invocation in `_execute_ground_stream_background` and route through `OpenNotebookGroundEngine`.

### 2. ODR Context Ingestion (`app/integrations/research_engine/open_deep_research/engine.py`)
- In `astream_events`, accept `research_context: Optional[dict] = None`.
- If `research_context` is provided (or fetched from `turn.context_version`), format it into a structured `RESEARCH CONTEXT AND WORKING STATE` section and prepend to the initial user message.
- Upstream ODR graph files (`deep_researcher.py`, `configuration.py`, etc.) remain 100% untouched.

### 3. Structured Candidate Emission
- Update `final_report_generation` handling in ODR adapter and worker finalization:
  - Generate candidate artifact with payload containing `content`, `candidate_type`, `proposed_memory_type`, `evidence_refs`, `source_refs`, `provenance_version="v2"`, and `promotion_status="pending_review"`.
  - Report remains persisted in `research_reports`.
  - Zero auto-promotion to `KnowledgeMemory` or Neo4j.

### 4. Synchronous Event Bridge (`app/workers/tasks.py` & `app/services/chat/events.py`)
- Standardize event constants in `app/schemas/chat.py` / `app/services/chat/events.py`:
  - `turn.research_started`, `turn.research_planning`, `turn.researching`, `turn.synthesizing`, `turn.promotion_available`, `turn.completed`, `turn.partial`, `turn.cancelled`, `turn.failed`.
- In worker `run_research_agent_job`: Whenever research status changes or engine emits milestones, call `ChatEventRepository.append_event` to persist to PostgreSQL and publish to `turn_events:{turn_id}`.

### 5. Unified Cancellation (`app/api/routes/chat.py` & `app/services/chat/service.py`)
- Implement `POST /workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}/cancel`.
- If mode is `research`: Lookup attached `ResearchRun`, trigger engine cancellation, transition `ResearchRun` to `cancelled`, update `ConversationTurn.status = 'cancelled'`, and emit `turn.cancelled`.
- If mode is `ground`: Cancel in-flight background task or streaming generator, update turn status, and emit `turn.cancelled`.

### 6. Production Checkpointer Guard (`app/services/working_memory.py` & startup)
- Implement `validate_checkpointer(env: str)`:
  - When `settings.NEOSIS_ENV == "production"`, initialize `AsyncPostgresSaver`; if connection fails, raise `RuntimeError("Production checkpointer requirement violated")`.
  - In `development`/`test`, allow `MemorySaver`.
- Wire into `lifespan` in `app/main.py` and `on_startup` in `app/workers/settings.py`.

### 7. Legacy Route Delegation (`app/api/routes/workspaces.py` & `app/api/routes/research.py`)
- `POST /workspaces/{workspace_id}/research`: Delegates to `ChatService.submit_turn(mode="research")`.
- `POST /workspaces/{workspace_id}/ask`: Delegates to `ChatService.submit_turn(mode="ground")`.
- Add headers `Deprecation: true` and `Link: </api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns>; rel="successor-version"`.
- Remove dead `enqueue_research_job()` in `app/api/routes/research.py`.

---

## Testing Decisions

- **Seams Tested**:
  1. `ChatService.submit_turn` & `stream_turn` (Canonical Product Seam)
  2. `OpenNotebookGroundEngine` (Ground Engine Boundary)
  3. `OpenDeepResearchEngine.astream_events` (Research Engine Boundary)
  4. Worker `run_research_agent_job` (Background Execution Seam)
  5. API Routes: `/turns`, `/turns/{turn_id}/events`, `/turns/{turn_id}/cancel`, `/rollback`
- **End-to-End Test Suite**:
  - `tests/e2e/test_ground_research_ground.py`: Ground turn -> Research turn -> Ground turn sequence verifying strict Ground context isolation after research.
  - `tests/e2e/test_research_promotion.py`: Research run -> candidate in `pending_review` -> acceptance -> materialization -> subsequent research turn consumption.
  - `tests/e2e/test_unified_turn_stream.py`: Real-time SSE streaming and event replay for both modes.
  - `tests/e2e/test_cancellation_and_fence.py`: Turn cancellation and timeline epoch fence integration.

---

## Out of Scope

- Redesigning ODR internal supervisor, researcher nodes, or research graphs.
- Implementing STORM or alternate research engines.
- Modifying Open Notebook internal server implementations.
- Frontend/UI implementations (deferred to Chapter 5).
- Reopening Phase 1, Phase 2, or Phase 3 database schemas or ADRs.

---

## Further Notes

All Phase 4 tickets must follow vertical slicing and `/unlazy` gate tracking, ensuring every gate is backed by executable tests before declaring completion.
