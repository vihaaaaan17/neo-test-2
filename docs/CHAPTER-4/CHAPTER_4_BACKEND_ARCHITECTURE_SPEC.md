# Chapter 4 — Unified Conversational Backend, Memory, State, Provenance and Research Workspace

**Document type:** Principal/Senior Engineering Architecture Specification  
**Status:** Proposed implementation specification  
**Date:** 2026-09-24  
**Repository:** `vihaaaaan17/neo-test-2`  
**Repository baseline:** `main` at commit `061519f9067874cf69fed9a32a1e4dac2a6fa10b`  
**Chapter 3 completion baseline:** commit `38e13284150faf4f3644c124323a1b2ff5ed78c6`  
**Primary backend goal:** make Ground and Research operate as one canonical conversational backend without weakening Ground's source-grounding guarantees.

---

## 1. Executive Summary

Chapter 3 established the research execution fabric: canonical `ResearchRun`, task/evidence/artifact/report/usage/event models, the `ResearchEngine` boundary, Open Deep Research integration, retriever normalization, admission and rate limiting, lifecycle enforcement, durable research events, and supporting Open Notebook integration. Chapter 4 must not restart that work.

Chapter 4 is the integration and product-backend layer above that machinery. Its job is to turn the existing components into one continuous research workspace in which the user can move between Ground and Research through one conversation, while preserving a strict information boundary:

> Ground is source-grounded. Research is memory/state-aware. Derived Research knowledge is never silently promoted into the Ground evidence corpus.

The backend therefore becomes a shared state machine with two asymmetric context policies.

Ground receives the user's current query plus the Ground conversation/session context and the canonical source set represented by Open Notebook. Ground does not receive `KnowledgeMemory`, Research KG nodes, research reports, research evidence, hypotheses, episodic research memory, or derived claims as evidence. A Research result may influence what the user asks next, but it does not become a Ground source merely because it exists in the workspace.

Research receives the current user turn plus the broader research context: working memory, scratchpad/hypotheses, accepted knowledge, prior research evidence, source-linked Ground findings, previous research runs, and the Research Output KG. This is the deliberate asymmetry that creates continuity without corrupting Ground.

A second core rule is that durable research knowledge is not automatically promoted. Research engines may generate `memory_candidate`, `graph_candidate`, `claim_candidate`, `hypothesis_candidate`, or related artifacts. These remain pending until the user explicitly accepts or rejects promotion. Rejection is terminal and auditable. Acceptance materializes the candidate into the appropriate canonical backend. This turns the memory layer into a human-controlled knowledge boundary rather than an LLM-controlled write path.

Chapter 4 therefore owns the full backend necessary for:

- one canonical Conversation/Turn model spanning Ground and Research;
- durable turn state and mode transitions;
- Research Working Memory and Scratchpad as first-class backend state;
- strict Ground context isolation;
- Research context assembly;
- candidate review and explicit accept/reject promotion;
- claims, derivations, calculations, verification and provenance bundles;
- curated Research Output KG projection;
- Git-style workspace versioning of durable approved research state;
- backend streaming and resumable event delivery;
- integration repairs around the already-built Open Notebook and ODR adapters;
- complete backend verification and migration to the canonical APIs.

Chapter 5 owns the frontend/UI presentation of these backend capabilities.

---

## 2. Current Repository Baseline

The current repository already contains the major Chapter 3 building blocks.

### 2.1 Existing Chapter 3 components to retain

The following are existing production-direction components and are not to be redesigned:

| Existing component | Current location | Chapter 4 treatment |
|---|---|---|
| Open Notebook Ground engine facade | `app/integrations/open_notebook/ground_engine.py` | Integrate through a canonical chat service; keep the engine boundary intact |
| Open Notebook HTTP client | `app/integrations/open_notebook/client.py` | Extend only where canonical turn/session metadata is required |
| Open Notebook source/workspace bindings | `app/models/open_notebook_binding.py` | Preserve; generalize conversation binding to the canonical Conversation model |
| Research engine factory | `app/integrations/research_engine/factory.py` | Reuse as-is; remove only dead/duplicate access paths |
| ODR adapter | `app/integrations/research_engine/open_deep_research/engine.py` | Keep ODR graph intact; repair adapter integration points only |
| ODR upstream graph | `app/integrations/research_engine/upstream/open_deep_research/` | Do not redesign |
| GPT Researcher capability | `app/integrations/research_engine/tools/gpt_researcher_tool.py` | Keep as existing capability provider |
| Normalized retrievers | `app/services/research/retrievers/` | Do not create another retriever abstraction |
| Research Repository | `app/repositories/research.py` | Extend for Chapter 4 lifecycle/domain operations |
| Research lifecycle | `app/services/research/lifecycle.py` | Reuse as execution state authority |
| Research admission/rate limiting | `app/services/research/admission.py`, `quota.py`, `rate_limiter.py` | Reuse; only integrate with the canonical chat submission path |
| Research provenance service | `app/services/research/provenance.py` | Extend for claim/candidate provenance |
| Research Event persistence | `ResearchEvent` in `app/models/research.py` | Preserve as execution-level event ledger |
| Output Graph repository | `app/repositories/graph.py` | Preserve as projection layer; enforce acceptance gate before user-visible projection |
| Memory Router | `app/services/memory_router.py` | Evolve into policy-aware memory/context boundary |
| Workspace commits | `app/models/workspace.py`, `app/repositories/workspace.py` | Extend from KnowledgeMemory snapshotting to a true durable workspace manifest |
| Background worker infrastructure | `app/workers/tasks.py`, `app/workers/settings.py` | Reuse existing queues/isolation; repair task integration only |

### 2.2 Important seams verified in the current codebase

The following are specifically Chapter 4 integration seams, not a request to reopen Chapter 3 architecture:

1. `app/api/routes/workspaces.py` currently stores every successful Ground answer as a `KnowledgeMemory` with `source_mode="ground"` and enqueues graph synchronization. This conflicts with the Chapter 4 Ground isolation rule. Ground turns must instead be stored as conversation turns with evidence references; they must not automatically become durable KnowledgeMemory records.

2. `ResearchService.promote_memory_candidates()` currently promotes every `memory_candidate` it finds, and `promote_graph_candidates()` immediately projects every `graph_candidate`. Chapter 4 changes this from automatic promotion to candidate materialization plus explicit user review.

3. `OpenDeepResearchEngine` currently contains a `MemorySaver` fallback around the existing Postgres checkpointer configuration. Chapter 4 must repair the integration contract so production execution cannot silently lose durable state. Development-only in-process behavior remains permitted for tests/local development where explicitly selected.

4. `app/api/routes/research.py` still contains a placeholder `enqueue_research_job()` path, while `app/api/routes/workspaces.py` uses the real ARQ job directly. Chapter 4 establishes one canonical research submission service and removes the split backend entry points.

5. The repository currently has `GroundConversation` and a Ground-specific Open Notebook conversation binding, but no canonical Conversation/Turn abstraction spanning both modes. Chapter 4 introduces that canonical abstraction.

6. Working memory has a LangGraph state schema and reducer behavior, but `app/services/working_memory.py` is effectively a passthrough graph. Chapter 4 turns Working Memory and Scratchpad into real backend state with a durable canonical representation and uses LangGraph checkpointing as execution state rather than as the only product-state store.

7. Workspace commits currently snapshot active KnowledgeMemory IDs. Chapter 4 extends the commit manifest so rollback represents a coherent research workspace state without deleting historical ResearchRun/Evidence/Conversation data.

These changes are integration and product-backend work built on top of Chapter 3, not a new ODR/retriever/worker architecture.

---

## 3. Non-Negotiable Architectural Principles

### 3.1 Ground is source-grounded, not memory-grounded

Ground evidence is defined by the canonical source set for the workspace, projected into Open Notebook for Ground execution.

Ground must never use any of the following as evidence or retrieval documents:

- `KnowledgeMemory` created by Research;
- Research Reports;
- Research Evidence;
- Research Output KG nodes/edges;
- derived calculations;
- hypotheses;
- episodic research memory;
- research scratchpad content;
- unverified candidate artifacts.

A user message such as "compare those new findings with my uploaded paper" is valid. The words "those new findings" are part of the user query. Ground still grounds its answer in the uploaded paper rather than treating the research finding as evidence.

The Ground backend may retain its own Open Notebook session continuity and canonical conversation metadata. It must not turn those conversations into the shared durable knowledge corpus automatically.

### 3.2 Research is state-aware

Research can consume:

- current user turn;
- bounded conversation history;
- source-linked Ground findings;
- prior Research Evidence;
- accepted KnowledgeMemory;
- Working Memory;
- Scratchpad entries;
- active hypotheses;
- accepted Research Output KG nodes/edges;
- prior reports and run state;
- current workspace commit/version context.

The inclusion order is policy-controlled and token-budgeted.

### 3.3 Knowledge is not automatically trusted

Research output first becomes a candidate artifact. Only user acceptance creates durable KnowledgeMemory or user-visible Output KG state.

A model cannot directly write durable KnowledgeMemory merely by producing a report.

### 3.4 Postgres is canonical

Postgres is the canonical source of truth for product state, conversation turns, research runs, evidence, artifacts, promotion decisions, working state, durable memory, and workspace versions.

Redis remains infrastructure for queues, distributed rate limiting, cache/live pub-sub, and transient acceleration. It is never the sole durable record.

Neo4j is a projection for graph traversal/presentation. It is not canonical research state.

Open Notebook is the Ground execution/retrieval engine. It is not the canonical Neosis workspace database.

### 3.5 Preserve execution identity boundaries

The following identities stay distinct:

- `Conversation`: user-visible chat container;
- `Turn`: one user request and its assistant execution/result;
- `ResearchRun`: one Research execution;
- `ResearchTask`: one execution unit within a run;
- `ResearchEvidence`: retrieved evidence;
- `ResearchArtifact`: durable intermediate/candidate output;
- `KnowledgeMemory`: user-approved durable knowledge;
- `WorkspaceCommit`: immutable workspace version manifest.

A `ResearchRun` must never be collapsed into the conversation model.

### 3.6 Chapter 4 is backend-complete

Chapter 4 must leave the backend capable of supporting the final user experience. Chapter 5 should be able to implement the UI without adding another core backend architecture.

---

## 4. Target Logical Architecture

```text
                                  +----------------------+
                                  |      FastAPI API      |
                                  +----------+-----------+
                                             |
                                    Canonical Chat API
                                             |
                                  +----------v-----------+
                                  |  Conversation/Turn   |
                                  |       Service        |
                                  +----+-------------+---+
                                       |             |
                         mode=ground   |             | mode=research
                                       |             |
                         +-------------v--+       +--v----------------+
                         | Ground Context  |       | Research Context  |
                         |    Policy       |       |      Policy       |
                         +--------+--------+       +--------+----------+
                                  |                         |
                                  | source-only            | state/memory aware
                                  v                         v
                         +--------+--------+       +--------+----------+
                         | Open Notebook  |       | ResearchAdmission |
                         | Ground Engine  |       | + existing ODR    |
                         +--------+--------+       +--------+----------+
                                  |                         |
                              Ground turn               ResearchRun
                                  |                         |
                                  |                         v
                                  |                existing ODR/retrievers
                                  |                         |
                                  |                 Evidence / Report /
                                  |                 Candidate Artifacts
                                  |                         |
                                  +-----------+-------------+
                                              |
                                        Shared Backend
                                              |
                    +-------------------------+-------------------------+
                    |                         |                         |
            Working Memory              Promotion                  Workspace
            Scratchpad/Hypotheses       Review Gate                 Versioning
                    |                         |                         |
                    v                         v                         v
             Postgres state             KnowledgeMemory           WorkspaceCommit
                                         Output KG projection
                    |                         |
                    +-----------+-------------+
                                |
                           Research Context
                                |
                                +---- never Ground evidence
```

The critical architectural property is the one-way information boundary:

```text
Ground sources  ---> Ground execution
       |                  |
       |                  +----> grounded conversation turn
       |                                 |
       +--------------------------------> Research context allowed

Research memory / KG / derived knowledge -X-> Ground evidence
```

---

## 5. Domain Model

### 5.1 Conversation

Introduce a canonical `Conversation` model as the product container.

Suggested fields:

```text
conversation_id UUID PK
workspace_id UUID FK
owner_id UUID
created_at timestamptz
updated_at timestamptz
status string              active | archived
last_turn_sequence bigint
metadata JSONB
```

Indexes:

- `(workspace_id, updated_at desc)`;
- `(workspace_id, owner_id)`;
- unique/guarded `conversation_id` ownership boundary.

A conversation is mode-agnostic. The mode belongs to each turn.

### 5.2 ConversationTurn

Create a canonical turn record.

Suggested fields:

```text
turn_id UUID PK
conversation_id UUID FK
workspace_id UUID FK
owner_id UUID
sequence bigint
mode string                ground | research
user_message text
assistant_message text nullable
status string              pending | running | completed | partial | failed | cancelled
research_run_id UUID nullable FK
client_request_id string nullable
ground_evidence_refs JSONB
context_version JSONB
error_code string nullable
created_at timestamptz
started_at timestamptz nullable
completed_at timestamptz nullable
```

Constraints:

- unique `(conversation_id, sequence)`;
- unique `(conversation_id, client_request_id)` when client request ID is supplied;
- `workspace_id` must match the conversation and research run;
- no turn can reference a ResearchRun outside its workspace.

The turn is the canonical product bridge between Ground and Research.

### 5.3 ResearchRun additions

Extend the existing `ResearchRun` with:

```text
conversation_id UUID nullable FK
turn_id UUID nullable FK
base_commit_id UUID nullable FK
parent_run_id UUID nullable FK
context_version JSONB nullable
```

These fields allow Research to explain exactly which conversational turn and workspace version initiated the run.

### 5.4 ResearchArtifact promotion state

Do not create a second candidate store. Extend `ResearchArtifact`.

Suggested additional fields:

```text
promotion_status string
    pending_review | accepted | rejected | superseded
reviewed_by UUID nullable
reviewed_at timestamptz nullable
review_reason text nullable
promoted_target_type string nullable
promoted_target_id UUID nullable
```

The artifact `payload` remains the typed domain payload, validated by Pydantic models before materialization.

This gives an auditable state machine without duplicating candidate data.

### 5.5 ScratchpadEntry

Create a first-class durable research workspace item.

Suggested fields:

```text
entry_id UUID PK
workspace_id UUID FK
conversation_id UUID nullable FK
turn_id UUID nullable FK
run_id UUID nullable FK
owner_id UUID
entry_type string
    note | observation | hypothesis | investigation | finding
status string
    active | promoted | dismissed | superseded
content text
provenance JSONB
pinned boolean
author_type string
    user | system | research_engine
created_at timestamptz
updated_at timestamptz
```

The lifecycle is intentionally explicit:

```text
NOTE
  -> OBSERVATION
  -> HYPOTHESIS
  -> INVESTIGATION
  -> VERIFIED_FINDING
  -> KNOWLEDGE
```

The backend should not require every item to progress through every state.

### 5.6 Working memory

Working memory has two representations:

1. canonical product state in Postgres (`ScratchpadEntry`, active hypotheses, pins, selected evidence);
2. execution checkpoint state in LangGraph using the existing checkpointer mechanism.

LangGraph state is therefore an execution view of canonical state, not the only system of record.

### 5.7 KnowledgeMemory

`KnowledgeMemory` remains the durable research memory entity, but Chapter 4 changes its write boundary.

A `KnowledgeMemory` record is normally created only after a user has accepted a `memory_candidate`.

The `status` should reflect lifecycle, for example:

```text
candidate -> active -> superseded / archived
```

The provenance payload must include enough information to reconstruct the chain back to:

- ResearchRun;
- ResearchArtifact;
- ResearchEvidence;
- canonical Source/SourceSnapshot where resolvable;
- calculation/verification details where applicable.

### 5.8 Output KG

The Research Output KG remains a curated user-visible semantic projection. It is not the Internal KG.

The graph should project only accepted graph candidates or explicitly approved graph updates.

Its nodes continue to use the existing `OutputGraphNode` / `OutputGraphEdge` representation, with deep provenance attached to claims/derived values.

---

## 6. Context and Memory Policy

### 6.1 GroundContextPolicy

Ground context must be deliberately tiny and source-scoped.

Allowed:

- current user message;
- explicit source scope selected by the user/backend;
- current Open Notebook notebook/session binding;
- Ground conversation continuity maintained by Open Notebook;
- canonical source metadata necessary for validation.

Not allowed:

- `KnowledgeMemory` content;
- Research Evidence content;
- Research Reports;
- Research Output KG nodes/edges;
- research scratchpad text;
- active research hypotheses;
- episodic research memory;
- unapproved candidates;
- derived calculations as evidence.

### 6.2 ResearchContextPolicy

Research context is assembled by `ResearchContextAssembler` under a token budget.

Priority order:

1. current user message;
2. active working memory;
3. user-approved pinned evidence;
4. active hypotheses/investigations;
5. recent source-grounded Ground findings and evidence refs;
6. accepted KnowledgeMemory;
7. recent Research Evidence summaries;
8. accepted Output KG context;
9. episodic memory;
10. older conversation history.

The assembler should return metadata describing what was included and what was evicted. This is important for observability and debugging.

### 6.3 The asymmetric memory rule

The shared state fabric is directional in information flow.

```text
GROUND -> Research context: allowed when source-linked
RESEARCH -> Ground evidence: forbidden
RESEARCH -> Research context: allowed
GROUND -> Ground evidence: source corpus only
```

This is the central invariant of Chapter 4.

### 6.4 Turn-by-turn memory behavior

Ground:

- persist the user/assistant turn for conversation history;
- persist source evidence references;
- do not automatically update `KnowledgeMemory`, research Working Memory, Research KG, or durable research knowledge;
- do not enqueue `sync_knowledge_to_graph_job` for a normal Ground answer.

Research:

- update Working Memory every turn/run;
- update Scratchpad/hypotheses as explicit research state;
- persist Research Evidence and artifacts;
- optionally compress to episodic memory according to existing service policy;
- create candidates automatically;
- do not create durable `KnowledgeMemory`/Output KG from candidates until user acceptance.

---

## 7. Unified Conversation Flow

### 7.1 Ground turn

```text
POST /workspaces/{workspace_id}/conversations/{conversation_id}/turns
mode=ground
message="What is established about X?"
        |
        v
Create Turn(status=pending)
        |
        v
GroundContextAssembler
        |
        +--> current query
        +--> Open Notebook session
        +--> canonical source scope
        |
        v
OpenNotebookGroundEngine
        |
        v
Ground answer + canonical evidence refs
        |
        v
Turn(status=completed)
```

The result is a conversation turn, not a KnowledgeMemory write.

### 7.2 Research turn

```text
POST /workspaces/{workspace_id}/conversations/{conversation_id}/turns
mode=research
message="Investigate what the literature says beyond these papers."
        |
        v
Create Turn(status=pending)
        |
        v
ResearchContextAssembler
        |
        v
ResearchAdmissionController
        |
        v
Existing ResearchEngineFactory -> ODR
        |
        v
ResearchRun / Tasks / Evidence / Events / Artifacts
        |
        v
Candidate artifacts -> pending_review
        |
        v
Turn(status=completed|partial)
```

### 7.3 Back to Ground

```text
User switches mode
        |
        v
GROUND
"Compare those new findings with my uploaded paper."
        |
        v
GroundContextAssembler
        |
        +--> user query
        +--> uploaded source corpus
        +--> current Ground ON session
        |
        X--> research memory / KG / report text as evidence
        |
        v
Open Notebook
        |
        v
Source-grounded comparison
```

The Research result can be mentioned by the user and can influence the wording of the query. The backend must not turn it into Ground evidence automatically.

---

## 8. Promotion and Review Architecture

### 8.1 Candidate generation

Research execution produces structured candidate artifacts. Examples:

```text
memory_candidate
claim_candidate
graph_candidate
hypothesis_candidate
finding_candidate
```

Each candidate payload must contain:

- stable artifact identity;
- human-readable content;
- candidate type;
- evidence references;
- source references where resolvable;
- provenance;
- confidence where available;
- derivation/calculation metadata where applicable;
- proposed target representation.

### 8.2 User review state machine

```text
                    +----------------+
                    | pending_review |
                    +-------+--------+
                            |
                 +----------+----------+
                 |                     |
               accept                reject
                 |                     |
                 v                     v
            +---------+          +-----------+
            | accepted|          |  rejected |
            +----+----+          +-----------+
                 |
         materialize target
                 |
     +-----------+------------+
     |                        |
KnowledgeMemory          OutputGraph
```

A rejected candidate remains stored for audit but has no durable knowledge side effect.

### 8.3 Acceptance semantics

Acceptance is idempotent.

Calling accept twice must not create two KnowledgeMemory records or duplicate graph state.

Acceptance must be transactional from the perspective of the canonical DB record:

1. verify workspace/owner access;
2. verify candidate is pending review;
3. materialize target;
4. persist target identity;
5. mark candidate accepted;
6. enqueue projection only after the canonical commit is safe.

### 8.4 Rejection semantics

Rejection:

- records reviewer identity and time;
- optionally records reason;
- sets `promotion_status=rejected`;
- never deletes research evidence;
- never creates durable knowledge;
- never writes to Output KG.

### 8.5 Candidate API

Suggested endpoints:

```text
GET  /workspaces/{workspace_id}/promotions
GET  /workspaces/{workspace_id}/promotions/{artifact_id}
POST /workspaces/{workspace_id}/promotions/{artifact_id}/accept
POST /workspaces/{workspace_id}/promotions/{artifact_id}/reject
```

The route layer should delegate to `PromotionService`, not directly modify SQLAlchemy models.

---

## 9. Provenance, Claims, Derivation and Verification

### 9.1 Provenance must be reconstructable

A user-visible derived claim must answer:

- What sources/evidence produced it?
- Which ResearchRun produced it?
- Which artifact/candidate produced it?
- Was it a direct finding, a calculation, or a synthesis?
- Was the calculation verified?
- Who approved the promotion?
- Which workspace version contains it?

### 9.2 Typed provenance references

The current UUID-only provenance bundle is useful but too ambiguous for the full backend. Chapter 4 should extend it to a typed reference structure.

Suggested shape:

```python
class ProvenanceRef(BaseModel):
    ref_type: Literal[
        "source",
        "source_snapshot",
        "block",
        "research_evidence",
        "research_artifact",
        "knowledge_memory",
        "conversation_turn"
    ]
    ref_id: UUID
    locator: str | None = None
```

`ProvenanceBundle` then contains:

```text
derived_from: list[ProvenanceRef]
calculation: optional string
verification_status: optional enum/string
verification_details: optional JSON
```

The previous `derived_from_refs` representation may be retained for backward compatibility during migration.

### 9.3 Deterministic verification boundary

LLMs may propose a calculation. They must not be the sole verifier of a calculation.

`app/services/research/verification.py` should provide deterministic/specialized verification for supported calculation forms.

Example:

```text
claim: 18.3%
calculation: (1.42 / 1.20 - 1) * 100
validator result: verified
```

The UI-facing Output KG can then display:

```text
DERIVED RESULT
Derived from: Paper A p.12; Table 3; Equation 4
Calculation: (1.42 / 1.20 - 1) × 100 = 18.3%
Status: Mathematically verified; Source grounded
```

The graph itself is not the verifier. It stores the verification result and provenance.

---

## 10. Workspace Versioning

The current `WorkspaceCommit` model is a useful base but snapshots only active KnowledgeMemory IDs. Chapter 4 expands it into an immutable workspace manifest.

Suggested commit manifest:

```json
{
  "knowledge_memory_ids": [],
  "accepted_artifact_ids": [],
  "output_graph_version": "...",
  "active_hypothesis_ids": [],
  "scratchpad_checkpoint": "...",
  "conversation_checkpoint": "...",
  "base_research_run_ids": [],
  "schema_version": 1
}
```

The commit should also capture the active conversation/turn context needed to reproduce the logical workspace state.

### 10.1 Rollback semantics

Rollback changes the active workspace pointers to a previous immutable manifest.

Rollback must not:

- delete ResearchRun;
- delete ResearchEvidence;
- delete conversation history;
- delete rejected candidates;
- delete historical reports;
- rewrite the past.

Rollback is a state selection operation, not destructive deletion.

### 10.2 Research branching

A new ResearchRun records `base_commit_id`. This makes it possible to reproduce which approved knowledge and graph state existed when the run started.

This is the backend foundation for later “go back to base” behavior.

---

## 11. Event and Streaming Architecture

There are two event layers:

1. `ResearchEvent` — execution-level research event ledger already established in Chapter 3.
2. `ChatEvent` — canonical conversation/turn event stream introduced in Chapter 4.

### 11.1 ChatEvent

Suggested fields:

```text
chat_event_id UUID PK
conversation_id UUID FK
turn_id UUID FK
sequence bigint
event_type string
payload JSONB
created_at timestamptz
```

Event examples:

```text
turn.created
ground.search_started
ground.answer_started
ground.answer_completed
research.started
research.plan_ready
research.evidence_added
research.synthesis_started
research.candidate_available
turn.completed
turn.partial
turn.failed
turn.cancelled
```

### 11.2 Live delivery

Redis pub/sub remains the live transport. Postgres remains the durable replay source.

The stream endpoint should:

1. read the last persisted cursor;
2. subscribe to live Redis events;
3. replay any durable events after the cursor to close the race window;
4. continue consuming live events;
5. terminate when the turn reaches a terminal state.

This makes the UI resilient to reconnects without turning Redis into canonical state.

### 11.3 Existing ResearchEvent integration

The Chapter 3 ResearchEvent path remains intact. Chapter 4 maps relevant ResearchEvent transitions into ChatEvent transitions so the user sees one coherent turn stream.

No ODR event architecture change is required.

---

## 12. Backend API Surface

### 12.1 Conversations

```text
POST /api/v1/workspaces/{workspace_id}/conversations
GET  /api/v1/workspaces/{workspace_id}/conversations
GET  /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}
```

### 12.2 Turns

```text
POST /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns
GET  /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns
GET  /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}
POST /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}/cancel
```

### 12.3 Streaming

```text
GET /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}/events
```

The stream accepts an optional cursor/sequence.

### 12.4 Promotion/review

```text
GET  /api/v1/workspaces/{workspace_id}/promotions
GET  /api/v1/workspaces/{workspace_id}/promotions/{artifact_id}
POST /api/v1/workspaces/{workspace_id}/promotions/{artifact_id}/accept
POST /api/v1/workspaces/{workspace_id}/promotions/{artifact_id}/reject
```

### 12.5 Scratchpad / Working Memory

Backend support for the future UI should include:

```text
GET    /api/v1/workspaces/{workspace_id}/scratchpad
POST   /api/v1/workspaces/{workspace_id}/scratchpad
PATCH  /api/v1/workspaces/{workspace_id}/scratchpad/{entry_id}
DELETE /api/v1/workspaces/{workspace_id}/scratchpad/{entry_id}
POST   /api/v1/workspaces/{workspace_id}/scratchpad/{entry_id}/promote
```

The UI is Chapter 5; these APIs are Chapter 4.

### 12.6 Workspace versions

Keep the existing endpoints but extend their semantics and response shape:

```text
POST /workspaces/{workspace_id}/commits
POST /workspaces/{workspace_id}/rollback
GET  /workspaces/{workspace_id}/commits
GET  /workspaces/{workspace_id}/commits/{commit_id}
```

---

## 13. File / Folder / Function-Level Design

### 13.1 New files

#### `app/models/chat.py` or consolidated `app/models/conversation.py`

Functions/methods represented primarily by service/repository operations:

- `Conversation` model
- `ConversationTurn` model
- optional `ChatEvent` model if not placed in `models/research.py`

#### `app/models/scratchpad.py`

- `ScratchpadEntry`

#### `app/schemas/chat.py`

- `ConversationCreate`
- `ConversationResponse`
- `TurnCreate`
- `TurnResponse`
- `TurnExecutionStatus`
- `ChatEventResponse`

#### `app/schemas/promotion.py`

- `PromotionCandidateResponse`
- `PromotionDecisionRequest`
- `PromotionDecisionResponse`

#### `app/schemas/scratchpad.py`

- `ScratchpadCreate`
- `ScratchpadUpdate`
- `ScratchpadResponse`

#### `app/repositories/conversation.py`

Suggested functions:

- `create_conversation()`
- `get_conversation()`
- `list_conversations()`
- `append_turn()`
- `get_turn()`
- `list_turns()`
- `allocate_turn_sequence()`
- `set_turn_status()`
- `set_turn_result()`
- `attach_research_run()`
- `get_turn_context_window()`

#### `app/repositories/scratchpad.py`

- `create_entry()`
- `get_entry()`
- `list_entries()`
- `update_entry()`
- `set_entry_status()`
- `pin_entry()`
- `dismiss_entry()`

#### `app/repositories/chat_events.py`

- `append_event()`
- `list_events_after()`
- `get_latest_sequence()`

#### `app/services/chat/service.py`

- `create_conversation()`
- `submit_turn()`
- `_submit_ground_turn()`
- `_submit_research_turn()`
- `_finalize_turn()`
- `_fail_turn()`
- `_enforce_turn_idempotency()`

#### `app/services/chat/context.py`

- `build_ground_context()`
- `build_research_context()`
- `get_recent_turn_window()`
- `resolve_source_scope()`
- `serialize_ground_context()`
- `serialize_research_context()`

#### `app/services/chat/events.py`

- `emit_turn_event()`
- `persist_and_publish()`
- `replay_events()`
- `publish_live_event()`

#### `app/services/memory/context.py`

- `build_context()`
- `filter_by_policy()`
- `apply_budget()`
- `record_evictions()`

#### `app/services/memory/policy.py`

- `GroundContextPolicy`
- `ResearchContextPolicy`
- `is_allowed_for_ground()`
- `is_allowed_for_research()`

#### `app/services/research/promotion.py`

- `list_candidates()`
- `get_candidate()`
- `accept_candidate()`
- `reject_candidate()`
- `materialize_memory_candidate()`
- `materialize_graph_candidate()`
- `mark_superseded()`

#### `app/services/research/derivation.py`

- `build_provenance_bundle()`
- `normalize_derivation()`
- `validate_claim_sources()`
- `attach_evidence_refs()`

#### `app/services/research/verification.py`

- `verify_calculation()`
- `verify_claim()`
- `build_verification_result()`

#### `app/services/working_memory.py`

Replace the current passthrough-only integration with:

- `load_working_memory()`
- `apply_working_delta()`
- `add_scratchpad_entry()`
- `add_hypothesis()`
- `pin_evidence()`
- `remove_pin()`
- `snapshot_execution_state()`
- `restore_execution_state()`

The LangGraph graph remains, but product-state operations are explicit.

### 13.2 Existing files to modify

#### `app/api/routes/workspaces.py`

Modify/remove the direct Ground-memory write path from `ask_ground_mode()`.

Compatibility endpoints may remain temporarily, but they must delegate to the canonical services.

New canonical route handlers should not contain business logic.

#### `app/api/routes/research.py`

Remove the placeholder `enqueue_research_job()` path and route requests through the same research submission service used by unified turns.

#### `app/integrations/open_notebook/ground_engine.py`

Extend `run()` to receive canonical conversation/turn context and return normalized evidence/provenance data. It must not receive MemoryRouter context.

#### `app/integrations/open_notebook/client.py`

Only add the minimum session/event helpers required to associate Open Notebook execution with the canonical turn.

#### `app/integrations/research_engine/open_deep_research/engine.py`

Keep the ODR graph untouched. Change only the adapter envelope:

- accept ResearchContext;
- emit normalized canonical events;
- create structured candidate artifacts with provenance;
- stop assuming candidates are immediately promoted;
- ensure production checkpoint behavior is explicit and durable.

#### `app/services/research/service.py`

Refactor automatic promotion into candidate materialization and delegate acceptance/rejection to `PromotionService`.

#### `app/repositories/research.py`

Add:

- candidate listing by status;
- atomic decision update;
- candidate-to-target linkage;
- idempotent promotion support;
- retrieval of candidate provenance/evidence.

#### `app/models/research.py`

Extend `ResearchRun` and `ResearchArtifact` for Chapter 4 fields.

#### `app/models/workspace.py`

Extend `WorkspaceCommit` to carry the durable workspace manifest/version references.

#### `app/repositories/workspace.py`

Add:

- `build_commit_manifest()`
- `restore_commit_manifest()`
- `list_commits()`
- `get_active_manifest()`

#### `app/repositories/graph.py`

Keep projection APIs. Add explicit accepted-version/graph metadata where required. Do not add graph retrieval to Ground context.

#### `app/schemas/graph.py`

Extend provenance models and define candidate/output validation models.

#### `app/schemas/knowledge.py`

Extend provenance/origin fields while retaining backward compatibility for existing rows.

#### `app/services/memory_router.py`

Separate:

- memory write routing;
- context retrieval/assembly;
- mode policies.

The router must not become a giant orchestration class.

#### `app/workers/tasks.py`

Change the research finalization path from:

```text
run completed -> automatically promote memory + graph
```

to:

```text
run completed -> persist candidates -> mark candidates pending review -> emit promotion.available
```

The worker remains an execution worker, not a user-decision service.

### 13.3 Compatibility/deprecation files

`app/models/conversation.py` currently contains `GroundConversation`. Keep it only until the conversation migration is complete.

`app/orchestration/ground_mode.py` and `app/orchestration/research_mode.py` remain deprecated compatibility code unless another backend path still depends on them. They must not become the canonical Chapter 4 entry point.

`streamlit_app.py` is Chapter 5/UI scope and should not drive Chapter 4 backend architecture.

---

## 14. Database and Indexing Strategy

Chapter 4 additions should use normal domain migrations. This is not a repeat of Chapter 3 schema-hardening work.

Required migration themes:

1. canonical `conversations` table;
2. `conversation_turns` table;
3. `chat_events` table;
4. Scratchpad table;
5. promotion/review fields on `research_artifacts`;
6. ResearchRun conversation/turn/base-commit fields;
7. workspace commit manifest fields;
8. typed provenance compatibility fields if required;
9. Open Notebook binding migration to canonical conversations.

Important indexes:

- conversations by workspace and updated time;
- turns by conversation and sequence;
- turns by research run;
- chat events by turn and sequence;
- candidates by workspace/promotion status;
- scratchpad by workspace/status and run;
- research runs by conversation/turn;
- research evidence by run/fingerprint;
- workspace commits by workspace/created time.

Avoid indexing large text columns directly unless the existing search stack requires it.

Do not create a second vector database or graph-as-canonical store.

---

## 15. Scalability and Concurrency

### 15.1 Stateless API layer

FastAPI instances must be stateless. All conversation/memory/run state required to reconstruct a request must be in Postgres or explicitly provided execution state.

### 15.2 Turn idempotency

Every frontend/client turn should be allowed to supply `client_request_id`.

Duplicate requests must return the existing turn rather than create a second ResearchRun.

### 15.3 Conversation sequencing

Turn sequence allocation must be concurrency safe. Use a transaction and row lock or another database-native atomic mechanism. Do not rely on application-process counters.

### 15.4 Context bounding

Never load an unbounded conversation or research history into an LLM call.

Use:

- recent-turn window;
- semantic retrieval where already available;
- explicit token budget;
- deterministic eviction policy;
- context provenance metadata.

### 15.5 Research concurrency

Reuse Chapter 3 admission and Redis rate limiting. Chapter 4 must call these services before scheduling a Research turn.

No new research worker pool architecture is introduced.

### 15.6 Projection isolation

Graph projection should remain asynchronous where possible. The canonical DB write for a user decision must not wait for Neo4j to complete before acknowledging the state transition if the target itself is already canonical in Postgres.

### 15.7 Reconnect/replay

Chat streams must recover from a dropped connection by replaying persisted events after a cursor.

### 15.8 Bounded load verification

Chapter 4 should include concurrency correctness and bounded stress verification. A 1000-user load test is explicitly outside this chapter.

---

## 16. Security and Multi-Tenant Isolation

Every service and repository method must enforce `workspace_id` and, where applicable, `owner_id`.

Promotion endpoints are security-sensitive because they create durable state. They must re-check candidate ownership at decision time rather than trusting IDs sent by the client.

Ground source scope must be resolved entirely within the current workspace.

No ResearchRun, ResearchEvidence, KnowledgeMemory, Output KG node, ScratchpadEntry, or ConversationTurn may be referenced across workspaces.

Do not allow a user to accept a candidate from another workspace by guessing an artifact UUID.

Prompt-injection defenses established around Research retrieval remain intact. Chapter 4 adds no shortcut that bypasses them.

---

## 17. Observability

Every turn must carry:

- `request_id`;
- `workspace_id`;
- `conversation_id`;
- `turn_id`;
- `mode`;
- `run_id` if Research;
- engine/revision if Research;
- context version/budget metadata.

Every promotion decision must log:

- candidate ID;
- decision;
- actor;
- source run;
- promoted target;
- latency;
- error if any.

Useful metrics:

```text
chat.turn.count
chat.turn.latency
chat.turn.failure_count
chat.context.tokens
chat.context.evictions
research.turn.started
research.turn.completed
research.turn.partial
promotion.pending_count
promotion.accepted_count
promotion.rejected_count
ground.context.policy_violations
research.context.build_latency
output_graph.projection_latency
```

A `ground.context.policy_violations` metric should be impossible to increment in healthy production behavior; it exists as a guardrail/alert.

---

## 18. Testing Strategy

### 18.1 Ground isolation tests

Mandatory test:

1. create a workspace;
2. create accepted Research KnowledgeMemory containing distinctive text;
3. create Research Output KG nodes containing another distinctive text;
4. invoke Ground;
5. assert neither value was passed to Open Notebook context;
6. assert response evidence references only canonical uploaded sources.

### 18.2 No automatic Ground promotion test

Update the existing Ground API tests so a successful Ground answer:

- creates a conversation turn;
- records evidence refs;
- does not create KnowledgeMemory automatically;
- does not call `sync_knowledge_to_graph_job`.

### 18.3 Candidate review tests

For each candidate type:

- pending candidate is visible;
- accept creates exactly one target;
- second accept is idempotent;
- reject creates no target;
- rejected candidate cannot silently re-promote;
- unauthorized user cannot accept.

### 18.4 Memory flow tests

Research turn:

```text
turn -> working memory -> artifact -> pending review
```

After accept:

```text
artifact -> KnowledgeMemory -> optional internal KG sync
```

### 18.5 Output KG tests

Graph candidate should remain absent from user-visible Output KG until accepted.

Provenance round-trip tests should preserve:

- source refs;
- evidence refs;
- calculations;
- verification status.

### 18.6 Versioning tests

Verify:

- commit captures approved knowledge/output state;
- rollback changes active pointers;
- historical runs/evidence remain intact;
- new ResearchRun records base commit.

### 18.7 Unified chat tests

Test sequences:

```text
Ground -> Research -> Ground
Research -> Research -> Ground
Ground -> Ground
Research -> Ground -> Research
```

The central invariant is that only Research receives Research memory context.

### 18.8 Streaming/replay tests

Simulate a disconnect after sequence N and reconnect at sequence N. Verify no events are lost or duplicated.

### 18.9 Integration tests with existing Chapter 3 components

Use real adapter boundaries and mocked external providers where appropriate.

Do not replace ODR/Open Notebook with new fake architecture merely to make tests easier.

---

## 19. Migration and Compatibility Plan

### 19.1 Existing GroundConversation rows

Create canonical Conversation rows from existing `GroundConversation` records. Preserve IDs when possible or maintain a deterministic mapping table.

Existing Open Notebook conversation bindings must be remapped to the canonical conversation ID.

### 19.2 Existing Ground KnowledgeMemory records

Historical Ground-generated KnowledgeMemory rows may already exist because the current Ground route writes them. Chapter 4 must not delete history blindly.

Recommended handling:

- mark them as legacy/derived-ground records;
- exclude them from Ground evidence retrieval permanently;
- exclude them from Research durable knowledge until explicitly reviewed if their semantics are ambiguous;
- preserve provenance for audit.

### 19.3 Existing Research candidates

Any candidates already written by Chapter 3 but auto-promoted should remain as history. New Chapter 4 execution uses the new pending-review gate.

### 19.4 Existing workspace commits

Old commits continue to work using `active_knowledge_ids`. New commits use the expanded manifest. The rollback service should understand both versions during migration.

---

## 20. Explicit Non-Goals

The following are deliberately not Chapter 4 redesign work:

- no ODR redesign;
- no new Research supervisor;
- no STORM implementation;
- no new retriever architecture;
- no Open Notebook rewrite;
- no Redis/worker architecture redesign;
- no repeat of Chapter 3 Postgres hardening;
- no new Research engine;
- no large-scale 1000-user load test;
- no frontend/UI implementation;
- no replacement of existing ODR upstream graph;
- no second canonical database;
- no graph database as source of truth.

Chapter 4 may modify integration code in those areas only when required to make the Chapter 4 contract work correctly.

---

## 21. Chapter 4 Definition of Done

Chapter 4 is complete when all of the following are true:

### Product/backend model

- One canonical Conversation model exists.
- Ground and Research are turn modes, not separate chat products.
- ResearchRun remains a distinct execution entity.
- ConversationTurn links a ResearchRun when appropriate.

### Ground integrity

- Ground is source-grounded.
- Research memory and Output KG are never injected into Ground evidence.
- Ground answers are not automatically written to KnowledgeMemory.
- Ground does not automatically synchronize answer text to the graph.

### Research continuity

- Research receives bounded memory/state context across turns.
- Working Memory and Scratchpad are durable backend concepts.
- Research can consume source-linked Ground findings without making Ground consume Research findings.

### Promotion governance

- Candidate artifacts are pending by default.
- User can accept or reject each candidate.
- Decisions are auditable and idempotent.
- Accepted memory becomes KnowledgeMemory.
- Accepted graph candidates become Output KG projections.
- Rejected candidates produce no durable knowledge side effects.

### Provenance

- Derived claims reference evidence/source/artifact chains.
- Calculations can be verified deterministically where supported.
- Output KG provenance survives storage/retrieval.

### Versioning

- Workspace commits represent durable approved research state.
- ResearchRun records base commit context.
- Rollback does not destroy history.

### Integration

- Existing Open Notebook and ODR adapters remain the execution engines.
- Research submission uses one canonical backend path.
- Existing worker/lifecycle/admission infrastructure remains authoritative.
- Auto-promotion in the worker is removed.
- Placeholder research enqueue paths are removed or retired.
- Production checkpointer behavior is explicit and durable.

### Streaming

- Unified turn events are persisted and streamable.
- Reconnect/replay works from a durable event cursor.

### Testing

- Ground isolation tests pass.
- Promotion accept/reject tests pass.
- Ground -> Research -> Ground integration passes.
- Research -> Ground isolation passes.
- Versioning and rollback tests pass.
- Streaming replay tests pass.
- Existing Chapter 3 regression suite remains green.

### Frontend readiness

Chapter 5 can build the UI with only presentation-level work because Chapter 4 already exposes:

- conversations;
- turns;
- mode;
- streaming;
- research status;
- candidates/promotions;
- scratchpad state;
- workspace versions;
- output graph/provenance APIs.

---

## 22. Architecture Outcome

The finished Chapter 4 backend should behave as one system, not as two systems glued together:

```text
                   NEOSIS WORKSPACE
                         |
                 +-------+-------+
                 |   Conversation |
                 +-------+-------+
                         |
                +--------+--------+
                |                 |
             GROUND            RESEARCH
                |                 |
       Open Notebook         Existing ODR
                |                 |
       source-grounded       external evidence
                |                 |
          Turn + refs       evidence + artifacts
                |                 |
                +--------+--------+
                         |
                 Shared State Fabric
                         |
       +-----------------+------------------+
       |                 |                  |
 Working Memory      Promotion         Versioning
 Scratchpad          Accept/Reject     Workspace Commit
       |                 |                  |
       |           +-----+-----+            |
       |           |           |            |
       |       Knowledge   Output KG        |
       |        Memory        |             |
       +-----------+-----------+-------------+
                   |
             Research context
                   |
             NEVER Ground evidence
```

The system is continuous at the conversation/state level, but intentionally asymmetric at the evidence level. That asymmetry is the core correctness property of the architecture.

