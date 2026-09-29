# Chapter 4 — Backend Implementation Phase Plan

**Repository:** `vihaaaaan17/neo-test-2`  
**Baseline:** `main` / `061519f9067874cf69fed9a32a1e4dac2a6fa10b`  
**Chapter 3 completed in:** `38e13284150faf4f3644c124323a1b2ff5ed78c6`  
**Scope:** Backend only  
**Phases:** 5  
**Chapter 5:** Frontend/UI only

---

# 0. How to Read This Plan

This plan is intentionally not a Chapter 3 rewrite. The repository already contains the Chapter 3 execution machinery. Chapter 4 wraps that machinery in the canonical conversation/state/promotion layer and repairs integration seams where the existing implementation does not yet satisfy the product contract.

The execution rule is:

> Build the backend contract first, then wire existing engines into it, then verify the entire Ground <-> Research workflow.

Each phase produces a working vertical slice. Later phases build on the previous phase; no phase should create a parallel architecture that has to be deleted later.

---

# 1. Phase Overview

| Phase | Name | Primary outcome |
|---|---|---|
| Phase 1 | Canonical Conversation and Turn Fabric | One backend conversation model with Ground/Research turn identity and durable events |
| Phase 2 | Memory, Working State and Context Isolation | Research state continuity plus a hard Ground evidence boundary |
| Phase 3 | Candidate Promotion, Provenance, Derivation and Versioning | User-controlled memory/graph promotion and reproducible research state |
| Phase 4 | Unified Execution and Chapter 3 Integration | Existing Open Notebook + ODR + workers operate behind the unified backend |
| Phase 5 | Verification, Migration, Production Readiness and Chapter 5 Handoff | Complete backend, regression-safe rollout, frontend-ready contracts |

Dependency graph:

```text
Phase 1
   |
   v
Phase 2
   |
   v
Phase 3
   |
   v
Phase 4
   |
   v
Phase 5
```

Phase 3 and Phase 4 can have limited parallel implementation, but Phase 4 integration testing depends on Phase 1-3 contracts existing.

---

# 2. Global Work Rules

1. Do not redesign ODR.
2. Do not implement STORM.
3. Do not introduce a second research supervisor.
4. Do not create a second retriever architecture.
5. Do not rewrite Open Notebook.
6. Do not redesign Redis/ARQ workers.
7. Do not repeat Chapter 3 infrastructure hardening as a separate initiative.
8. Do not add another research engine.
9. Do not make Neo4j canonical.
10. Do not allow Research-derived knowledge into Ground evidence.
11. Do not auto-promote Research candidates.
12. Do not put frontend code into the core Chapter 4 work.

The coding pattern should remain:

```text
API route
   -> service
      -> repository / integration
         -> canonical DB state
```

Routes must not become orchestration scripts.

---

# 3. Phase 1 — Canonical Conversation and Turn Fabric

## Objective

Replace the current asymmetric backend entry points with a single canonical conversation/turn model that can dispatch to either Ground or Research while preserving `ResearchRun` as a separate execution identity.

## Current baseline being integrated

Existing relevant files:

- `app/models/conversation.py`
- `app/models/research.py`
- `app/models/open_notebook_binding.py`
- `app/schemas/conversation.py`
- `app/api/routes/workspaces.py`
- `app/api/routes/research.py`
- `app/workers/tasks.py`

The repository currently has `GroundConversation` and a Ground-specific `/chat` path, while Research is started through a separate background-run API. Phase 1 establishes the canonical product abstraction.

## Phase 1 workstreams

### P1.1 — Canonical conversation model

Modify/create:

- `app/models/conversation.py`
- `app/schemas/conversation.py`
- `app/repositories/conversation.py` [new]

Implement:

```text
Conversation
ConversationTurn
```

Repository functions:

```text
create_conversation()
get_conversation()
list_conversations()
append_turn()
get_turn()
list_turns()
allocate_turn_sequence()
set_turn_status()
set_turn_result()
attach_research_run()
get_recent_turns()
```

Rules:

- workspace ownership is checked in every repository read/write;
- turn sequence is transaction-safe;
- `client_request_id` provides idempotency;
- mode is stored on the turn, not on the conversation.

### P1.2 — Canonical chat schemas

Create:

`app/schemas/chat.py`

Models:

```text
ConversationCreate
ConversationResponse
TurnCreate
TurnResponse
TurnStatusResponse
ChatEventResponse
```

`TurnCreate` should contain at minimum:

```json
{
  "message": "...",
  "mode": "ground|research",
  "client_request_id": "optional-idempotency-key"
}
```

Optional future-safe fields:

```text
source_scope
selected_source_ids
research_options
```

Do not expose engine-specific configuration in the public chat contract.

### P1.3 — Canonical turn service

Create:

`app/services/chat/service.py`

Functions:

```text
create_conversation()
submit_turn()
_submit_ground_turn()
_submit_research_turn()
_finalize_turn()
_fail_turn()
```

The service owns orchestration. Routes only validate/authenticate and call it.

`submit_turn()` flow:

```text
validate workspace
   -> idempotency check
   -> allocate sequence
   -> create turn
   -> dispatch by mode
```

### P1.4 — Canonical event stream

Create:

`app/models/chat_event.py` or place `ChatEvent` next to conversation models.

Create:

`app/repositories/chat_events.py`
`app/services/chat/events.py`

Functions:

```text
append_event()
list_events_after()
get_latest_sequence()
emit_turn_event()
publish_live_event()
replay_events()
```

Redis is live transport; Postgres is replay source.

### P1.5 — Canonical API routes

Create:

`app/api/routes/chat.py`

Endpoints:

```text
POST /workspaces/{workspace_id}/conversations
GET  /workspaces/{workspace_id}/conversations
GET  /workspaces/{workspace_id}/conversations/{conversation_id}
POST /workspaces/{workspace_id}/conversations/{conversation_id}/turns
GET  /workspaces/{workspace_id}/conversations/{conversation_id}/turns
GET  /workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}
GET  /workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}/events
```

### P1.6 — Compatibility routing

Modify:

`app/api/routes/workspaces.py`
`app/api/routes/research.py`

Do not immediately delete old routes.

Instead:

- legacy Ground `/ask` delegates to Ground turn service;
- legacy Ground `/chat` delegates to canonical conversation service where feasible;
- legacy `/research` creates a canonical Research turn or canonical run request;
- remove the placeholder `enqueue_research_job()` path;
- document compatibility endpoints as deprecated.

### P1.7 — Open Notebook conversation migration

Modify:

`app/models/open_notebook_binding.py`
`app/repositories/open_notebook.py` if present

Migrate `OpenNotebookConversationBinding` so it points to canonical `Conversation` rather than only `GroundConversation`.

Keep the Open Notebook session ID unchanged.

The binding still means:

```text
Neosis Conversation -> Open Notebook execution session
```

It does not mean Open Notebook is the canonical conversation database.

## Phase 1 tests

Create:

`tests/integration/chat/test_conversation.py`
`tests/integration/chat/test_turns.py`
`tests/integration/chat/test_events.py`

Must verify:

- conversation creation;
- turn sequence ordering;
- duplicate `client_request_id` idempotency;
- workspace isolation;
- mode stored per turn;
- event sequence monotonicity;
- reconnect replay.

## Phase 1 exit criteria

A backend client can create one conversation and submit both:

```text
mode=ground
mode=research
```

without using separate product conversation models.

The Research turn may still use the existing worker/runtime internally. The user-facing identity is now unified.

---

# 4. Phase 2 — Memory, Working State and Context Isolation

## Objective

Make memory/state real and enforce the asymmetry between Ground and Research.

This phase is the most important correctness phase of Chapter 4.

## Phase 2 workstreams

### P2.1 — Memory policy layer

Create:

`app/services/memory/policy.py`
`app/services/memory/context.py`

Implement:

```text
GroundContextPolicy
ResearchContextPolicy
is_allowed_for_ground()
is_allowed_for_research()
filter_by_policy()
build_context()
apply_budget()
```

Hard rule:

```text
KnowledgeMemory -> Ground = false
ResearchEvidence -> Ground = false
ResearchReport -> Ground = false
OutputGraph -> Ground = false
ResearchScratchpad -> Ground = false
ResearchHypothesis -> Ground = false
```

### P2.2 — Ground context builder

Create:

`app/services/chat/context.py`

Implement:

```text
build_ground_context()
resolve_ground_source_scope()
```

The Ground context object must include only:

- current user query;
- source scope;
- Open Notebook conversation/session binding;
- canonical source metadata required for validation.

Do not call `MemoryRouter` to retrieve research knowledge for Ground.

### P2.3 — Research context builder

Implement:

```text
build_research_context()
get_recent_ground_turn_context()
get_working_memory_context()
get_accepted_knowledge_context()
get_research_evidence_context()
get_output_graph_context()
```

Use a deterministic token budget.

The result should include:

```text
current message
recent conversation context
source-linked Ground findings
working state
scratchpad/hypotheses
accepted knowledge
research evidence
accepted Output KG context
```

### P2.4 — Ground answer persistence correction

Modify:

`app/api/routes/workspaces.py`
`app/services/memory_router.py`
`app/integrations/open_notebook/ground_engine.py`

Remove this Chapter 3-era behavior:

```text
Ground answer
 -> KnowledgeMemory
 -> sync_knowledge_to_graph_job
```

Replace it with:

```text
Ground answer
 -> ConversationTurn.assistant_message
 -> ground_evidence_refs
 -> ChatEvent
```

This is a mandatory Chapter 4 correction.

Update the existing `tests/test_ground_mode_api.py` expectations accordingly.

### P2.5 — Working Memory canonical state

Modify:

`app/services/working_memory.py`
`app/schemas/working_memory.py`

Create:

`app/models/scratchpad.py`
`app/repositories/scratchpad.py`
`app/schemas/scratchpad.py`

Implement:

```text
load_working_memory()
apply_working_delta()
add_scratchpad_entry()
add_hypothesis()
pin_evidence()
remove_pin()
snapshot_execution_state()
```

The existing LangGraph state remains the execution-state representation.

The Postgres Scratchpad model becomes the user-visible canonical state.

### P2.6 — Durable checkpointer integration

Modify:

`app/services/working_memory.py`
`app/integrations/research_engine/open_deep_research/engine.py`
`app/core/config.py`

Use existing `AsyncPostgresSaver` integration as the production path.

Do not introduce another persistence mechanism.

The implementation must explicitly distinguish:

```text
local/dev/test -> MemorySaver permitted
production -> durable saver required
```

No silent production downgrade.

### P2.7 — Research turn state updates

Modify:

`app/services/chat/service.py`
`app/workers/tasks.py`
`app/services/episodic.py`

A Research turn should update Working Memory and Scratchpad state as the run progresses.

The system must not promote every intermediate thought to durable KnowledgeMemory.

### P2.8 — Memory Router decomposition

Modify:

`app/services/memory_router.py`

Split responsibilities conceptually:

```text
Memory write routing
Context assembly
Mode policy
Graph sync scheduling
```

Avoid creating a second memory service implementation. The goal is clear boundaries, not another framework.

## Phase 2 tests

Create:

`tests/integration/chat/test_ground_isolation.py`
`tests/integration/chat/test_research_context.py`
`tests/integration/memory/test_policy.py`
`tests/integration/memory/test_scratchpad.py`

Critical test:

```text
Research memory contains "DISTINCTIVE_RESEARCH_FACT".
Output KG contains "DISTINCTIVE_GRAPH_FACT".
Ground query asks a related question.
Assert neither string enters Ground engine context.
```

Second critical test:

```text
Ground answer exists.
Assert KnowledgeMemory count does not increase merely because a Ground turn completed.
```

## Phase 2 exit criteria

The following sequence is fully supported by the backend:

```text
Ground
  -> source-grounded turn
  -> no durable knowledge write

Research
  -> state-aware turn
  -> working memory updated
  -> candidate generated

Ground
  -> can continue conversation
  -> does not receive Research-derived evidence
```

---

# 5. Phase 3 — Promotion, Provenance, Derivation and Workspace Versioning

## Objective

Turn Research output into a controlled human-reviewed knowledge pipeline.

## Phase 3 workstreams

### P3.1 — Candidate lifecycle fields

Modify:

`app/models/research.py`
`app/repositories/research.py`

Add:

```text
promotion_status
reviewed_by
reviewed_at
review_reason
promoted_target_type
promoted_target_id
```

Add repository functions:

```text
list_candidates_by_status()
get_candidate_for_review()
set_candidate_decision()
link_candidate_target()
```

### P3.2 — Candidate schemas

Create:

`app/schemas/promotion.py`
`app/schemas/research_artifact.py` if useful

Candidate payloads should be type-specific and validated.

Do not allow arbitrary unvalidated dictionaries to become user-visible knowledge.

### P3.3 — Promotion service

Create:

`app/services/research/promotion.py`

Functions:

```text
list_candidates()
get_candidate()
accept_candidate()
reject_candidate()
materialize_memory_candidate()
materialize_graph_candidate()
mark_superseded()
```

Acceptance must be idempotent and transactionally safe.

### P3.4 — Remove automatic promotion from the worker

Modify:

`app/workers/tasks.py`
`app/services/research/service.py`

Current behavior is effectively:

```text
completed run
 -> promote_memory_candidates()
 -> promote_graph_candidates()
```

Replace with:

```text
completed run
 -> materialize candidate artifacts
 -> mark pending_review
 -> emit promotion.available
```

A user/API decision performs the promotion.

### P3.5 — Provenance strengthening

Modify:

`app/services/research/provenance.py`
`app/schemas/graph.py`
`app/schemas/knowledge.py`

Add typed provenance references.

Research candidates should be able to reference:

- ResearchEvidence;
- Source/SourceSnapshot;
- DocumentBlock;
- ResearchArtifact;
- ConversationTurn;
- KnowledgeMemory.

The provenance chain must be auditable across workspace boundaries.

### P3.6 — Derivation service

Create:

`app/services/research/derivation.py`

Functions:

```text
build_provenance_bundle()
normalize_derivation()
attach_evidence_refs()
validate_claim_sources()
```

The ODR adapter may continue producing its own result, but Neosis normalizes the result into canonical provenance before a candidate is considered valid.

### P3.7 — Verification service

Create:

`app/services/research/verification.py`

Functions:

```text
verify_calculation()
verify_claim()
build_verification_result()
```

Start with deterministic arithmetic/calculation verification. Keep the interface extensible but do not build a giant verification framework in Phase 3.

### P3.8 — Output KG acceptance gate

Modify:

`app/repositories/graph.py`
`app/services/research/promotion.py`
`app/workers/tasks.py`

The graph projection path remains the same. The difference is when it is called.

```text
candidate graph
 -> pending_review
 -> user accepts
 -> project_output_graph()
```

The Internal KG synchronization of accepted KnowledgeMemory can remain as already implemented.

### P3.9 — Workspace commit manifest

Modify:

`app/models/workspace.py`
`app/repositories/workspace.py`
`app/schemas/workspace.py`

Add a durable workspace manifest that captures:

- approved KnowledgeMemory IDs;
- accepted artifact IDs;
- Output KG version/reference;
- active hypotheses;
- scratchpad checkpoint/version;
- conversation checkpoint/reference;
- base research run IDs.

Do not copy large content blobs into every commit.

### P3.10 — Research base commit

Modify:

`app/models/research.py`
`app/repositories/research.py`
`app/services/chat/service.py`

When a Research turn starts, store the current `base_commit_id`.

This allows historical reproduction of the workspace state used to start research.

## Phase 3 tests

Create:

`tests/integration/research/test_promotion.py`
`tests/integration/research/test_provenance.py`
`tests/integration/research/test_verification.py`
`tests/integration/research/test_output_graph_acceptance.py`
`tests/integration/workspace/test_commit_manifest.py`

Test matrix:

| Candidate | Accept | Reject | Re-accept | Target |
|---|---|---|---|---|
| memory_candidate | create exactly one memory | no memory | idempotent | KnowledgeMemory |
| graph_candidate | create/projection once | no graph | idempotent | Output KG |
| hypothesis_candidate | update working state | remains unpromoted | idempotent | Working state |
| claim_candidate | persist approved claim/finding | remains audit-only | idempotent | Claim/finding target |

## Phase 3 exit criteria

No Research candidate reaches durable KnowledgeMemory or user-visible Output KG without a recorded user decision.

Every accepted derived result has reconstructable provenance.

Workspace rollback can select a prior approved research state without destroying historical execution records.

---

# 6. Phase 4 — Unified Execution and Chapter 3 Integration

## Objective

Wire the canonical Chapter 4 conversation/state layer to the existing Chapter 3 execution components. This is where the backend becomes operationally seamless.

The rule is to adapt interfaces, not redesign engines.

## Phase 4 workstreams

### P4.1 — Ground execution adapter integration

Modify:

`app/integrations/open_notebook/ground_engine.py`
`app/integrations/open_notebook/client.py`

Ground execution should accept:

```text
workspace_id
conversation_id
turn_id
query
source_scope
Open Notebook binding
```

Return:

```text
answer
evidence refs
provenance status
engine metadata
```

No Research context object is allowed here.

### P4.2 — Research execution adapter integration

Modify:

`app/integrations/research_engine/open_deep_research/engine.py`

The adapter receives the canonical ResearchContext generated by Chapter 4.

It maps that into the existing ODR graph's input state.

Do not change the ODR supervisor/researcher structure.

### P4.3 — Structured candidate emission from ODR

The ODR adapter currently creates a `memory_candidate` from the final report. Chapter 4 changes the envelope so the artifact includes structured provenance and candidate metadata.

Recommended payload fields:

```json
{
  "candidate_type": "memory_candidate",
  "content": "...",
  "evidence_refs": [],
  "source_refs": [],
  "derived_from_artifacts": [],
  "verification": {},
  "proposed_memory_type": "research_memory",
  "provenance_version": "v2"
}
```

The adapter may still store the full report as `ResearchReport` exactly as before.

### P4.4 — Worker finalization correction

Modify:

`app/workers/tasks.py`

Keep:

- lifecycle transitions;
- usage tracking;
- durable event persistence;
- report persistence;
- cancellation behavior;
- graph projection job infrastructure.

Change:

- no automatic candidate promotion;
- emit promotion-available events;
- attach run to canonical turn;
- finalize the corresponding ConversationTurn.

### P4.5 — Canonical Research submission

Modify:

`app/services/chat/service.py`
`app/api/routes/chat.py`
`app/api/routes/research.py`
`app/api/routes/workspaces.py`

Research turn submission sequence:

```text
turn created
 -> ResearchContext assembled
 -> ResearchAdmissionController.admit_research_run()
 -> ResearchRun created
 -> lifecycle planning
 -> enqueue existing run_research_agent_job
 -> turn linked to run
 -> event stream available
```

The existing admission/rate-limiter implementation stays authoritative.

### P4.6 — Canonical Ground submission

Ground turn submission sequence:

```text
turn created
 -> GroundContext built
 -> OpenNotebookGroundEngine.run()
 -> answer/evidence normalized
 -> turn finalized
```

No MemoryRouter durable write occurs.

### P4.7 — Research event to chat event bridge

Modify:

`app/repositories/research.py`
`app/services/chat/events.py`
`app/workers/tasks.py`

Map terminal and important ResearchEvent transitions into `ChatEvent`.

Examples:

```text
research.started -> turn.research_started
run.status_changed(planning) -> turn.research_planning
run.status_changed(researching) -> turn.researching
run.status_changed(synthesizing) -> turn.synthesizing
candidate.created -> turn.promotion_available
run.status_changed(completed) -> turn.completed
```

The exact event vocabulary should be documented in code constants/enums rather than free-text strings spread across workers.

### P4.8 — Unified cancellation

Reuse existing Research engine cancellation.

Canonical endpoint:

```text
POST /workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}/cancel
```

For a Research turn:

```text
cancel turn
 -> cancel ResearchRun
 -> existing engine.cancel()
 -> lifecycle cancelled
 -> turn cancelled
```

Ground cancellation only cancels the upstream request/stream and finalizes the turn accordingly.

### P4.9 — Production checkpoint contract

The current ODR adapter has a MemorySaver fallback. Chapter 4 should not silently accept that path for production.

Define configuration semantics:

```text
NEOSIS_ENV=development
  -> MemorySaver allowed

NEOSIS_ENV=production
  -> AsyncPostgresSaver required
  -> startup fails if unavailable
```

The actual persistence integration remains the existing AsyncPostgresSaver work from Chapter 3.

### P4.10 — Repair duplicate/dead API paths

Identify and retire:

- placeholder `enqueue_research_job()`;
- direct research route logic that bypasses canonical conversation turn service;
- direct Ground memory write logic;
- old compatibility paths that still create parallel product state.

Keep compatibility endpoints only when they delegate to the canonical Chapter 4 service.

## Phase 4 integration scenarios

### Scenario A — Ground -> Research

```text
User: Read my uploaded papers and tell me what is established.
  Ground
  -> source-grounded answer

User: Now investigate what the literature says beyond these papers.
  Research
  -> ODR
  -> external evidence
  -> ResearchRun
  -> pending candidates
```

### Scenario B — Research -> Ground

```text
User: Compare those new findings with my uploaded paper.
  Ground
  -> current user query
  -> uploaded source corpus
  -> no research memory injection
```

### Scenario C — Research -> accept promotion

```text
Research completes
 -> candidate shown by backend as pending
 -> accept
 -> KnowledgeMemory created
 -> internal graph sync
 -> next Research turn can use it
```

### Scenario D — Research -> reject promotion

```text
Research completes
 -> candidate pending
 -> reject
 -> candidate remains audit history
 -> no KnowledgeMemory
 -> no Output KG projection
```

## Phase 4 tests

Create end-to-end tests:

`tests/e2e/test_ground_research_ground.py`  
`tests/e2e/test_research_promotion.py`  
`tests/e2e/test_unified_turn_stream.py`  
`tests/e2e/test_ground_isolation_after_research.py`

These are the most important tests in the chapter.

---

# 7. Phase 5 — Verification, Migration, Production Readiness and Chapter 5 Handoff

## Objective

Finish the backend as a coherent production surface and hand the frontend a stable contract.

## Phase 5 workstreams

### P5.1 — Full regression audit

Run:

- Chapter 3 acceptance suite;
- all existing Ground tests;
- all Research tests;
- new Chapter 4 unit/integration/E2E suites.

Expected outcome:

No Chapter 3 regression caused by the new conversation/memory layer.

### P5.2 — Migration execution

Create and test migrations for:

- conversations;
- turns;
- chat events;
- scratchpad;
- ResearchArtifact promotion state;
- ResearchRun links/base commit;
- workspace commit manifest;
- Open Notebook conversation binding migration.

Migration requirements:

- forward migration;
- rollback migration where safe;
- backfill validation;
- row-count verification;
- foreign-key validation;
- index creation validation.

### P5.3 — Historical state reconciliation

Write a one-time reconciliation script under:

`scripts/reconcile_chapter4_state.py`

Responsibilities:

- map GroundConversation -> Conversation;
- map Open Notebook bindings;
- mark legacy Ground KnowledgeMemory rows;
- backfill ResearchRun/Turn linkage where possible;
- identify already-promoted research candidates;
- report inconsistent provenance without deleting history.

The script should be idempotent.

### P5.4 — Observability verification

Verify telemetry fields exist for:

```text
workspace_id
conversation_id
turn_id
run_id
mode
engine
candidate_id
promotion_decision
```

Add dashboards/metrics only to the existing telemetry system. Do not introduce a second observability platform.

### P5.5 — Concurrency verification

Test:

- duplicate turn submissions;
- concurrent turns on one conversation;
- two users/workspaces in parallel;
- accept/reject racing on the same candidate;
- stream reconnects;
- worker retry after crash;
- Research run completion while the client disconnects.

The goal is correctness under concurrency, not a 1000-user benchmark.

### P5.6 — API contract stabilization

Freeze the Chapter 4 backend contracts for Chapter 5:

```text
Conversation
Turn
TurnEvent
ResearchRun status
PromotionCandidate
ScratchpadEntry
WorkspaceCommit
OutputGraph
ProvenanceBundle
```

Generate/validate OpenAPI descriptions where the project already supports them.

### P5.7 — Deprecation cleanup

Mark old direct routes and classes as deprecated only after canonical routes are verified.

Potentially deprecated:

- `GroundConversation` as a product-level model;
- direct Ground `/ask` implementation path;
- direct Research route orchestration;
- legacy mode orchestrators;
- placeholder enqueue path.

Do not delete old code until the canonical backend path is verified and migration is complete.

### P5.8 — Chapter 5 handoff

Create:

`docs/chapter4-api-contract.md`
`docs/chapter4-state-model.md`
`docs/chapter4-event-catalog.md`
`docs/chapter4-ui-handoff.md`

The UI handoff must explain:

- how to create a conversation;
- how to send a Ground turn;
- how to send a Research turn;
- how to subscribe/reconnect to events;
- how to display pending promotions;
- how to accept/reject;
- how to read Scratchpad;
- how to show workspace versions;
- how to render Output KG provenance.

No UI implementation belongs in Phase 5.

## Phase 5 exit criteria

The backend can be deployed and used by a frontend with no need for a second backend abstraction.

---

# 8. Detailed File Change Matrix

| File | Phase | Change type | Main functions |
|---|---|---|---|
| `app/models/conversation.py` | P1 | Major extend | Conversation, ConversationTurn |
| `app/schemas/conversation.py` | P1 | Extend | legacy compatibility only |
| `app/schemas/chat.py` | P1 | New | canonical chat contracts |
| `app/repositories/conversation.py` | P1 | New | conversation/turn CRUD + sequencing |
| `app/models/chat_event.py` | P1 | New | ChatEvent |
| `app/repositories/chat_events.py` | P1 | New | append/replay |
| `app/services/chat/events.py` | P1/P4 | New | persist/publish/replay |
| `app/services/chat/service.py` | P1/P2/P4 | New | submit/dispatch/finalize turns |
| `app/services/chat/context.py` | P2/P4 | New | Ground/Research context assembly |
| `app/api/routes/chat.py` | P1/P4 | New | canonical API |
| `app/api/routes/workspaces.py` | P2/P4 | Modify | remove auto Ground memory write |
| `app/api/routes/research.py` | P1/P4 | Modify | remove placeholder/split path |
| `app/models/scratchpad.py` | P2 | New | durable Scratchpad |
| `app/schemas/scratchpad.py` | P2 | New | Scratchpad contracts |
| `app/repositories/scratchpad.py` | P2 | New | Scratchpad persistence |
| `app/services/working_memory.py` | P2 | Major modify | durable state wrapper |
| `app/schemas/working_memory.py` | P2 | Extend | richer deltas/entries |
| `app/services/memory/policy.py` | P2 | New | mode isolation |
| `app/services/memory/context.py` | P2 | New | memory/context assembly |
| `app/services/memory_router.py` | P2 | Refactor | write routing only + compatibility |
| `app/models/research.py` | P3/P4 | Extend | run links, promotion state |
| `app/repositories/research.py` | P3/P4 | Extend | candidate/review/run links |
| `app/services/research/service.py` | P3 | Refactor | candidate materialization, no auto-promotion |
| `app/services/research/promotion.py` | P3 | New | accept/reject/materialize |
| `app/services/research/provenance.py` | P3 | Extend | typed provenance |
| `app/services/research/derivation.py` | P3 | New | derivation normalization |
| `app/services/research/verification.py` | P3 | New | deterministic verification |
| `app/schemas/promotion.py` | P3 | New | review API |
| `app/schemas/graph.py` | P3 | Extend | typed provenance |
| `app/schemas/knowledge.py` | P3 | Extend | origin/provenance |
| `app/models/workspace.py` | P3 | Extend | commit manifest |
| `app/repositories/workspace.py` | P3 | Extend | manifest build/restore |
| `app/schemas/workspace.py` | P3 | Extend | manifest response |
| `app/repositories/graph.py` | P3 | Small modify | accepted projection metadata |
| `app/api/routes/promotions.py` | P3 | New | accept/reject API |
| `app/api/routes/scratchpad.py` | P2 | New | Scratchpad API |
| `app/api/routes/versions.py` | P3 | New/compat | version API |
| `app/integrations/open_notebook/ground_engine.py` | P4 | Modify | turn-aware source-only execution |
| `app/integrations/open_notebook/client.py` | P4 | Small modify | canonical session metadata |
| `app/integrations/open_notebook_binding.py` | P1 | Migration support | canonical conversation binding |
| `app/integrations/research_engine/open_deep_research/engine.py` | P4 | Adapter modify | context + candidate/provenance integration |
| `app/integrations/research_engine/factory.py` | P4 | Small modify | canonical resolution only |
| `app/workers/tasks.py` | P3/P4 | Modify | no auto-promotion, turn/event linkage |
| `app/core/config.py` | P4 | Modify | explicit production checkpointer policy |
| `tests/integration/chat/*` | P1/P2/P4 | New | canonical chat tests |
| `tests/integration/memory/*` | P2 | New | policy/state tests |
| `tests/integration/research/test_promotion.py` | P3 | New | review gate |
| `tests/integration/research/test_provenance.py` | P3 | New | provenance chain |
| `tests/integration/research/test_output_graph_acceptance.py` | P3 | New | graph gate |
| `tests/integration/workspace/test_commit_manifest.py` | P3 | New | versioning |
| `tests/e2e/test_ground_research_ground.py` | P4 | New | central workflow |
| `tests/e2e/test_ground_isolation_after_research.py` | P4 | New | critical invariant |
| `scripts/reconcile_chapter4_state.py` | P5 | New | one-time migration/reconciliation |

---

# 9. Suggested Implementation Order Inside Each Phase

Do not implement horizontally by file type. Implement vertically.

For each phase:

```text
model/schema
   -> repository
      -> service
         -> route
            -> integration/worker
               -> tests
```

Example for promotion:

```text
ResearchArtifact review fields
   -> ResearchRepository decision method
      -> PromotionService.accept/reject
         -> /promotions/{id}/accept route
            -> graph/memory materialization
               -> integration test
```

This avoids creating interfaces before the end-to-end behavior exists.

---

# 10. Critical Invariants to Encode as Tests

These should exist as named tests and documentation, not just developer assumptions.

### INV-01 — Ground evidence purity

A Ground turn may be grounded only in the canonical workspace source set.

### INV-02 — No Research-derived Ground injection

`KnowledgeMemory`, `ResearchEvidence`, `ResearchReport`, `ScratchpadEntry`, hypotheses and Output KG content are forbidden from Ground context.

### INV-03 — Ground does not auto-promote

A successful Ground response does not create KnowledgeMemory or Output KG state.

### INV-04 — Research state continuity

A Research turn can read its previous research Working Memory and approved state.

### INV-05 — User-controlled promotion

No candidate becomes durable KnowledgeMemory or Output KG solely because the model produced it.

### INV-06 — Promotion idempotency

Repeated accept requests cannot duplicate target state.

### INV-07 — Workspace isolation

A candidate/evidence/memory/turn from workspace A cannot be read or promoted into workspace B.

### INV-08 — Version reproducibility

A ResearchRun records the workspace version from which it started.

### INV-09 — Historical preservation

Rollback does not delete ResearchRun/Evidence/Conversation history.

### INV-10 — Durable stream replay

A disconnected client can resume from a persisted event sequence.

### INV-11 — No engine architecture replacement

Existing ODR/Open Notebook integrations remain the execution implementations behind canonical services.

---

# 11. Final Chapter 4 Backend Flow

After all five phases, the backend should implement the following complete system.

```text
                         USER MESSAGE
                              |
                              v
                      Canonical Conversation
                              |
                     +--------+--------+
                     |                 |
                  GROUND            RESEARCH
                     |                 |
             GroundContext       ResearchContext
                     |                 |
            source-only           state-aware
                     |                 |
             Open Notebook        existing ODR
                     |                 |
                Ground turn     ResearchRun
                     |                 |
                     |         Evidence / Report
                     |                 |
                     |             Candidates
                     |                 |
                     |          +------+------+
                     |          |             |
                     |       ACCEPT         REJECT
                     |          |             |
                     |    KnowledgeMemory    |
                     |    Output KG          |
                     |          |             |
                     +----------+-------------+
                                |
                         Research context
                                |
                     NEVER Ground evidence
```

The frontend in Chapter 5 should simply render and control this backend state. It should not have to invent missing concepts such as candidate review, memory policy, turn identity, research run linkage, or versioning.

---

# 12. Chapter 4 Completion Checklist

## Conversation

- [ ] Canonical Conversation exists.
- [ ] ConversationTurn exists.
- [ ] Ground/Research are turn modes.
- [ ] ResearchRun remains a separate execution entity.
- [ ] Turn idempotency exists.
- [ ] Turn event stream exists.

## Ground

- [ ] Open Notebook remains the Ground engine.
- [ ] Ground receives source-only context.
- [ ] Research memory is never injected.
- [ ] Ground answer is stored as a conversation result, not automatic durable knowledge.
- [ ] Ground no longer auto-syncs answer text to the graph.

## Research

- [ ] ODR remains the primary Research engine.
- [ ] Existing retriever/capability architecture remains unchanged.
- [ ] Research receives bounded shared state.
- [ ] Working Memory persists.
- [ ] Scratchpad persists.
- [ ] ResearchRun links to the triggering turn.

## Promotion

- [ ] Candidates begin as pending.
- [ ] User can accept.
- [ ] User can reject.
- [ ] Decisions are auditable.
- [ ] Acceptance is idempotent.
- [ ] Rejection creates no durable knowledge.

## Provenance

- [ ] Evidence references are structured.
- [ ] Derived claims have provenance.
- [ ] Calculations have verification status.
- [ ] Output KG stores provenance.

## Versioning

- [ ] Workspace commit includes approved research state.
- [ ] ResearchRun records base commit.
- [ ] Rollback preserves historical execution.

## Integration

- [ ] Placeholder research queue path removed.
- [ ] Auto-promotion path removed.
- [ ] ODR adapter uses canonical context.
- [ ] Ground adapter uses canonical turn context.
- [ ] Research events map into chat events.
- [ ] Cancellation flows through the existing lifecycle/engine.
- [ ] Production checkpointer behavior is explicit.

## Verification

- [ ] Ground -> Research -> Ground passes.
- [ ] Research -> Ground isolation passes.
- [ ] Accept/reject flows pass.
- [ ] Streaming replay passes.
- [ ] Versioning/rollback passes.
- [ ] Existing Chapter 3 regression suite passes.
- [ ] Backend API/state/event contracts documented for Chapter 5.

---

# 13. Recommended Delivery Sequence

The implementation team should work in this exact order unless a dependency is discovered:

```text
1. Canonical Conversation + Turn
2. Turn events + idempotency
3. Ground/Research context policies
4. Durable Working Memory + Scratchpad
5. Ground memory-write removal
6. Candidate review state
7. Promotion service + API
8. Provenance + derivation + verification
9. Workspace commit manifest
10. Ground adapter integration
11. ODR adapter integration
12. Worker turn/event integration
13. Unified streaming/cancellation
14. Migration/reconciliation
15. Full E2E verification
16. Chapter 5 backend handoff
```

The key sequencing choice is deliberate: the system's product identity and information-flow rules are defined before the existing engines are wired into the final path. This prevents the Chapter 4 implementation from becoming another layer of route-specific conditionals around Chapter 3.

