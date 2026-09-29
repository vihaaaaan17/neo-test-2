# Chapter 4 — Post-Implementation Bug Fix Phase
## Consolidated Audit of the Existing Implementation

> **Canonical intent:** Fix the existing Chapter 4 implementation in one consolidated phase. Do not rebuild Chapter 4 from scratch.

## Audit Basis

This audit reconciles the Chapter 4 implementation plan, backend architecture specification, frozen API contract, frozen SSE event catalog, frozen domain state model, frozen frontend handoff, and the repository-derived implementation audit recorded against `main` at commit `9ae29693900ae85bcd4d45c254aedbc4e3af6e96`.

The direct GitHub repository `vihaaaaan17/neo-test-2` could not be re-fetched from this execution environment because the connected GitHub integration did not expose the repository and outbound GitHub network access was unavailable. Therefore, GitHub-specific claims below are grounded in the repository-derived audit artifact rather than represented as an independently re-fetched live repository state.

The five frozen handoff documents are treated as contract evidence, not as proof that the implementation matches them. Where implementation and documentation disagree, the bug-fix phase must make one canonical behavior explicit and update the affected contract.

## Audit Conclusion

Chapter 4 is substantially implemented, but it is **not yet implementation-complete**. The remaining gaps are concentrated at execution boundaries: Ground source enforcement, genuine SSE transport, event ordering/deduplication, concurrency and cancellation races, timeline/version authority, candidate validation, promotion transaction safety, rollback visibility, tenant integrity, observability, migration reconciliation, and contract drift.

The correct response is a **single post-implementation bug-fix phase**, not another architecture chapter.


**Repository:** `https://github.com/vihaaaaan17/neo-test-2`  
**Audited branch:** `main`  
**Audited commit:** `9ae29693900ae85bcd4d45c254aedbc4e3af6e96`  
**Scope:** Chapter 4 implementation only  
**Approach:** Fix the existing implementation. Do **not** rebuild Chapter 4 from scratch.

---

# 0. Audit conclusion

Chapter 4 is substantially implemented but is not yet implementation-complete. This document consolidates the remaining defects into one fix phase.

**Do not redesign ODR, Open Notebook, ARQ, retrieval, memory, promotion, or graph architecture.**

---

# 1. P0 / CRITICAL — Ground source scope is not enforced at execution time

### Location

```text
app/services/chat/context.py
    resolve_ground_source_scope()

app/services/chat/service.py
    _execute_ground_turn()
    _execute_ground_stream_background()
    submit_turn()
    stream_turn()

app/integrations/open_notebook/ground_engine.py
    run()
    astream()
    _resolve_citations()

app/integrations/open_notebook/client.py
    search()
    chat_execute()
    chat_stream()
```

### Problem

The backend validates `source_scope` against canonical PostgreSQL Sources, but Open Notebook retrieval itself is not constrained to that scope.

`OpenNotebookClient.search()` searches the whole notebook.

`chat_execute()` obtains Open Notebook context with:

```text
context_config = {}
```

and does not pass a source allowlist.

The Ground engine filters citation IDs **after** Open Notebook has already searched/synthesized.

Therefore a source outside the requested scope can influence the answer while its citation is later removed.

### Required fix

Make source scope an execution-level constraint, not a post-processing filter.

The Open Notebook integration must receive the canonical allowed source IDs and use them when constructing retrieval/context.

If Open Notebook cannot enforce exact source-level filtering for an API call, fail closed or use an integration-level mechanism that guarantees only the allowed canonical sources can enter Ground execution.

### Acceptance

A scoped Ground request must be impossible to influence using an out-of-scope source.

Test both unary and streaming execution.

---

# 2. P0 / CRITICAL — Ground streaming is not actually streaming

### Location

```text
app/integrations/open_notebook/client.py
    chat_stream()

app/integrations/open_notebook/ground_engine.py
    astream()
```

### Problem

`chat_stream()` calls `/api/chat/execute`, waits for the full JSON response, extracts the final AI message, and yields it as one token-like event.

The implementation therefore provides:

```text
one large "token"
```

rather than incremental token streaming.

This contradicts the frozen SSE/event contract.

### Required fix

Use the actual Open Notebook streaming endpoint/protocol.

Map genuine incremental chunks into canonical Neosis `token` events.

Preserve:

```text
source scope
conversation session
session rehydration
citation metadata
terminal event semantics
```

Do not simulate streaming by wrapping a completed answer.

### Acceptance

A long Ground answer produces multiple incremental token events before completion.

---

# 3. P0 / CRITICAL — SSE wire protocol is incomplete

### Location

```text
app/services/chat/events.py
    format_sse_event()

app/services/chat/service.py
    stream_turn_events()

app/api/routes/chat.py
    list_turn_events()
```

### Problem

`format_sse_event()` emits:

```text
event:
data:
```

but not:

```text
id:
```

The frozen event contract requires `id=<sequence>`.

Also the API only accepts `after_sequence`; it does not process the standard `Last-Event-ID` header.

### Required fix

Make the canonical formatter sequence-aware:

```text
event: <event_type>
id: <sequence>
data: <json>
```

Accept both:

```text
Last-Event-ID
after_sequence
```

Define deterministic precedence/conflict behavior.

### Acceptance

A browser/client reconnect using only `Last-Event-ID` receives exactly the missing events.

---

# 4. P0 / CRITICAL — SSE replay does not transition to the live stream

### Location

```text
app/api/routes/chat.py
    list_turn_events()

app/services/chat/service.py
    stream_turn_events()
```

### Problem

When `stream=true`, the route fetches historical events once and returns them.

It does not remain connected to live events for an active turn.

The documented behavior is:

```text
replay missing events
        ↓
switch to live stream
```

### Required fix

Make the streaming route use a single replay+live mechanism:

```text
load persisted events after cursor
        ↓
establish live subscription
        ↓
close replay/live race window safely
        ↓
replay missing events
        ↓
stream live events
```

Do not create a gap between replay and subscription.

---

# 5. P0 / CRITICAL — Live SSE is local-process only

### Location

```text
app/services/chat/service.py
    stream_turn_events()

app/services/chat/events.py
    TurnEventBroker
    ChatEventService.record_and_publish()
```

### Problem

`stream_turn_events()` subscribes only to:

```text
TurnEventBroker.subscribe_local()
```

The worker can publish through Redis, but the HTTP SSE process may be a different process.

The current implementation compensates with DB polling, which introduces latency and does not provide a true live multi-worker stream.

### Required fix

Use a Redis-backed live event subscription/fan-in.

Keep PostgreSQL as durable replay source.

Target architecture:

```text
PostgreSQL
  = durable event ledger

Redis
  = live transport

SSE endpoint
  = replay + Redis live stream
```

The local broker may remain as an optimization.

### Acceptance

A worker in process/container A can stream live events to an SSE client served by process/container B.

---

# 6. P0 / CRITICAL — Research event → ChatEvent duplication

### Location

```text
app/services/chat/service.py
    stream_turn()
    _bridge_research_events_background()

app/workers/tasks.py
    run_research_agent_job()
```

### Problem

Both sides can create canonical ChatEvents:

```text
worker -> _bridge_chat_event()
```

and:

```text
ChatService -> _bridge_research_events_background()
```

The same Research lifecycle may therefore be persisted twice.

### Required fix

Choose exactly one canonical ChatEvent writer.

Recommended:

```text
Research worker / lifecycle transition
    ↓
persist ResearchEvent
    ↓
persist mapped ChatEvent
    ↓
publish live ChatEvent
```

The existing bridge should become recovery/replay-only or be removed from the live writer path.

Add event identity/deduplication where necessary.

### Acceptance

One research lifecycle transition produces exactly one corresponding ChatEvent.

---

# 7. P0 / CRITICAL — Timeline epoch is not persisted as the immutable run baseline

### Location

```text
app/models/research.py
    ResearchRun

app/services/chat/service.py
    _execute_research_turn()
    stream_turn()

app/workers/tasks.py
    run_research_agent_job()
```

### Problem

The worker captures:

```text
expected_epoch = workspace.timeline_epoch
```

at worker start.

That is unsafe for retries.

A ResearchRun created before rollback can be retried afterward, see the new current epoch, and incorrectly adopt it as its own baseline.

### Required fix

Persist:

```text
ResearchRun.base_timeline_epoch
```

at Research submission/admission time.

Every retry must use that immutable value.

Never redefine a run's baseline from the current workspace epoch.

### Acceptance

```text
run created at epoch 10
rollback -> epoch 11
retry old run
```

must remain fenced as an epoch-10 run.

---

# 8. P0 / CRITICAL — Timeline fencing does not cover all durable worker writes

### Location

```text
app/workers/tasks.py
    run_research_agent_job()

app/repositories/research.py
    create_event()
    create_evidence()
    create_artifact()
    create_report()
    create_usage()
```

### Problem

The worker checks the epoch primarily around finalization.

During execution it can still write:

```text
ResearchEvidence
ResearchReport
ResearchArtifact
ResearchUsage
ResearchEvent
ScratchpadEntry
```

after a rollback.

### Required fix

Define a clear rule:

### Historical execution records

May survive rollback, but must carry the run's immutable baseline epoch and must never affect active workspace state.

### Active workspace mutations

Must be fenced against the current timeline epoch.

Implement the epoch check at the canonical durable mutation boundary instead of duplicating ad-hoc checks throughout workers.

### Acceptance

Rollback during active research cannot alter active workspace state, while historical execution records remain auditable.

---

# 9. P0 / CRITICAL — PromotionService does not enforce the timeline fence

### Location

```text
app/services/research/promotion.py
    accept_candidate()
```

### Problem

A candidate from an old timeline can still be accepted after rollback.

The promotion code validates provenance and lifecycle, but not the candidate/run's active timeline eligibility.

### Required fix

Inside the acceptance transaction:

```text
lock workspace
lock candidate
verify candidate/run baseline epoch == current workspace epoch
```

If stale:

```text
reject promotion
or require explicit rebase
```

Do not silently promote a stale candidate into the new active workspace.

### Acceptance

A pre-rollback candidate cannot mutate the post-rollback active timeline.

---

# 10. P0 / CRITICAL — Output graph projection job is independently ungated

### Location

```text
app/workers/tasks.py
    project_output_graph_job()
```

### Problem

The job accepts:

```text
workspace_id
graph_dict
```

and projects directly into Neo4j.

It does not independently verify:

```text
candidate ID
candidate accepted status
workspace ownership
current timeline epoch
```

PromotionService currently enqueues it, but the job itself is not authoritative.

### Required fix

Pass an authority envelope, e.g.:

```text
workspace_id
artifact_id
expected_epoch
```

Worker verifies:

```text
candidate exists
candidate belongs to workspace
candidate type == graph_candidate
promotion_status == accepted
epoch is still current
```

Only then project.

### Acceptance

Direct/manual/replayed invocation of the worker cannot project an unaccepted or stale graph candidate.

---

# 11. P0 / CRITICAL — Rollback does not actually restore active state

### Location

```text
app/repositories/workspace.py
    rollback_workspace_atomic()

app/api/routes/workspaces.py
    rollback_workspace()

app/repositories/graph.py
    get_output_graph()
    project_output_graph()

app/services/chat/context.py
    build_research_context()
```

### Problem

Rollback currently changes:

```text
active_commit_id
timeline_epoch
```

but does not restore/filter:

```text
KnowledgeMemory
Scratchpad
Research context
Output KG
```

Therefore a rollback is currently closer to:

```text
move pointer
```

than:

```text
restore active workspace state
```

### Required fix

Do not delete historical objects.

Make the active commit manifest authoritative.

Active-state readers must filter against the current active commit/timeline.

For Output KG, make graph visibility version-aware.

For Research context, use only state present in the active manifest.

### Acceptance

After rollback:

```text
reverted memory
reverted scratchpad state
reverted graph state
```

cannot appear in current Research/Graph state.

Historical records remain queryable through historical views where supported.

---

# 12. P0 / CRITICAL — Output KG is not version-aware

### Location

```text
app/repositories/graph.py
    project_output_graph()
    get_output_graph()
```

### Problem

Graph nodes/edges are stored only by workspace and node IDs.

There is no effective:

```text
commit_id
timeline_epoch
active version
```

filtering.

`get_output_graph()` therefore returns the workspace graph without regard to rollback state.

### Required fix

Add version metadata to projected graph state or establish an equivalent version-aware projection strategy.

`get_output_graph(workspace_id)` must return only the active graph state.

Keep Neo4j as a derived projection.

### Acceptance

Graph state before rollback, after rollback, and after new promotion are distinguishable and correct.

---

# 13. P0 / CRITICAL — Research context can read stale post-rollback state

### Location

```text
app/services/chat/context.py
    build_research_context()
```

### Problem

Queries currently read:

```text
KnowledgeMemory
ResearchEvidence
ScratchpadEntry
ConversationTurn
OutputGraph
```

without consistently constraining them to the active workspace version/timeline.

### Required fix

Context assembly must resolve the active workspace manifest/version first.

Only active eligible state enters Research context.

Historical state must be opt-in.

### Acceptance

A reverted KnowledgeMemory, Scratchpad entry, or graph fact does not re-enter a new Research turn.

---

# 14. P0 / CRITICAL — Promotion queueing happens before canonical commit

### Location

```text
app/services/research/promotion.py
    accept_candidate()
```

### Problem

For memory and graph candidates, the code can enqueue the projection job before committing the candidate's accepted state.

Failure window:

```text
enqueue succeeds
DB commit fails
worker runs
target/acceptance may not exist
```

### Required fix

Canonical sequence:

```text
DB transaction
    ↓
materialize target
    ↓
mark candidate accepted
    ↓
COMMIT
    ↓
enqueue projection
```

Prefer an existing durable/outbox-style mechanism if needed to guarantee post-commit delivery.

Do not move Neo4j into the DB transaction.

---

# 15. P0 / CRITICAL — Terminal event/state ordering is inconsistent

### Location

```text
app/services/chat/service.py
    _execute_ground_turn()
    _execute_ground_stream_background()
    cancel_turn()

app/workers/tasks.py
    run_research_agent_job()

app/services/chat/events.py
    ChatEventRepository.append_event()
```

### Problem

The code can:

```text
mark Turn terminal
    ↓
append terminal ChatEvent
```

while the frozen state model says terminal turns cannot receive later events.

`ChatEventRepository.append_event()` does not itself enforce terminal-state rules.

### Required fix

Define one terminal transition transaction.

Recommended:

```text
lock turn
verify non-terminal
append allowed terminal event(s)
mark terminal state
commit
publish
```

Or define a single repository operation that atomically records the terminal event and state transition.

### Acceptance

No event can be appended after a turn reaches a terminal state.

---

# 16. P0 / CRITICAL — Cancellation/worker completion race

### Location

```text
app/services/chat/service.py
    cancel_turn()

app/services/research/lifecycle.py
    transition_run()

app/workers/tasks.py
    run_research_agent_job()
```

### Problem

`cancel_turn()` and the research worker can race.

The worker may finalize:

```text
completed
```

after cancellation already changed the turn/run to:

```text
cancelled
```

There is also a concrete signature mismatch:

`cancel_turn()` calls `transition_run()` using:

```text
target_status=
metadata=
```

while the actual function signature expects:

```text
new_status=
payload=
```

The exception is then masked by a fallback direct status mutation.

### Required fix

1. Fix the lifecycle method call.
2. Remove the error-masking fallback.
3. Make terminal transitions compare-and-set/row-locked.
4. A terminal `cancelled` turn/run cannot later become `completed`.
5. Worker completion must detect terminal cancellation and stop finalization.

### Acceptance

Cancel vs complete race yields exactly one legal terminal state.

---

# 17. P0 / CRITICAL — All ResearchArtifacts are effectively promotion candidates

### Location

```text
app/models/research.py
    ResearchArtifact.promotion_status

app/repositories/research.py
    create_artifact()
    list_candidates_by_status()
    get_candidate_for_review()

app/services/research/promotion.py
    list_candidates()
    get_candidate()
```

### Problem

`ResearchArtifact.promotion_status` defaults to:

```text
pending_review
```

even for ordinary execution artifacts.

Repository candidate queries do not constrain artifact type.

Therefore arbitrary artifacts can enter the promotion API.

### Required fix

Define a candidate-type allowlist:

```text
memory_candidate
graph_candidate
claim_candidate
finding_candidate
hypothesis_candidate
```

Non-promotable artifacts must be:

```text
not_promotable
```

or otherwise explicitly excluded.

Promotion APIs must query only candidate types.

### Acceptance

Raw execution artifacts never appear in the promotion inbox.

---

# 18. P1 / HIGH — Candidate payload schemas exist but are not enforced

### Location

```text
app/schemas/promotion.py
app/services/research/promotion.py
    accept_candidate()
    materialize_graph_candidate()
```

### Problem

Type-specific Pydantic payload schemas exist, but acceptance largely trusts raw:

```text Dict[str, Any]
```

Graph materialization only checks that `nodes` and `edges` keys exist.

### Required fix

Use explicit candidate-type validation before acceptance.

At minimum:

```text
memory_candidate → MemoryCandidatePayload
graph_candidate → GraphCandidatePayload
claim_candidate → ClaimCandidatePayload
finding_candidate → FindingCandidatePayload
hypothesis_candidate → HypothesisCandidatePayload
```

Graph validation must also verify:

```text unique node IDs
valid edge endpoints
required provenance
valid property structures
```

---

# 19. P1 / HIGH — Unsupported candidate types are marked accepted without actual targets

### Location

```text
app/services/research/promotion.py
    accept_candidate()
```

### Problem

Current behavior:

```text
hypothesis_candidate
    → target_type = scratchpad_entry
    → target_id = artifact_id
```

but no ScratchpadEntry is actually created.

Similarly:

```text
claim_candidate
finding_candidate
```

are marked accepted with:

```text claim_finding
```

without a real canonical claim/finding target model.

### Required fix

Until those canonical targets exist:

```text
hypothesis_candidate
claim_candidate
finding_candidate
```

must not be falsely marked accepted.

Either:

```text
mark not_promotable
```

or explicitly implement the real target materialization using already-approved domain models.

Do not create fake target IDs.

---

# 20. P1 / HIGH — Accepted KnowledgeMemory cannot re-enter Research context

### Location

```text
app/services/research/promotion.py
    materialize_memory_candidate()

app/services/chat/context.py
    build_research_context()
```

### Problem

Promotion creates:

```text
KnowledgeMemory.status = "active"
```

while Research context currently selects:

```text
status == "accepted"
```

Result: accepted research memory is not visible to later Research turns.

### Required fix

Define one canonical KnowledgeMemory lifecycle and align:

```text
materialization
context eligibility
API response
workspace manifests
promotion state
```

Do not solve with an arbitrary query hack.

---

# 21. P1 / HIGH — Legacy automatic promotion methods remain dangerous

### Location

```text
app/services/research/service.py
    promote_memory_candidates()
    promote_graph_candidates()
```

### Problem

These methods remain callable and represent the old auto-promotion path.

Even if no current worker calls them, they remain an architectural bypass.

### Required fix

Remove them or make them explicit wrappers around:

```text
PromotionService.accept_candidate()
```

They must never mean:

```text promote everything
```

Add regression tests proving no implicit promotion API exists.

---

# 22. P1 / HIGH — Research event sequence allocation is race-prone

### Location

```text
app/repositories/research.py
    create_event()

app/models/research.py
    ResearchEvent
```

### Problem

Sequence allocation uses:

```text
MAX(sequence) + 1
```

without locking the ResearchRun row.

There is no unique:

```text (run_id, sequence)
```

constraint.

Also retrieval orders by:

```text created_at
```

instead of sequence.

### Required fix

Use one of:

```text
lock ResearchRun row
```

or an equivalent atomic sequence allocator.

Add:

```text
UniqueConstraint(run_id, sequence)
```

Order by `sequence`.

### Acceptance

Concurrent event writers cannot produce duplicate or non-contiguous run event sequences.

---

# 23. P1 / HIGH — `selected_source_ids` is exposed but ignored

### Location

```text
app/schemas/chat.py
    TurnCreate.selected_source_ids

app/services/chat/service.py
    submit_turn()
    stream_turn()
```

### Problem

The field exists in the API contract but the service only propagates:

```text source_scope
```

The selected source field is effectively dead.

### Required fix

Normalize:

```text selected_source_ids
```

into the canonical source scope before execution/persistence.

Define clear conflict semantics if both fields are supplied.

Persist the resulting authoritative scope.

---

# 24. P1 / HIGH — Ground streaming drops the requested source scope

### Location

```text
app/services/chat/service.py
    stream_turn()
    _execute_ground_stream_background()
```

### Problem

The background Ground stream is launched with:

```text
workspace_id
conversation_id
turn_id
user_message
```

and later calls:

```text
build_ground_context(... explicit_scope=None)
```

So even if the Turn stored a source scope, the streaming execution does not pass it.

### Required fix

Carry the normalized source scope through the stream task and into:

```text build_ground_context()
 OpenNotebookGroundEngine.astream()
```

This is separate from the deeper Open Notebook scope enforcement issue.

---

# 25. P1 / HIGH — Invalid turn mode can persist a bad Turn

### Location

```text
app/schemas/chat.py
    TurnCreate.mode

app/services/chat/service.py
    submit_turn()
    stream_turn()
```

### Problem

`mode` is a free string.

The service allocates a sequence and persists the turn before checking whether the mode is supported.

An invalid request can therefore leave a persisted pending turn.

### Required fix

Use a `Literal`/enum:

```text
ground
research
```

Validate before sequence allocation and DB mutation.

---

# 26. P1 / HIGH — One-running-turn-per-conversation invariant is not enforced

### Location

```text
app/repositories/conversation.py
    allocate_turn_sequence()

app/services/chat/service.py
    submit_turn()
    stream_turn()
```

### Problem

The frozen state model requires:

```text
at most one running turn per conversation
```

The implementation does not enforce this.

### Required fix

Add a locked running-turn check before execution.

Return:

```text
409 Conflict
```

when another turn is already running.

Make idempotency + concurrency deterministic.

Also handle concurrent duplicate `client_request_id` insertion safely rather than leaking `IntegrityError` as a 500.

---

# 27. P1 / HIGH — Ground scope validation silently removes invalid IDs

### Location

```text
app/services/chat/context.py
    resolve_ground_source_scope()
```

### Problem

If a user supplies:

```text
[source_A, source_B]
```

and `source_B` is invalid/cross-workspace, the function returns only `source_A`.

This is dangerous because a malformed scoped request can silently become a broader request.

### Required fix

If explicit scope contains any invalid/cross-workspace source:

```text fail closed
```

Return an explicit client error.

Never silently shrink the user's requested security boundary.

---

# 28. P1 / HIGH — Ground session rehydration loses prior Ground history

### Location

```text
app/services/chat/service.py
    _rehydrate_open_notebook_session()

app/integrations/open_notebook/ground_engine.py
    _get_or_create_conversation_session()
```

### Problem

A new Open Notebook session is created, but the canonical prior Ground-only history is not replayed into that new session.

Therefore session recovery can lose conversational continuity.

### Required fix

Rehydrate Open Notebook from canonical:

```text
Ground-only ConversationTurn history
```

before retrying the user request.

Do not replay Research turns.

---

# 29. P1 / HIGH — Research client can inject untrusted working memory / graph state

### Location

```text
app/services/chat/service.py
    _execute_research_turn()
    submit_turn()
    stream_turn()

app/schemas/chat.py
    TurnCreate.research_options

app/services/chat/context.py
    build_research_context()
```

### Problem

The client can provide arbitrary:

```text research_options["working_memory"]
research_options["output_graph"]
```

and the service passes these values into context assembly.

This bypasses canonical state.

### Required fix

`research_options` may contain execution configuration only.

Never accept client-supplied durable state as authoritative Research context.

Working Memory, Scratchpad, accepted KnowledgeMemory and Output KG must be loaded from canonical backend state.

---

# 30. P1 / HIGH — Research token budget is not server-bounded

### Location

```text
app/services/chat/service.py
    _execute_research_turn()
    stream_turn()

app/services/chat/context.py
    build_research_context()
```

### Problem

Client-supplied `token_budget` is effectively unbounded.

A caller can request:

```text
0
negative
very large
```

values.

### Required fix

Use a typed bounded option with:

```text min
max
default
```

and enforce it server-side.

---

# 31. P1 / HIGH — Research context does not preserve structured Ground evidence

### Location

```text
app/services/chat/context.py
    build_research_context()
```

### Problem

Research gets prior Ground turns as conversational text, but there is no clear structured stream of:

```text Ground finding → ground_evidence_refs
```

The architecture calls for source-linked Ground findings.

### Required fix

Include Ground turn metadata plus canonical `ground_evidence_refs` in Research context.

Keep:

```text assistant text
```

and:

```text canonical evidence references
```

separate.

---

# 32. P1 / HIGH — Scratchpad repository accepts invalid cross-linked IDs

### Location

```text
app/repositories/scratchpad.py
    create_entry()
    set_lifecycle()
    supersede_entry()

app/api/routes/scratchpad.py
    create_scratchpad()
    update_scratchpad()
```

### Problem

The repository does not consistently verify:

```text conversation_id
turn_id
run_id
```

belong to the same workspace/conversation/run relationship.

Lifecycle values are also accepted as arbitrary strings.

### Required fix

Validate linked ownership and legal lifecycle transitions.

Require conversation-scoped user-created entries to actually belong to the target conversation.

`superseded_by_id` must be same-workspace and valid.

---

# 33. P1 / HIGH — Workspace legacy research route still contains a bypass

### Location

```text
app/api/routes/workspaces.py
    start_research()
```

### Problem

Although `app/api/routes/research.py:create_research_run()` follows the canonical path, `start_research()` still:

1. chooses the most recent active conversation;
2. falls back to an in-memory Conversation object if DB access fails;
3. catches any ChatService exception;
4. bypasses canonical turn creation using direct admission;
5. generates a synthetic random `turn_id`.

This is a major integrity problem.

### Required fix

Make this route a pure compatibility delegate:

```text
optional conversation_id
    ↓
otherwise dedicated conversation
    ↓
ChatService.submit_turn()
```

No broad fallback.

No direct ResearchAdmissionController call.

No synthetic turn IDs.

---

# 34. P1 / HIGH — Legacy Ground routes can still create parallel GroundConversation state

### Location

```text
app/api/routes/workspaces.py
    ask_ground_mode()
    ask_ground_mode_stream()
    chat_ground_mode()
    chat_ground_mode_stream()  # if present
```

### Problem

Legacy compatibility routes can still create/use `GroundConversation` as part of runtime behavior.

That keeps the old product-state path alive.

### Required fix

Compatibility routes should delegate to canonical:

```text Conversation
 → ConversationTurn
 → ChatService
```

`GroundConversation` should remain migration-only/legacy read compatibility, not a newly created product record.

---

# 35. P1 / HIGH — Workspace commit manifest is incomplete/inaccurate

### Location

```text
app/api/routes/workspaces.py
    create_workspace_commit()

app/repositories/workspace.py
    create_commit_with_manifest()
```

### Problem

Current manifest contains approximations:

```text output_graph_version = timeline_epoch
scratchpad_checkpoint = active count only
conversation_checkpoint = timestamp only
base_research_run_ids = all workspace runs
```

Also manifest assembly catches broad exceptions and still creates the commit with potentially incomplete state.

### Required fix

Manifest must reference exact canonical versions/IDs.

At minimum capture:

```text approved KnowledgeMemory IDs
 accepted artifact IDs
 actual Output KG version/reference
 active scratchpad IDs/version
 active hypothesis IDs
 conversation checkpoint sequence/turn IDs
 relevant ResearchRun IDs
 timeline epoch
```

If required state cannot be assembled correctly, commit creation should fail rather than create a partial snapshot.

---

# 36. P1 / HIGH — Commit creation and active-pointer update are not atomic

### Location

```text
app/repositories/workspace.py
    create_commit_with_manifest()
    set_active_commit()
```

### Problem

Current flow is:

```text
COMMIT new WorkspaceCommit
    ↓
separate COMMIT active_commit_id
```

There is a failure window where the commit exists but is not active.

### Required fix

Use one transactional operation for:

```text
create commit
update active pointer
```

under an appropriate workspace row lock.

---

# 37. P1 / HIGH — Workspace schema does not match the frozen API contract

### Location

```text
app/schemas/workspace.py
app/api/routes/workspaces.py
app/repositories/workspace.py
```

### Problem

`WorkspaceCreate` is effectively empty.

`WorkspaceUpdate` only supports:

```text
status
```

`WorkspaceResponse` omits fields documented by the frozen contract:

```text name
description
research_engine
```

The route also ignores create input.

### Required fix

Either:

1. implement the documented canonical fields, or
2. deliberately revise the contract to match the actual intended product.

Do not leave schema/docs/code inconsistent.

Given the current handoff, implementing the documented fields is preferred.

---

# 38. P1 / HIGH — Workspace lifecycle terminology is inconsistent

### Location

```text
app/repositories/workspace.py
    delete_workspace()

app/schemas/workspace.py
app/api/routes/workspaces.py
```

### Problem

The code uses:

```text
archived
```

as the deletion state.

The frozen domain model documents:

```text deleted
```

as the terminal workspace state.

### Required fix

Choose one canonical lifecycle and align:

```text model
repository
API
docs
frontend contract
queries
```

Do not silently map between two meanings.

---

# 39. P1 / HIGH — `sync_knowledge_to_graph_job()` has no active-state/epoch authority check

### Location

```text
app/workers/tasks.py
    sync_knowledge_to_graph_job()
```

### Problem

The job retrieves a KnowledgeMemory by ID and writes it into Neo4j without checking:

```text workspace active state
quarantine status
timeline epoch
active commit membership
```

A stale/reverted memory can therefore be projected after rollback.

### Required fix

Pass an authority envelope or resolve it from canonical accepted state.

Verify before projection:

```text memory belongs to workspace
memory is not quarantined
memory is active in current workspace version
```

Add epoch/commit checks where necessary.

---

# 40. P1 / HIGH — Research metrics are still placeholders

### Location

```text
app/services/research/metrics.py
    emit_metrics()
    track_time_to_first_event()
    track_cost()
    track_failures()
    get_observability_dashboard_data()
```

### Problem

These functions claim observability coverage but contain placeholders:

```text wait_time_seconds = 0
time_to_first_event_seconds = 0
track_time_to_first_event() = pass
track_cost() = pass
dashboard = all zeros
```

This conflicts with the production observability objective.

### Required fix

Implement actual measurements using existing instrumentation/data.

At minimum:

```text queue wait time
time to first event
duration
cost
failure counts
active/completed/failed runs
```

Do not add a second observability stack.

---

# 41. P1 / HIGH — E2E tests are not all true end-to-end tests

### Location

```text
tests/e2e/test_ground_research_ground.py
tests/e2e/test_research_promotion.py
tests/e2e/test_unified_turn_stream.py
tests/e2e/test_cancellation_and_fence.py
```

### Problem

Several tests named E2E rely heavily on:

```text AsyncMock
 MagicMock
 fake sessions
 mocked repositories
```

They prove service behavior but not the complete:

```text HTTP → PostgreSQL → Redis → worker → engine → PostgreSQL → SSE
```

path.

### Required fix

Keep unit tests.

Add a small number of high-fidelity E2E tests that exercise real:

```text FastAPI
PostgreSQL
Redis
canonical routes
canonical ChatService
event persistence/replay
```

Mock only external providers/LLMs/ODR where necessary.

Do not require a huge production cluster.

---

# 42. P1 / HIGH — Reconciliation script is not safely scoped in all paths

### Location

```text
scripts/reconcile_chapter4_state.py
    _reconcile_open_notebook_bindings()
    _reconcile_ground_conversations()
    _link_historical_research_runs()
```

### Problem

When `workspace_id` is supplied, binding queries are not consistently restricted to that workspace.

There are also insufficient consistency checks for:

```text run.workspace_id
turn.workspace_id
conversation.workspace_id
```

### Required fix

All reconciliation operations must respect the selected workspace boundary.

When linking historical records, verify workspace/owner relationships explicitly.

An inconsistent record should be reported, not silently linked.

---

# 43. P2 / MEDIUM — Repository mutation methods are not tenant-safe by themselves

### Location

```text
app/repositories/conversation.py
    set_turn_status()
    append_event()

app/repositories/scratchpad.py
    set_lifecycle()
    update_entry()
    pin_to_workspace()
    unpin_from_workspace()
```

### Problem

Some repository mutations identify records by ID without requiring workspace context.

Current route/service validation reduces practical exposure, but the repository layer itself is weaker than the stated tenant-isolation invariant.

### Required fix

Make critical mutations workspace-aware:

```text workspace_id
 conversation_id where applicable
 owner_id where required
```

Use conditional/locked queries.

---

# 44. P2 / MEDIUM — Workspace/child records lack some database-level tenant relationship constraints

### Location

```text
app/models/conversation.py
app/models/research.py
app/models/scratchpad.py
app/models/workspace.py
```

### Problem

Several records have independent:

```text workspace_id
foreign key
```

relationships but not composite constraints proving related entities share the same workspace.

Application checks currently carry much of this guarantee.

### Required fix

Where practical, strengthen DB integrity for:

```text turn ↔ conversation ↔ workspace
scratchpad ↔ conversation ↔ workspace
research run ↔ turn ↔ conversation ↔ workspace
```

Do this only where it can be introduced safely without disruptive redesign.

---

# 45. P2 / MEDIUM — Workspace foreign keys in model schema are incomplete

### Location

```text
app/models/workspace.py
    Workspace.active_commit_id
    WorkspaceCommit.parent_id
```

### Problem

The frozen state model treats these as foreign-key relationships, but the SQLAlchemy model does not define actual FKs for these fields.

### Required fix

Add the appropriate FK relationships and migration if safe.

Preserve historical commit graph semantics.

---

# 46. P2 / MEDIUM — Checkpointer lifecycle is still import-time and weakly managed

### Location

```text
app/services/working_memory.py
    checkpointer = get_checkpointer()
    working_memory_engine = graph_builder.compile(...)
```

### Problem

The checkpointer is initialized at module import time.

The startup validation exists, but there is no clearly managed lifecycle for the actual long-lived async checkpointer instance/pool.

### Required fix

Keep the current architecture but make lifecycle explicit:

```text
startup
    → initialize one managed checkpointer

worker/app lifetime
    → reuse

shutdown
    → close/cleanup resources
```

Validate behavior against the pinned LangGraph package version.

Do not introduce a second persistence system.

---

# 47. P2 / MEDIUM — Provenance legacy field semantics are mixed

### Location

```text
app/services/research/promotion.py
    materialize_memory_candidate()

app/schemas/knowledge.py
    Provenance

app/schemas/graph.py
    ProvenanceBundle
```

### Problem

`derived_from_refs` may contain references that are not actually Source IDs, while `KnowledgeMemory.Provenance.source_refs` semantically describes source references.

Typed references preserve information, but the legacy field becomes ambiguous.

### Required fix

Make the semantic distinction explicit:

```text source_refs
    = source/source_snapshot references

typed_refs
    = typed cross-object lineage
```

Do not put arbitrary ResearchEvidence/Turn IDs into a field presented as source refs.

---

# 48. P2 / MEDIUM — API/TypeScript handoff drift

The frozen frontend contract does not fully match current backend schemas.

### Scratchpad

Handoff currently describes fields/types like:

```text title
pinned
tags
entry_type = insight/citation
```

while backend currently exposes:

```text content
is_pinned_to_workspace
metadata
entry_type = note/observation/hypothesis/investigation/finding
```

### Promotion

Handoff/documentation differs on:

```text notes vs review_reason
promoted_entity_id vs promoted_target_id
reviewer_notes vs reviewed_by/review_reason
```

### Turn/workspace

There are also mismatches around:

```text turn status: done vs completed
workspace response fields
ResearchRun context_version
```

### Required fix

Update the frozen handoff contracts to match the actual canonical backend after the code fixes are complete.

Do not add frontend-only fake fields.

---

# 49. P2 / MEDIUM — Event catalog and implementation drift

### Location

```text
app/models/conversation.py
    ChatEvent.event_type

app/services/chat/events.py
app/workers/tasks.py
```

### Problem

Model comments/documentation describe a narrower event vocabulary than the actual Chapter 4 catalog.

Also some runtime events are emitted as:

```text status_change
progress
done
```

while the catalog expects canonical research milestones.

### Required fix

Centralize canonical event constants and make all emitters use them.

Then update the event catalog to exactly match the implementation.

---

# 50. P2 / MEDIUM — ResearchRun state documentation/code drift

### Location

```text
app/models/research.py
app/services/research/lifecycle.py
app/schemas/research.py
docs/chapter4-state-model.md
docs/chapter4-ui-handoff.md
```

### Problem

Current lifecycle includes:

```text finalizing
aborted_by_timeline_fence
partial
```

while some frozen documents describe different terminal/status values.

The model also does not expose every state/version field documented in the handoff.

### Required fix

Make one canonical state enum/contract and use it consistently across:

```text model
lifecycle service
API schema
events
docs
frontend types
```

---

# 51. P2 / MEDIUM — `ConversationTurn` lacks some database-level constraints expected by the domain

### Location

```text
app/models/conversation.py
    ConversationTurn
```

### Problem

The model has:

```text unique conversation + sequence
unique conversation + client_request_id
```

but execution semantics such as:

```text one running turn per conversation
```

are not encoded or protected beyond application behavior.

### Required fix

Enforce this invariant at the database/application transaction boundary.

A PostgreSQL partial unique index on running turns may be appropriate if compatible with the current lifecycle schema.

---

# 52. P2 / MEDIUM — Research report versioning remains weak

### Location

```text
app/models/research.py
    ResearchReport

app/repositories/research.py
    create_report()
```

### Problem

Reports have a `version` string but no strong version sequence/identity semantics.

This is not immediately catastrophic, but it weakens the historical reproducibility promised by Chapter 4.

### Required fix

Define report version semantics sufficient to distinguish:

```text rerun
refinement
verification update
new evidence
source correction
```

Do not overwrite historical report versions.

---

# 53. P2 / MEDIUM — Graph projection needs stronger graph payload validation

### Location

```text
app/services/research/promotion.py
    materialize_graph_candidate()

app/repositories/graph.py
    project_output_graph()
```

### Problem

Graph schema validation currently allows malformed structures that can lead to:

```text missing edge endpoints
empty IDs
partial projection
invalid dynamic labels/types
```

### Required fix

Before projection validate:

```text every node has non-empty stable ID
node IDs unique
every edge endpoint exists in payload
edge type valid
provenance valid
```

Also ensure projection failures are observable and retryable.

---

# 54. P2 / MEDIUM — Open Notebook conversation binding should have stronger uniqueness/integrity guarantees

### Location

```text
app/models/open_notebook_binding.py
app/integrations/open_notebook/ground_engine.py
    _get_or_create_conversation_session()
```

### Problem

The application expects a single active binding per canonical conversation/workspace, but the database contract should make duplicate bindings impossible.

### Required fix

Verify/add appropriate uniqueness constraints for:

```text conversation_id
```

and, where applicable:

```text workspace_id + active binding
```

Use row locking when creating a missing binding to prevent duplicate sessions under concurrent first requests.

---

# 55. P2 / MEDIUM — Open Notebook session rehydration can race

### Location

```text
app/integrations/open_notebook/ground_engine.py
    _get_or_create_conversation_session()

app/services/chat/service.py
    _rehydrate_open_notebook_session()
```

### Problem

Two concurrent requests can both observe no binding and create two Open Notebook sessions.

### Required fix

Use a transaction/unique constraint/lock around binding creation.

Only one canonical binding may win.

---

# 56. P2 / MEDIUM — Metrics timestamp handling should be timezone-safe

### Location

```text
app/services/research/metrics.py
    emit_metrics()
    track_failures()
```

### Problem

Some timestamps are timezone-aware while metrics fallback uses `datetime.now()` without timezone.

### Required fix

Use UTC-aware timestamps consistently.

---

## Audit boundary: Chapter 4 vs Chapter 4.5

The following are intentionally **not** counted as Chapter 4 implementation gaps because they belong to the separately scoped Chapter 4.5 verification/promotion enhancement: full semantic entailment verification, dedicated critic orchestration, contradiction detection, generalized compute sandboxing, and richer human clarification loops. Chapter 4 must, however, expose clean hooks and preserve the evidence/provenance needed by Chapter 4.5.


# 57. Phase-specific non-goals for this bug-fix phase

Do NOT add:

```text new research engine
new supervisor
STORM implementation
new retriever architecture
new memory framework
new graph database
new queue system
new event system
new UI
full semantic critic system
full contradiction engine
full code execution sandbox
```

Chapter 4.5 remains the dedicated verification/critic/promotion enhancement boundary.

---

# 58. Recommended implementation order

Fix vertically, not file-by-file:

```text
1. Ground source execution boundary
2. SSE replay/live transport and event sequencing
3. Turn concurrency + cancellation/terminal state
4. Timeline epoch authority
5. Candidate eligibility + validation
6. Promotion transaction safety
7. Output KG version/authority
8. Rollback active-state semantics
9. Research context active-version filtering
10. Scratchpad integrity
11. Legacy route cleanup
12. Workspace commit correctness
13. Observability
14. Migration/reconciliation hardening
15. Contract/documentation alignment
16. High-fidelity E2E verification
```

---

# 59. Required tests for the consolidated fix phase

Add or strengthen tests for:

```text
Ground source scope enforced at retrieval time
Ground scope rejects foreign source IDs
selected_source_ids normalization
Ground streaming is genuinely incremental
SSE includes id sequence
Last-Event-ID replay
replay → live handoff
multi-process Redis live events
exactly-once ChatEvent mapping
one-running-turn-per-conversation
duplicate client_request_id race
invalid mode rejected before persistence
cancel vs complete race
terminal event ordering
stale ResearchRun retry after rollback
stale worker durable writes
stale candidate promotion
ungated graph projection rejection
rollback restores active memory visibility
rollback restores active scratchpad visibility
rollback restores active graph visibility
Research context active-version filtering
candidate-type filtering
candidate payload validation
unsupported candidate type cannot be falsely accepted
accepted KnowledgeMemory re-enters Research context
post-commit projection enqueue
research event sequence concurrency
scratchpad ownership/lifecycle
workspace commit atomicity
manifest completeness
legacy research fallback cannot bypass ChatService
metrics actually populated
reconciliation workspace isolation
real HTTP + Postgres + Redis E2E
```

---

# 60. Final acceptance gate

This consolidated fix phase passes only when:

```text
[ ] Ground cannot use an out-of-scope source
[ ] Ground streaming is genuinely incremental
[ ] SSE protocol supports sequence IDs
[ ] Last-Event-ID reconnect works
[ ] replay transitions safely into live events
[ ] multi-worker live streaming works
[ ] each lifecycle event maps once
[ ] terminal Turn state is immutable
[ ] cancel/complete races are deterministic
[ ] ResearchRun retains immutable base timeline epoch
[ ] stale workers cannot mutate active timeline
[ ] stale candidates cannot be promoted
[ ] only real candidate artifacts enter promotion inbox
[ ] candidate payloads are type-validated
[ ] accepted targets actually exist
[ ] promotion commit precedes async projection
[ ] Output KG projection is independently gated
[ ] Output KG is version-aware
[ ] rollback actually changes active visible state
[ ] Research context respects active workspace version
[ ] Scratchpad links/lifecycle are validated
[ ] legacy routes cannot bypass canonical ChatService
[ ] workspace commits are complete and atomic
[ ] observability metrics are real
[ ] migration/reconciliation tooling is safe
[ ] API/event/state/frontend contracts match implementation
[ ] Chapter 3/Phase 2/Phase 3 behavior remains intact
[ ] high-fidelity E2E tests pass
```

---

# 61. Frozen-Contract Consistency Checks

These are documentation/API consistency checks that must be resolved together with the code fixes; they are not permission to invent new architecture.

### 61.1 API error envelope

`chapter4-api-contract.md` documents FastAPI-style `{"detail": ...}` errors, while the Phase 5 handoff discussion specifies a stable product error envelope. Choose one canonical product-level envelope and make route handlers, exception handling, TypeScript types, and tests agree.

**Locations:**
```text
app/main.py
app/api/routes/chat.py
app/api/routes/workspaces.py
app/api/routes/research.py
chapter4-api-contract.md
chapter4-ui-handoff.md
```

### 61.2 Workspace version read APIs

The architecture specification includes `GET /workspaces/{workspace_id}/commits` and `GET /workspaces/{workspace_id}/commits/{commit_id}`, while the frozen API handoff does not document them consistently. Resolve whether these endpoints are canonical and align implementation + handoff.

**Locations:**
```text
app/api/routes/versions.py
app/repositories/workspace.py
chapter4-api-contract.md
chapter4-ui-handoff.md
```

### 61.3 Scratchpad API surface

The architecture specification lists workspace-level Scratchpad CRUD/promote operations, while the frozen contract exposes conversation-scoped list/create plus get/update. Align the actual API surface with the intended Chapter 4 product contract.

**Locations:**
```text
app/api/routes/scratchpad.py
app/repositories/scratchpad.py
chapter4-api-contract.md
chapter4-ui-handoff.md
```

### 61.4 Event/state contract alignment

`turn.completed` is terminal in the domain model but is represented as non-terminal in the SSE catalog. Research lifecycle terminology also differs across the frozen documents. Canonicalize enums/status semantics and regenerate the handoff from the implementation after fixes.

**Locations:**
```text
app/models/conversation.py
app/models/research.py
app/services/research/lifecycle.py
app/services/chat/events.py
chapter4-state-model.md
chapter4-event-catalog.md
chapter4-ui-handoff.md
```

---

# 62. Architecture that must remain after the fixes

```text
                         NEOSISLM
                            |
                       Conversation
                            |
                 +----------+----------+
                 |                     |
               GROUND               RESEARCH
                 |                     |
          GroundContext         ResearchContext
                 |                     |
         Open Notebook              ODR
                 |                     |
          source evidence      evidence / artifacts
                 |                     |
                 +----------+----------+
                            |
                       Canonical State
                            |
             +--------------+---------------+
             |              |               |
          Scratchpad    Promotion       Versioning
                           Gate              |
                       +----+----+            |
                       |         |            |
                 Knowledge     Output KG   Commit/Epoch
                 Memory
```

The important post-fix invariant remains:

> **We are repairing the existing Chapter 4 implementation, not rebuilding it. One canonical product state remains authoritative, PostgreSQL remains the source of truth, existing engines remain behind integration boundaries, and Research-derived state never becomes Ground evidence.**
