# Specification: Chapter 4 Phase 2 — Memory, Working State & Context Isolation

## Problem Statement

In the existing architecture, the boundary between grounded factual retrieval (Ground Mode) and generative multi-source exploration (Research Mode) is vulnerable to cross-contamination. Historically, Ground mode execution automatically created `KnowledgeMemory` records and triggered Neo4j knowledge graph synchronization on every successful response. Furthermore, as users switch back and forth between Ground and Research modes within a single conversation, there is no formal policy boundary preventing research-derived inferences, unverified hypotheses, intermediate agent thoughts, or external web findings from leaking into the Ground engine's prompt context. 

From the researcher's perspective, Ground mode must remain strictly factual and grounded solely in uploaded canonical source papers. Conversely, Research mode needs full awareness of conversation history, active hypotheses, pinned evidence, and accepted knowledge, but its intermediate thoughts must remain in an interactive working state (Scratchpad) rather than being silently promoted to durable knowledge or canonical ground evidence.

## Solution

Implement the Phase 2 Memory, Working State & Context Isolation layer with an uncompromising invariant:
> **"Ground is source-grounded. Research is state-aware. Research-derived knowledge must never become Ground evidence."**

1. **Context Policy Boundary (`app/services/memory/policy.py`)**: A centralized, deterministic policy enforcement layer that explicitly defines what each mode can read and write. Ground mode is denied access to all `KnowledgeMemory`, `ResearchEvidence`, `ResearchReport`, `OutputGraph`, and `ScratchpadEntry` data.
2. **Ground Context Isolation**: Ground turns execute through a dedicated context builder that filters conversation history to include prior Ground turns only, completely stripping Research turns and unverified claims.
3. **Durable Scratchpad (`app/models/scratchpad.py`)**: A first-class PostgreSQL model for interactive working state (`note`, `observation`, `hypothesis`, `investigation`, `finding`) with full lifecycle tracking (`active`, `promoted`, `dismissed`, `superseded`), conversation-scoping by default, and workspace-level pinning.
4. **Deterministic Token Budget & Eviction Hierarchy**: Research context assembly deterministically measures token usage and evicts lowest-priority items first (Output KG → older evidence → distant turns → older scratchpad → accepted knowledge), while preserving the current prompt and working memory at all costs. An immutable, auditable `context_version` bundle is snapshotted into `ConversationTurn` at submission time.
5. **Durable Checkpointer Fail-Fast Contract**: Production deployments strictly mandate `AsyncPostgresSaver` with startup validation, eliminating silent fallback to in-memory `MemorySaver`.
6. **Live Working State Updates**: Research workers emit structured scratchpad entries live to PostgreSQL and Redis Pub/Sub, keeping the user updated in real time without exposing raw model chain-of-thought.

## User Stories

1. As a researcher, I want my Ground mode queries to cite exclusively from my uploaded source papers, so that I can be 100% confident every citation represents verified source text.
2. As a researcher, I want to alternate between Ground and Research modes in the same conversation thread, so that I can seamlessly brainstorm and verify facts without juggling multiple chat windows.
3. As a researcher, I want any findings discovered during Research mode to be excluded from Ground mode's context when I switch back, so that unverified web claims never masquerade as source-grounded evidence.
4. As a researcher, I want Ground mode answers to be saved only as conversational turns and evidence references, so that conversational responses do not clutter my workspace knowledge memory or pollute the knowledge graph.
5. As a researcher, I want Research mode to have access to recent conversation context and my active working hypotheses, so that the research agent understands the thread of our investigation.
6. As a researcher, I want to create, inspect, update, and dismiss scratchpad notes and hypotheses, so that I maintain active control over the working state of my investigation.
7. As a researcher, I want to pin critical scratchpad entries to the workspace, so that key hypotheses discovered in one conversation thread are accessible across all research conversations in the workspace.
8. As a researcher, I want to see research hypotheses and observations appear live during a research run, so that I can observe the agent's reasoning progress in real time.
9. As a researcher, I want intermediate research thoughts to remain in the Scratchpad until I explicitly review and promote them, so that unverified model outputs never become permanent workspace knowledge.
10. As a platform administrator, I want production instances to fail fast if PostgreSQL checkpointer storage is misconfigured, so that research state is never silently lost due to fallback to an ephemeral in-memory saver.
11. As an API client, I want legacy research endpoints (`POST /workspaces/{id}/research`) to create canonical conversation turns automatically, so that all research runs have a consistent conversational identity.
12. As an auditor, I want each research turn to record an immutable `context_version` snapshot of all included and evicted context, so that I can inspect the exact prompt conditions of any past research run.

## Implementation Decisions

### Phase 1 Pre-requisite Seams
* **Legacy Research Turn Creation**: `app/api/routes/research.py` `POST /workspaces/{workspace_id}/research` delegates to `ChatService.submit_turn(mode="research")`. If `conversation_id` is supplied in the request body, it appends to it; if omitted, it automatically creates a dedicated canonical `Conversation` titled `f"Research: {objective[:40]}..."`.
* **TurnCreate Schema Extension**: Add optional fields `selected_source_ids: Optional[List[UUID]] = None` (aliasing `source_scope`) and `research_options: Optional[Dict[str, Any]] = None` to `app/schemas/chat.py`.

### Memory Policy & Context Isolation
* **Policy Architecture**: Create `app/services/memory/policy.py` defining `GroundContextPolicy` and `ResearchContextPolicy`. Ground categorically rejects `KnowledgeMemory`, `ResearchEvidence`, `ResearchReport`, `OutputGraph`, `ScratchpadEntry`, and unpromoted candidates.
* **Ground Context Assembly**: Create `app/services/chat/context.py` implementing `build_ground_context()`. Multi-turn conversation context passed to Open Notebook includes only prior turns with `mode == "ground"`. All research turns are completely stripped.
* **Ground Persistence Correction**: Ensure `ChatService._execute_ground_turn()` and legacy `/ask` and `/chat` routes persist answers exclusively to `ConversationTurn.assistant_message`, `ground_evidence_refs`, and `ChatEvent`. Zero calls to `KnowledgeMemoryCreate` and zero jobs enqueued to `sync_knowledge_to_graph_job`.

### Scratchpad Working State
* **SQL Model (`app/models/scratchpad.py`)**: `ScratchpadEntry` mapped to table `scratchpad_entries`.
  * Fields: `entry_id` (UUID PK), `workspace_id` (UUID FK), `conversation_id` (UUID FK, nullable), `turn_id` (UUID FK, nullable), `run_id` (UUID FK, nullable), `entry_type` (`note`, `observation`, `hypothesis`, `investigation`, `finding`), `lifecycle` (`active`, `promoted`, `dismissed`, `superseded`), `content` (Text), `is_pinned_to_workspace` (Boolean, default False), `pinned_at` (DateTime), `superseded_by_id` (UUID self-FK, nullable), `metadata_` (JSONB), `created_at`, `updated_at`.
  * Indexes on `(workspace_id, lifecycle)`, `(conversation_id, lifecycle)`, and `(workspace_id, is_pinned_to_workspace)`.
* **Repository (`app/repositories/scratchpad.py`)**: Provides transactional CRUD, lifecycle transitions (`dismiss`, `supersede`, `promote`), and filtering for active entries scoped to `conversation_id` plus workspace-pinned entries.
* **REST Endpoints (`app/api/routes/scratchpad.py`)**:
  * `POST /workspaces/{workspace_id}/conversations/{conversation_id}/scratchpad`
  * `GET /workspaces/{workspace_id}/conversations/{conversation_id}/scratchpad`
  * `PATCH /workspaces/{workspace_id}/scratchpad/{entry_id}` (update content, toggle pin, dismiss)

### Research Context & Deterministic Eviction
* **Context Assembly**: `build_research_context()` in `app/services/chat/context.py` aggregates:
  1. Current message
  2. Working memory (pinned evidence & active hypotheses)
  3. Scratchpad entries (active in conversation + workspace pins)
  4. Recent conversation turns (both Ground and Research)
  5. Accepted `KnowledgeMemory`
  6. Prior `ResearchEvidence`
  7. Accepted `OutputGraph` context
* **Eviction Hierarchy**: When token budget (default 8,000 tokens) is exceeded, deterministic reverse-priority eviction drops:
  1. `OutputGraph` context *(Dropped first)*
  2. Older `ResearchEvidence` records
  3. Distant conversation turns
  4. Older `ScratchpadEntry` notes/observations
  5. Accepted `KnowledgeMemory`
  6. Current message & Working Memory *(Preserved at all costs)*
* **Audit Snapshot**: The resulting manifest (`budget`, `estimated_tokens`, `included_items`, `evicted_items`, `eviction_reasons`) is saved to `ConversationTurn.context_version` synchronously during `submit_turn()`.

### Durable Checkpointer & Environment Safety
* **Environment Guard**: Add `ENVIRONMENT: str = "development"` in `app/core/config.py`.
* **Async Checkpointer Factory**: Provide `get_checkpointer()` in `app/services/working_memory.py`.
  * If `ENVIRONMENT == "production"`: `ASYNC_POSTGRES_SAVER_ENABLED` is required. If connection fails during startup validation, raise a fatal `RuntimeError` immediately.
  * If `ENVIRONMENT in ("development", "test")`: Gracefully fallback to `MemorySaver()` when Postgres is unreachable.
* **Startup Validation**: Wire startup check in `app/main.py` and `app/workers/settings.py`.

### Live Structured Working State Streaming
* **Worker Updates**: In `app/workers/tasks.py` (`run_research_agent_job`), when the agent formulates a structured hypothesis, observation, or finding, persist it to `ScratchpadRepository` immediately and emit a `ChatEvent(event_type="scratchpad_entry")` to Redis.
* **Safety Constraint**: Strictly structured observations, hypotheses, and findings are permitted. Raw chain-of-thought or unconstrained intermediate model output must never be streamed or persisted to the scratchpad.

## Testing Decisions

* **External Behavior Testing**: Tests focus on observable API responses, context inspection, and database state, never private helper methods.
* **Critical Ground Isolation Test (`tests/integration/chat/test_ground_isolation.py`)**: Populate database with distinctive research facts (`DISTINCTIVE_RESEARCH_FACT`) and output graph facts (`DISTINCTIVE_GRAPH_FACT`). Execute a Ground turn. Assert with 100% precision that neither distinctive fact appears anywhere in the Ground context or payload passed to the Ground engine.
* **Critical Ground Persistence Test**: Verify that executing Ground turns never increments the count of `KnowledgeMemory` and never enqueues `sync_knowledge_to_graph_job`.
* **Research Context & Eviction Test (`tests/integration/chat/test_research_context.py`)**: Populate items exceeding 8,000 tokens. Execute `build_research_context()`. Verify deterministic eviction drops Output KG and evidence first, while strictly preserving current message and working memory. Verify `context_version` snapshot on the turn.
* **Scratchpad Lifecycle & API Test (`tests/integration/memory/test_scratchpad.py`)**: Verify create, list, pin to workspace, dismiss, and supersede across conversations.
* **Policy Unit Tests (`tests/integration/memory/test_policy.py`)**: Test every disallowed entity type against `is_allowed_for_ground()` and assert `False`.

## Out of Scope

* **Candidate Promotion & Graph Materialization**: Explicit human review, candidate acceptance/rejection, claim derivation verification, and Neo4j Output KG projection belong to Chapter 4 Phase 3.
* **Frontend UI**: User interface components, toggles, and scratchpad sidebars belong to Chapter 5.
* **Alternative Research Engines**: Redesigning ODR, implementing STORM, or introducing alternative RAG pipelines is prohibited.

## Further Notes

* All database migrations must follow standard Alembic naming conventions with reversible `upgrade()` and `downgrade()` methods.
* Knowledge graph artifacts must be refreshed using `graphify update .` upon completion of code modifications.
