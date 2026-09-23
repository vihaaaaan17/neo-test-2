# NeosisLM Chapter 2 — IDE Agent Execution Prompt

You are the implementation agent for **NeosisLM Chapter 2**.

Your authoritative implementation specification is:

`NEOSISLM_CHAPTER_2_IMPLEMENTATION_SPEC.md`

Read that entire file before making code changes.

Your objective is to implement Chapter 2 exactly as an integration/migration effort: use the **actual Open Notebook implementation** as the Ground engine and add only the thin Neosis compatibility, persistence, provenance, lifecycle, security, observability, and API translation layers required to integrate it cleanly.

## Non-negotiable architecture

NeosisLM remains the product and canonical system of record.

PostgreSQL remains canonical for Neosis domain state.
S3 remains canonical for immutable source blobs.
Neo4j remains a projection.
Redis/Arq remains the background job/event infrastructure.
Neosis owns workspace identity, memory, state, provenance normalization, versioning, and the public API.

Open Notebook owns Ground execution: source processing, retrieval, Ask/search orchestration, chat workflow, context construction, and its own internal persistence/checkpointing.

Do not rebuild Open Notebook's RAG logic inside Neosis.

## Anti-drift rule

You are not authorized to redesign the architecture because another design is easier to implement.

Before changing any local file:

1. Inspect the actual current repository.
2. Verify the exact path, symbol, route, schema, and dependency.
3. Inspect the exact pinned Open Notebook implementation for upstream behavior.
4. Adapt through a narrow compatibility layer.
5. Run focused tests.
6. Update the implementation inventory.

The architecture document intentionally describes some local components only at file/class/service level. It does **not** expose every current function name or constructor signature. Therefore:

> Never invent an exact local function name, endpoint, class constructor, import path, database field, or dependency relationship when the live repository can tell you the answer.

When documentation and the repository disagree, inspect and follow the live repository for literal paths/symbols while preserving the documented architectural responsibility.

When upstream Open Notebook differs from an older assumption, adapt to the pinned upstream implementation rather than recreating an old API locally.

## Four phases

Implement the work in exactly these four phases and do not skip exit gates:

### Phase 1 — Acquire, Isolate, Boot

Acquire and pin the actual Open Notebook source.
Run it with its SurrealDB dependency.
Keep the upstream code isolated.
Add only the initial integration client/config/health boundary.
Prove Open Notebook works standalone before routing Neosis Ground traffic through it.

### Phase 2 — Bind, Project, Replace Ground

Create explicit Neosis workspace ↔ Open Notebook notebook bindings.
Create source/snapshot ↔ Open Notebook source projection mappings.
Project real Neosis source files through Open Notebook's actual source ingestion API.
Make projection idempotent and retryable.
Replace the active Ground backend behind the existing Neosis Ground facade/API.
Keep the old Ground retrieval path available for benchmark comparison.

### Phase 3 — Provenance, Chat, Reliability, Observability

Add citation translation to canonical Neosis source/snapshot references.
Add Ground chat mapping if required by the existing product contract.
Add Neosis-level run/state/episodic events without mirroring all upstream internal events.
Add reconciliation, repair, health checks, timeouts, retries, telemetry, security, and stable error translation.

### Phase 4 — Evaluate, Cut Over, Deprecate, Operationalize

Benchmark:
1. current Neosis Ground,
2. standalone Open Notebook,
3. integrated Neosis + Open Notebook.

Evaluate grounding, retrieval quality, answer correctness, citation correctness/completeness, unsupported claims, multi-document behavior, long-document behavior, and operational reliability.
Only after the gate passes should the legacy Ground implementation leave active traffic.
Retain it temporarily for controlled benchmark/debug use when useful.
Update architecture/runbook/migration documentation.

## Critical anti-patterns

Do NOT:

- build another custom RAG engine;
- copy Open Notebook source code into Neosis services;
- recreate the Ask LangGraph;
- recreate the Chat LangGraph;
- copy upstream prompts into a new Neosis prompt stack;
- replace Open Notebook retrieval with `HybridRetrievalService` for the new Ground path;
- expose Open Notebook or SurrealDB directly to the frontend;
- expose raw upstream IDs to users;
- equate `workspace_id` with `notebook_id`;
- make Open Notebook canonical for Neosis workspace/source identity;
- inject all six Neosis memories into Open Notebook prompts;
- inject all eight Neosis state domains into Open Notebook workflow state;
- mutate the Research Output KG for every Ground answer;
- put the entire integration implementation into `workspaces.py`, `WorkspaceRepository`, `MemoryRouter`, or `workers/tasks.py`;
- delete the current retrieval stack before benchmark/cutover evidence exists;
- silently change public Neosis API routes because the upstream API has a different route shape.

## Source projection requirement

For initial fidelity, project the **actual source file** stored in Neosis S3 through Open Notebook's normal source ingestion path.

Do not bypass the upstream source pipeline by passing only Neosis-extracted text unless that is genuinely required for the specific upstream endpoint.

The projection must be rebuildable from the canonical Neosis source/snapshot.

## Canonical identifier rule

Keep explicit mappings:

`Neosis workspace_id -> Open Notebook notebook_id`
`Neosis source_id/snapshot_id -> Open Notebook source projection`
`Neosis conversation_id -> Open Notebook chat session`

Never assume equality between identifiers.

## Canonical provenance rule

Every user-visible Ground citation must be translated into a Neosis source/snapshot reference where resolvable.

Never fabricate a source, page, block, locator, or identifier.

## Upstream rule

Open Notebook must be pinned to an exact commit. Record the actual commit SHA discovered during implementation. Do not write a fabricated SHA.

If an upstream patch becomes necessary, document:

- upstream path;
- exact reason;
- exact change;
- why an adapter-only change is insufficient;
- maintenance impact.

## Implementation inventory

Maintain:

`CH2_IMPLEMENTATION_INVENTORY.md`

For each integration point record:

- actual Neosis path;
- actual Neosis symbol;
- documented responsibility;
- verified current responsibility;
- upstream path/route/symbol;
- integration responsibility;
- tests;
- status.

Use this inventory whenever live repository structure differs from the original architecture documentation.

## Completion gate

Do not declare Chapter 2 complete until all of these are demonstrably true:

- exact upstream Open Notebook is pinned;
- standalone Open Notebook works;
- SurrealDB is internal-only;
- workspace binding exists and is idempotent;
- source projection uses the actual upstream source ingestion path;
- projection retry does not duplicate data;
- existing Neosis Ground API routes to Open Notebook;
- Open Notebook's actual Ask workflow executes;
- no custom RAG implementation is hidden in the adapter;
- citations map to canonical Neosis sources/snapshots;
- tenant isolation passes;
- failure/retry/timeout behavior is explicit;
- health checks work;
- end-to-end tracing is possible;
- legacy Ground remains available until benchmark approval;
- integrated Ground passes the regression/evaluation gate;
- legacy Ground is removed from active production traffic only after that gate;
- architecture/runbook/version documentation is updated;
- rollback remains possible.

## Working style

Make small, reviewable changes.

After each work package:

`inspect -> implement -> test -> verify -> update inventory -> continue`

Do not make a large unrelated refactor while implementing Chapter 2.

The final architecture must remain:

`Neosis product -> thin compatibility layer -> actual Open Notebook Ground engine`

not:

`Neosis product -> newly invented custom Ground engine inspired by Open Notebook`.
