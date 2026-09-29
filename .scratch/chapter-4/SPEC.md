# Chapter 4 & 4.5 Specification — Unified Conversational Backend, Memory, State, Verification & Human-Controlled Promotion

**Status:** ready-for-agent  
**Date:** 2026-09-24  
**Target:** Backend Architecture (Chapter 4 & Chapter 4.5)  
**Baseline Commit:** `061519f9067874cf69fed9a32a1e4dac2a6fa10b`  

---

## Problem Statement

Researchers investigating complex domains currently experience an unnatural cognitive split caused by disjointed backend architectures:
1. **Disconnected Modalities:** Ground Mode (citation-grounded document QA) and Research Mode (autonomous web exploration) exist behind split endpoints (`/ask-ground-mode`, `/chat-ground-mode`, `/research`, `/runs`). The user cannot ask a grounded question about uploaded papers and subsequently command the system to research an unexplored gap within the same conversational context.
2. **Memory Contamination:** In the previous architecture, Ground Mode answers were automatically recorded as `KnowledgeMemory` and pushed to the Neo4j Knowledge Graph, diluting the distinction between source truth and synthesized assistant prose.
3. **Unchecked Hallucinations & Auto-Promotion:** In Research Mode, autonomous agent runs automatically promoted findings directly into `KnowledgeMemory` and Neo4j without human verification, allowing unchecked agent hallucinations, unverified arithmetic, and contradictory claims to become permanent truth.
4. **Lack of Semantic Verification:** Citations were only verified for referential integrity (checking whether an evidence UUID exists), with no automated validation of whether the cited text semantically entails or supports the claim.
5. **Vulnerable Workspace Rollbacks:** Rolling back a workspace to an earlier commit could not guarantee state isolation; in-flight background worker jobs could complete seconds after a rollback and commit stale promotions into the restored timeline.

---

## Solution

A unified conversational backend that treats Ground and Research as two operational modes of a single conversation, bounded by strict asymmetric information policies and human-controlled promotion:
1. **Canonical Conversation & Turn Fabric:** A unified `Conversation` and `ConversationTurn` abstraction in PostgreSQL. Users interact via a single endpoint `POST /workspaces/{id}/conversations/{id}/turns`. Transport differs internally (inline SSE for Ground; ARQ job with Redis Pub/Sub SSE bridge for Research), but the turn lifecycle is identical and durable in PostgreSQL.
2. **Strict Asymmetric Memory Invariant:** Ground is source-grounded in uploaded documents via Open Notebook; it never receives research-derived memory. Research is state-aware; it receives bounded conversation history, accepted knowledge, scratchpad items, and active hypotheses via a token-budgeted `ResearchContextAssembler`.
3. **Transparent Upstream Resilience:** If Open Notebook loses its transient in-memory chat session (409 Conflict), Neosis transparently re-provisions an upstream session from canonical source state and idempotently re-executes the Ground turn.
4. **Interactive Scratchpad:** A first-class durable `ScratchpadEntry` entity with foreign keys, lifecycle states (`note` → `observation` → `hypothesis` → `investigation` → `finding`), and explicit `superseded_by` lineage.
5. **Quality, Critic & Verification Pipeline:** Inline post-synthesis pipeline executing referential verification (Layer A), source resolution (Layer B), semantic support classification (Layer C), bounded deterministic AST mathematical derivation (Layer D), cross-evidence contradiction detection (Layer E), and a structured Research Critic pass.
6. **Human-Controlled Promotion Inbox:** Research outputs materialize as `PromotionCandidate` records in `pending_review`. Durable promotion to `KnowledgeMemory` or Neo4j Output KG requires explicit user approval (supporting both individual item review and predicate-based bulk approval). Rejection is permanent and auditable.
7. **Atomic Rollback Fencing:** Workspace rollbacks increment a PostgreSQL `timeline_epoch`. Background workers enforce an atomic commit fence (`WHERE timeline_epoch = expected_epoch`), immediately aborting mutations if the workspace was rolled back during execution.

---

## User Stories

### Conversational Lifecycle & Turn Management
1. As a researcher, I want to create a named conversation within my workspace, so that I can organize distinct investigation threads.
2. As a researcher, I want to list and retrieve previous conversations in my workspace, so that I can revisit prior investigation contexts.
3. As a researcher, I want to submit a query specifying `mode: "ground"`, so that my answer is derived strictly from my uploaded workspace documents with zero hallucinations.
4. As a researcher, I want to submit a query specifying `mode: "research"`, so that the system autonomously browses the web, academic databases, and tools to answer broad exploratory questions.
5. As a researcher, I want to switch between Ground Mode and Research Mode in consecutive turns within the same conversation, so that I can seamlessly explore new ideas and verify them against my documents.
6. As a frontend client, I want to submit a turn with `stream=true`, so that I receive immediate Server-Sent Events (SSE) containing tokens, status transitions, and citations.
7. As a frontend client, I want to submit a turn without streaming, so that I receive an immediate `202 Accepted` response with a `turn_id` for pollable background execution.
8. As a researcher, I want long-running research turns to continue running durably in the background if my browser disconnects, so that I do not lose progress on complex investigations.
9. As a researcher, I want to inspect the complete turn history of a conversation with ordered sequence numbers and execution statuses, so that I have a reliable chronological record of my session.
10. As a researcher, I want duplicate requests with the same `client_request_id` to return the existing turn idempotently, so that network retries do not spawn duplicate agent runs.

### Ground Mode Isolation & Upstream Recovery
11. As a researcher, I want Ground Mode to ignore research-derived memories, reports, and knowledge graph nodes, so that speculative web findings never contaminate citation-grounded answers.
12. As a researcher, I want Ground Mode answers to link directly to canonical source document IDs and paragraph locators, so that every claim is verifiable in my original documents.
13. As a researcher, I want Ground Mode to continue working seamlessly if the underlying Open Notebook microservice restarts, so that container crashes do not terminate my conversation.
14. As a system administrator, I want Ground Mode session recovery to re-initialize exclusively from canonical Neosis sources, so that upstream failures never inject external data.
15. As a researcher, I want Ground Mode answers to be stored as conversation turns rather than automatically written into durable `KnowledgeMemory`, so that casual chat does not clutter my verified knowledge base.

### Research Context Assembly & Working Memory
16. As a researcher, I want Research Mode to be aware of my recent Ground Mode findings, so that external research builds directly upon facts already established in my documents.
17. As a researcher, I want Research Mode to respect a strict token budget for context injection, so that model calls do not exceed context windows or inflate inference costs.
18. As a researcher, I want the system to deterministically evict lower-priority context (such as older chat history) when the token budget is reached, so that critical working memory and hypotheses are always preserved.
19. As a system operator, I want context assembly to emit telemetry detailing included and evicted item IDs, so that context construction is fully observable and debuggable.
20. As a researcher, I want context assembly to be a read-time construction layer that never silently mutates or summarizes durable memory, so that my stored data remains unchanged until I explicitly modify it.
21. As a researcher, I want to create and pin scratchpad notes and hypotheses in my workspace, so that I can steer ongoing research with my own domain expertise.
22. As an autonomous research agent, I want to record intermediate observations and investigation leads in the scratchpad, so that multi-turn research preserves working state across runs.
23. As a researcher, I want scratchpad items to maintain explicit `superseded_by` lineage, so that I can trace how initial observations evolved into verified findings.

### Quality, Verification & Critique
24. As a researcher, I want every claim in a synthesized research report to be validated for referential citation integrity, so that phantom citations are caught immediately.
25. As a researcher, I want external web citations to resolve to canonical workspace sources where a match exists, so that external evidence links to my local library.
26. As a researcher, I want an automated semantic support verifier to classify whether cited evidence actually entails, partially supports, or contradicts each claim, so that I know the true strength of each finding.
27. As a researcher, I want mathematical and statistical derivations (e.g., percentages, growth rates, ratios) to be verified by a deterministic engine rather than an LLM, so that calculations are mathematically guaranteed.
28. As a system operator, I want the mathematical derivation engine to enforce strict resource limits on expression length, AST depth, and numbers of operations, so that malicious expressions cannot exhaust CPU resources.
29. As a researcher, I want contradictory evidence across distinct papers to be explicitly surfaced as contradiction records, so that I am alerted to conflicting scientific viewpoints.
30. As a researcher, I want synthesized findings to pass through an adversarial Research Critic pass, so that unsupported generalizations and weak evidence chains are highlighted before I review them.
31. As a researcher, I want the research engine to persist raw reports and artifacts before running verification, so that completed research is never lost if a verifier experiences a transient timeout.
32. As a researcher, I want verification or critic timeouts to gracefully tag candidates as `unverified` rather than failing the entire research run, so that I can still review the research output.

### Human-Controlled Review, Promotion & Projection
33. As a researcher, I want research findings, memory candidates, and graph updates to appear in a review inbox with status `pending_review`, so that no AI-generated claim enters my permanent knowledge base without my approval.
34. As a researcher, I want to inspect a candidate's complete evidence chain, semantic verification status, contradiction flags, and mathematical derivations, so that I can make an informed promotion decision.
35. As a researcher, I want to explicitly accept an individual candidate, so that it is materialized into permanent `KnowledgeMemory`.
36. As a researcher, I want to explicitly reject an individual candidate with an optional reason, so that unverified or irrelevant claims are permanently excluded.
37. As a researcher, I want rejected candidates to remain historically visible in the audit log, so that there is an immutable record of what was considered and discarded.
38. As a researcher, I want to execute bulk candidate approvals based on strict verification criteria (e.g., verified with no blocking contradictions), so that I can quickly promote high-confidence batches without reviewing every trivial claim.
39. As a researcher, I want candidate acceptance to immediately update status in PostgreSQL while dispatching heavy Neo4j graph projections to background workers, so that review actions are instant.
40. As a researcher, I want graph projection jobs to be idempotent, so that retrying a projection never creates duplicate nodes or edges in the Knowledge Graph.
41. As a researcher, I want promoted `KnowledgeMemory` to retain complete provenance linking back to the originating `ResearchRun`, `ResearchEvidence`, and candidate ID, so that every permanent fact remains auditable.

### Workspace Versioning & Rollback Fencing
42. As a researcher, I want to create workspace commits that snapshot the complete approved manifest (approved knowledge, active sources, approved scratchpad notes, approved graph state), so that I can version my research progress.
43. As a researcher, I want to roll back my workspace to an earlier commit, so that I can revert unwanted changes or explore alternative hypotheses.
44. As a researcher, I want workspace rollbacks to automatically cancel in-flight turns and research runs, so that aborted investigations do not continue consuming compute resources.
45. As a researcher, I want rollback to mark all unreviewed candidates created after the target commit as `superseded`, so that orphaned candidates from discarded timelines do not clutter my inbox.
46. As a system architect, I want rollback to atomically increment a database `timeline_epoch`, so that background workers from pre-rollback runs are strictly blocked from committing promotions into the restored workspace.
47. As a researcher, I want historical research runs, raw evidence, and reports to remain intact after a rollback, so that my research history is never destroyed.

---

## Implementation Decisions

### 1. Unified Conversation & Turn Architecture
- **Model Separation:** A `Conversation` represents the user session container (`conversation_id`, `workspace_id`, `owner_id`, `status`, `last_turn_sequence`). A `ConversationTurn` represents a single interaction (`turn_id`, `conversation_id`, `workspace_id`, `sequence`, `mode`, `user_message`, `assistant_message`, `status`, `research_run_id`, `client_request_id`, `ground_evidence_refs`, `context_version`).
- **Turn State Machine:**
  ```text
  pending -> running -> completed
                     -> partial (budget exhaustion / cancellation)
                     -> failed (unhandled error)
                     -> cancelled (user or rollback cancellation)
  ```
- **Execution Dispatching in `ChatService`:**
  - `mode == "ground"`: Queries `OpenNotebookGroundEngine` within the request thread (or streams SSE inline). On success, updates `ConversationTurn(status="completed", assistant_message=..., ground_evidence_refs=...)`.
  - `mode == "research"`: Admits run via `ResearchAdmissionController`, creates canonical `ResearchRun` linked to `turn_id`, enqueues `run_research_agent_job` in ARQ queue `research-standard`, sets `ConversationTurn(status="running", research_run_id=...)`, and bridges events over SSE or returns HTTP 202.

### 2. Context Isolation & Assembly Policies
- **Ground Context Policy:** Deliberately source-only. Open Notebook is passed: query, current Open Notebook session binding, and active canonical workspace sources. Forbidden: `KnowledgeMemory`, Research Evidence, Scratchpad, Hypotheses, Output KG.
- **Research Context Assembler:** Gathers context using a 10-tier priority hierarchy with deterministic reverse-priority eviction:
  1. Current user turn message
  2. Active working memory state
  3. User-approved pinned evidence
  4. Active hypotheses & investigations
  5. Recent source-grounded Ground findings
  6. Accepted `KnowledgeMemory`
  7. Recent Research Evidence summaries
  8. Accepted Output KG entities & relations
  9. Episodic memory summaries
  10. Older conversation history
- **Assembly Invariant:** The assembler is read-only. It never writes to, summarizes, or mutates durable memory. It emits structured telemetry (`included_item_ids`, `evicted_item_ids`, `budget`, `estimated_tokens`, `final_tokens`, `eviction_reason`).

### 3. Open Notebook Session Recovery (409 Conflict)
- When `OpenNotebookClient` receives HTTP 404 from SurrealDB (mapped to `409 session_state_lost`), `ChatService` catches the exception.
- It transparently executes `open_notebook_client.create_chat_session()`, updates `OpenNotebookConversationBinding`, and retries the turn once.
- The rehydration payload contains only the canonical Ground source corpus.

### 4. Interactive Working Memory & Scratchpad
- Dedicated PostgreSQL table `scratchpad_entries`:
  - `entry_id` (UUID PK), `workspace_id`, `conversation_id`, `turn_id`, `run_id`, `owner_id`
  - `entry_type`: `note`, `observation`, `hypothesis`, `investigation`, `finding`
  - `status`: `active`, `promoted`, `dismissed`, `superseded`
  - `content` (text), `provenance` (JSONB), `pinned` (boolean), `author_type` (`user` | `agent`)
  - `superseded_by` (UUID nullable self-referential FK)
- Distinguishes interactive working state (`ScratchpadEntry`) from immutable execution output (`ResearchArtifact`).

### 5. Research Quality, Critic & Verification Pipeline
- **Execution Order in Worker (`tasks.py`):**
  ```text
  ODR LangGraph Run
    ↓
  Persist Raw Report & Artifacts (PostgreSQL)
    ↓
  Layer A: Referential Verification (citation UUIDs -> ResearchEvidence)
    ↓
  Layer B: Source Resolution (external URLs -> canonical Source/Snapshot)
    ↓
  Layer C: Semantic Support Verifier (claim + evidence -> entailment classification)
    ↓
  Layer D: Deterministic Math Engine (AST arithmetic verification)
    ↓
  Layer E: Cross-Evidence Contradiction Detection
    ↓
  Research Critic Pass (adversarial critique of unsupported generalizations)
    ↓
  Materialize Promotion Candidates (status="pending_review")
    ↓
  ResearchRun(status="completed")
  ```
- **Deterministic Math Engine:**
  - Custom AST visitor parsing expressions via Python's `ast.parse`.
  - Whitelist: Numeric literals, Binary operations (`+`, `-`, `*`, `/`, `**`, `%`), Unary operations (`+`, `-`), safe built-ins (`round`, `abs`, `min`, `max`, `sum`, `pct_change`).
  - Strict resource limits: Max 500 characters, max AST depth 10, max exponent 10,000, max 50 operations.
  - Emits: `{inputs, expression, computed_value, expected_value, tolerance, verified}`.
- **Graceful Verifier Degradation:** If an LLM verifier fails or times out, deterministic results are preserved, candidates are marked `verification_status="unverified"`, and the run transitions to `completed`.

### 6. Human Review & Promotion Seams
- **Candidate Data Model:** Implemented via `PromotionCandidate` linked to `ResearchArtifact`:
  - `promotion_status`: `pending_review`, `under_review`, `accepted`, `rejected`, `superseded`
  - `verification_status`: `verified`, `unverified`, `failed`
  - `verification_report`: JSONB (semantic scores, derivation details, contradiction flags, critic notes)
  - `reviewed_by`, `reviewed_at`, `review_reason`
- **Promotion Seams:**
  - Individual: `POST /workspaces/{id}/candidates/{id}/review` (`decision: "accept" | "reject"`).
  - Bulk: `POST /workspaces/{id}/candidates/bulk-review` with explicit candidate IDs or predicate (`status=pending_review AND verification_status=verified AND no_blocking_contradictions`).
  - Fast transactional status update in PostgreSQL enqueues ARQ job `materialize_promoted_candidate_job` for background `KnowledgeMemory` creation and Neo4j Output KG projection.

### 7. Atomic Rollback Fencing
- Add `timeline_epoch` (integer default 1) to `workspaces` table.
- When `rollback_workspace()` executes:
  ```sql
  UPDATE workspaces 
  SET timeline_epoch = timeline_epoch + 1, active_commit_id = :target_commit_id 
  WHERE workspace_id = :workspace_id;
  ```
- Any background worker committing evidence, candidates, reports, or promotions executes within a fenced transaction:
  ```sql
  UPDATE ... WHERE workspace_id = :workspace_id AND :worker_epoch = (SELECT timeline_epoch FROM workspaces WHERE workspace_id = :workspace_id);
  ```
- If the epoch has advanced, the worker rolls back mutations, emits an abort event, and exits safely.
- Unreviewed candidates created after the target commit are marked `superseded`. Historical runs and evidence remain untouched in the audit log.

---

## Testing Decisions

### What Makes a Good Test
- Tests must verify external system behavior and observable contracts, never internal helper methods or private state.
- Assert that inputs produce expected outputs, state transitions, and database state across HTTP endpoints and worker job boundaries.
- Mock only external network calls (Tavily search, external LLM provider APIs, upstream SurrealDB Open Notebook HTTP service). PostgreSQL and Redis should run real or transaction-isolated instances.

### Primary Testing Seams
To keep testing seams minimal, test through the highest possible interfaces:
1. **API Seam (Primary):** FastAPI TestClient invoking `POST /workspaces/{id}/conversations/{id}/turns` with streaming and non-streaming modes.
2. **Review Seam:** `POST /workspaces/{id}/candidates/{id}/review` validating transactional state transitions and ARQ enqueueing.
3. **Rollback Seam:** `POST /workspaces/{id}/rollback` testing the `timeline_epoch` fence against concurrent simulated workers.
4. **Worker Seam:** ARQ task `run_research_agent_job` validating inline verification, candidate creation, and graceful verifier degradation.
5. **Deterministic Math Engine Seam:** Unit tests validating valid arithmetic expressions and asserting that pathological expressions (large exponents, deep ASTs, disallowed built-ins) are safely rejected.

### Prior Art in Repository
- `tests/integration/test_ground_mode_api.py`: Tests Ground Mode HTTP routes, mock streaming, and SSE event decoding.
- `tests/integration/benchmark/test_failure_injection.py`: Tests worker crashes, saturation, and recovery.
- `tests/integration/benchmark/test_rollback_verification.py`: Tests engine switching and rollback assertions.

---

## Out of Scope

1. **Frontend / UI Implementation:** All React / Streamlit frontend updates are deferred to Chapter 5. Chapter 4 is strictly backend-complete.
2. **ODR Upstream Redesign:** The LangGraph graph topology in `app/integrations/research_engine/upstream/open_deep_research/` is treated as a stable upstream dependency and will not be rewritten.
3. **Stanford STORM Implementation:** Formally deferred via ADR 0002.
4. **New Retriever Frameworks:** The existing normalized retrievers (`WebRetriever`, `AcademicRetriever`, `MCPRetriever`, `GPTResearcherRetriever`) in `app/services/research/retrievers/` are reused as-is.
5. **Alternative Primary Databases:** PostgreSQL remains the sole canonical store. Neo4j remains a projection; SurrealDB remains an Open Notebook implementation detail.

---

## Further Notes

### Migration & Deprecation Path
- A single new Alembic migration will introduce:
  - `conversations` table
  - `conversation_turns` table
  - `scratchpad_entries` table
  - `promotion_candidates` table (or column extensions to `research_artifacts`)
  - `timeline_epoch` column on `workspaces`
  - Foreign key additions on `research_runs` (`conversation_id`, `turn_id`)
- Legacy endpoints (`POST /ask-ground-mode`, `POST /chat-ground-mode`, `POST /research`, `POST /runs`) will be internally refactored in Phase 4 to delegate directly to `ChatService` while maintaining backward compatibility for existing integration tests.
