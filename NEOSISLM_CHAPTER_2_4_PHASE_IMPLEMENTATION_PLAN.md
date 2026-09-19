# NeosisLM Chapter 2 — Four-Phase Implementation Plan

**Purpose:** Standalone execution roadmap for Chapter 2 of NeosisLM.

**Primary objective:** Replace the current custom Ground/RAG implementation with the actual Open Notebook implementation as the Ground engine, while preserving NeosisLM as the product boundary, canonical data system, shared memory/state fabric, provenance layer, and public API.

**Authoritative relationship:** This file is a phase-level execution companion to `NEOSISLM_CHAPTER_2_IMPLEMENTATION_SPEC.md`. The full specification contains the detailed architectural rules, invariants, contracts, anti-drift protocol, file responsibilities, testing requirements, and migration constraints. When this file and the main specification differ, the main specification wins.

---

## 1. Target Architecture

```text
                              NeosisLM
                                 |
                 +---------------+---------------+
                 |                               |
              GROUND                         RESEARCH
                 |                               |
                 v                               v
       Actual Open Notebook                Future Research
          Ground Engine                     substrate
                 |
                 v
       Neosis compatibility layer
                 |
       +---------+----------------+
       |                          |
       v                          v
Neosis canonical data       Neosis shared fabric
PostgreSQL + S3             memory/state/provenance
       |
       +------------------+
       |                  |
       v                  v
  Internal KG        Research Output KG
```

The central rule is simple:

> **Neosis owns the product. Open Notebook owns Ground execution. The compatibility layer owns the boundary.**

Open Notebook must remain an actual reused engine, not a source of architectural inspiration for a new local RAG implementation.

---

## 2. Four Phases at a Glance

| Phase | Name | Primary goal | Major architectural result |
|---|---|---|---|
| **1** | **Acquire, Isolate, Boot** | Bring the exact Open Notebook codebase into the project and prove it runs independently | A pinned, isolated Open Notebook Ground engine with SurrealDB and no Neosis coupling yet |
| **2** | **Bind, Project, Replace Ground** | Connect Neosis workspaces/sources to Open Notebook and switch the Ground execution path | Neosis Ground requests execute through actual Open Notebook workflows |
| **3** | **Provenance, Chat, Reliability, Observability** | Complete the production boundary around the engine | Citations, chat, retries, idempotency, SSE, health, telemetry, failure handling, security |
| **4** | **Evaluate, Cut Over, Deprecate, Operationalize** | Prove parity/quality, remove the old Ground path from active use, and stabilize the new architecture | Open Notebook is the production Ground engine and the custom Ground implementation is retired from the active path |

The dependency is strictly sequential:

```text
PHASE 1
  |
  v
PHASE 2
  |
  v
PHASE 3
  |
  v
PHASE 4
```

Do not skip a phase gate to make progress in a later phase.

---

# PHASE 1 — ACQUIRE, ISOLATE, BOOT

## Phase objective

Acquire the real upstream Open Notebook implementation, pin it to an explicit commit/version, run it as an isolated internal service, provision its database dependency, and prove that its native source processing, search/ask, chat, and model provisioning workflows operate before any Neosis integration changes are introduced.

## Phase 1 invariant

At the end of Phase 1:

> **Open Notebook must run correctly as Open Notebook.**

The Neosis integration must not yet distort the upstream behavior.

## Workstream 1 — Upstream acquisition

Add the actual Open Notebook repository under an explicit third-party/vendor boundary such as:

```text
third_party/open-notebook/
```

or an equivalent clearly isolated location discovered from the live repository.

Pin the exact commit/tag used by the project.

Record:

- repository URL,
- commit SHA/tag,
- date pinned,
- license information,
- upstream service requirements,
- upstream database requirements,
- local startup procedure,
- supported routes required by Neosis.

Do not make upstream code part of `app/` merely for convenience.

## Workstream 2 — Internal service boundary

Run Open Notebook as a separate internal service.

The root project should gain the required service/container definitions while preserving the existing Neosis services.

Target topology:

```text
Neosis FastAPI
      |
      | internal HTTP
      v
Open Notebook service
      |
      v
Open Notebook SurrealDB
```

The Open Notebook UI should not become the Neosis product UI.

Expose only the internal backend interface required by Neosis.

## Workstream 3 — Baseline upstream behavior

Before any Neosis integration, prove the following directly against Open Notebook:

1. Source creation/upload works.
2. Source processing completes.
3. Search works.
4. Ask/search synthesis works.
5. Native citation/source references are produced as expected.
6. Chat execution works where required by the chosen integration path.
7. Model provisioning works with the supported development configuration.
8. Open Notebook can restart without corruption of its persisted data.

Create small smoke tests or executable verification scripts.

## Workstream 4 — Compatibility inventory

Create a Chapter 2 implementation inventory that records:

- verified upstream endpoint,
- request schema,
- response schema,
- native source ID shape,
- native notebook ID shape,
- source processing status behavior,
- search/ask response structure,
- citation/reference structure,
- chat/session identifiers,
- model configuration mechanism,
- error behavior,
- timeout behavior,
- streaming behavior if present.

Do not infer these structures from documentation when they can be inspected directly.

## Workstream 5 — Configuration isolation

Open Notebook-specific settings must remain isolated from the Neosis configuration surface.

Neosis should own integration configuration such as:

```text
OPEN_NOTEBOOK_BASE_URL
OPEN_NOTEBOOK_TIMEOUT
OPEN_NOTEBOOK_CONNECT_TIMEOUT
OPEN_NOTEBOOK_ENABLED
OPEN_NOTEBOOK_UPSTREAM_VERSION
```

Exact names must be adapted to the current repository configuration conventions rather than invented blindly.

## Phase 1 tests

Minimum validation:

- upstream boot test,
- SurrealDB connectivity test,
- source ingestion smoke test,
- Ask/search smoke test,
- chat smoke test,
- model configuration smoke test,
- service restart test,
- malformed request behavior test.

## Phase 1 exit gate

Phase 1 passes only when all of the following are true:

- exact Open Notebook code is present and pinned,
- the service starts reproducibly,
- SurrealDB is connected and persistent,
- native source ingestion works,
- native Ask/search works,
- native chat works where in scope,
- no Neosis code has been used to replace upstream Ground internals,
- the implementation inventory is complete enough to construct the integration layer,
- CI/local smoke tests are reproducible.

No Phase 2 integration work is considered complete until these criteria pass.

---

# PHASE 2 — BIND, PROJECT, REPLACE GROUND

## Phase objective

Connect Neosis workspaces and sources to the isolated Open Notebook Ground engine, preserve Neosis canonical ownership, and route Ground Mode through the actual upstream Open Notebook execution path.

## Phase 2 invariant

At the end of Phase 2:

> **A Neosis Ground request must execute through the actual Open Notebook engine while the user continues to interact with the Neosis API/product surface.**

## Workstream 1 — Workspace binding

Create an explicit binding between Neosis and Open Notebook.

Conceptually:

```text
Neosis workspace_id <----binding----> Open Notebook notebook_id
```

Do not use the same identifier merely to reduce code.

The binding must support:

- workspace ID,
- notebook ID,
- creation timestamp,
- synchronization state,
- last successful synchronization,
- failure metadata,
- optional upstream version/contract metadata.

Exact model/repository names must be discovered from the live project structure.

## Workstream 2 — Source binding

Bind:

```text
Neosis source_id
Neosis snapshot_id
        |
        v
Open Notebook source_id
```

Preserve the distinction between a canonical Neosis source/snapshot and its Open Notebook projection.

The binding must be idempotent.

The same checksum/snapshot should not create uncontrolled duplicate upstream sources.

## Workstream 3 — Source projection

The canonical Neosis source remains in S3.

When a source becomes eligible for Ground use, project the actual source file into Open Notebook through the real upstream `/sources` ingestion path or the exact endpoint verified in Phase 1.

Do not bypass native Open Notebook ingestion by sending only extracted text during the initial migration if doing so would bypass upstream parsing/processing behavior.

Target flow:

```text
User upload
   |
   v
Neosis source record
   |
   v
Neosis S3 snapshot
   |
   +------> existing Neosis ingestion/retrieval path
   |
   +------> Open Notebook source projection
                  |
                  v
          Open Notebook processing
                  |
                  v
           Open Notebook retrieval
```

The duplication is intentional during migration because the objective is exact Open Notebook behavior.

## Workstream 4 — Compatibility client

Create a thin internal integration package, conceptually:

```text
app/integrations/open_notebook/
    client.py
    config.py
    ground_engine.py
    chat_engine.py
    source_sync.py
    workspace_binding.py
    citation_mapper.py
    model_bridge.py
    schemas.py
    errors.py
    health.py
```

Exact names may change only when repository inspection establishes a better existing convention.

Responsibilities:

- HTTP calls to Open Notebook,
- request/response translation,
- timeout/error handling,
- source projection,
- binding lookup,
- Ground execution facade,
- chat facade,
- citation translation,
- health checking.

The compatibility layer must stay thin.

## Workstream 5 — Replace Ground orchestration with a facade

The existing `GroundModeOrchestrator` should no longer implement an independent RAG strategy.

The intended conceptual flow becomes:

```text
Neosis /ask
   |
   v
Auth + workspace validation
   |
   v
GroundModeOrchestrator facade
   |
   v
OpenNotebookGroundEngine
   |
   v
Open Notebook Ask/Search workflow
   |
   +--> strategy generation
   |
   +--> parallel searches
   |
   +--> native vector retrieval
   |
   +--> per-search synthesis
   |
   +--> final synthesis
   |
   v
citation/reference mapping
   |
   v
Neosis Ground response
```

Do not reproduce this workflow in Neosis merely because the architecture is visible.

Open Notebook remains responsible for its internal graph and prompts.

## Workstream 6 — Preserve Neosis API contract

Keep the existing user-facing Ground endpoint and request/response semantics where practical.

Conceptually:

```text
POST /api/v1/{workspace_id}/ask
```

or the exact current route discovered in the repository.

The API layer should remain thin:

- authenticate,
- validate workspace access,
- validate request,
- invoke Ground engine,
- map response,
- emit expected telemetry/SSE behavior.

Do not embed Open Notebook-specific logic into route handlers.

## Workstream 7 — Preserve Neosis memory/state boundaries

Open Notebook must not become the Neosis memory system.

Keep the six memory systems in Neosis:

1. Source Memory
2. Working Memory
3. Episodic Memory
4. Knowledge Memory
5. Research Memory
6. User/Workspace Memory

Keep the eight state domains in Neosis:

1. Workspace State
2. Research State
3. Plan State
4. Task State
5. Run State
6. Evidence State
7. Graph State
8. Version State

Do not inject all memory/state into Open Notebook prompts.

Instead, shared Neosis state is accessed through explicit adapters and persistence boundaries when required.

## Workstream 8 — Keep existing Neosis retrieval code available

`app/services/hybrid_retrieval.py` and the current Neosis document blocks must not be deleted in Phase 2.

They remain useful for:

- research mode retrieval,
- local evidence services,
- future evidence verification,
- migration comparison,
- fallback/shadow evaluation where needed.

They simply cease to be the active Ground execution engine after the cutover gate.

## Phase 2 tests

Minimum validation:

- workspace binding creation/reuse,
- source binding creation/reuse,
- source projection idempotency,
- source deletion behavior,
- source processing failure propagation,
- successful Ground request through Open Notebook,
- workspace isolation,
- cross-workspace negative tests,
- empty workspace behavior,
- multi-source Ground question,
- long-document question,
- citation/reference mapping,
- Open Notebook service unavailable behavior.

## Phase 2 exit gate

Phase 2 passes only when:

- every Ground workspace can resolve its Open Notebook notebook binding,
- uploaded sources can be projected through native Open Notebook ingestion,
- duplicate jobs do not create uncontrolled duplicate upstream objects,
- Ground requests execute through the actual Open Notebook workflow,
- the Neosis public Ground API remains stable or is deliberately versioned,
- no Open Notebook storage identifiers leak into the public contract,
- tenant isolation is proven,
- the old Ground backend is still available for comparison/fallback but is no longer the intended primary architecture.

---

# PHASE 3 — PROVENANCE, CHAT, RELIABILITY, OBSERVABILITY

## Phase objective

Harden the integration so that Open Notebook behaves like a production engine inside Neosis rather than a manually operated sidecar.

## Phase 3 invariant

At the end of Phase 3:

> **A Ground run is traceable, attributable, recoverable, tenant-safe, and explainable from Neosis without exposing Open Notebook internals to the user.**

## Workstream 1 — Citation and provenance mapping

The system must translate Open Notebook source/reference identifiers into Neosis canonical evidence references.

Target conceptual chain:

```text
Open Notebook answer/reference
          |
          v
citation mapper
          |
          v
Neosis source_id
Neosis snapshot_id
Neosis block/evidence locator where available
          |
          v
GroundAnswer.evidence / citations
```

Do not create a separate citation graph.

Provenance remains a data capability attached to sources, evidence, claims, memories, and research objects.

Do not expose SurrealDB object IDs as the product's canonical source IDs.

## Workstream 2 — Ground chat integration

If the Neosis product exposes persistent conversational Ground interaction, build a thin adapter around Open Notebook's native chat/session execution.

Conceptually:

```text
Neosis conversation_id <----binding----> Open Notebook session_id
```

Use the actual Open Notebook chat graph and checkpoint behavior.

Do not create a second Neosis-specific chat graph that duplicates the upstream graph.

The Neosis layer owns authentication, workspace scope, API contract, and persistence mapping.

## Workstream 3 — SSE and streaming

Preserve the existing Neosis job/event model.

Open Notebook streaming, where used, must be adapted to the Neosis API/SSE contract.

Users should not need to know whether an event came from:

- Neosis orchestration,
- Open Notebook,
- source projection,
- citation mapping,
- or background processing.

Internal telemetry may retain engine-specific spans/events.

## Workstream 4 — Reliability

Add explicit:

- connection timeouts,
- request timeouts,
- retries only for retryable failures,
- exponential backoff,
- idempotency keys,
- circuit breaking or equivalent protection where appropriate,
- duplicate suppression,
- job reconciliation,
- stale binding recovery,
- service health checks.

Never retry non-idempotent operations blindly.

## Workstream 5 — Failure taxonomy

At minimum distinguish:

```text
validation failure
workspace authorization failure
binding missing
source projection failure
Open Notebook unavailable
Open Notebook timeout
Open Notebook upstream processing failure
retrieval failure
citation mapping failure
model/provider failure
Neosis persistence failure
unknown/internal failure
```

Each failure must have a predictable public behavior and an internal telemetry representation.

## Workstream 6 — Security

Guarantee:

- workspace-scoped binding lookup,
- tenant-safe source projection,
- no cross-workspace notebook reuse,
- no cross-workspace source attachment,
- no API key leakage into prompts/logs,
- redacted error logs,
- internal-only Open Notebook service exposure,
- secure upstream credentials,
- safe object-store download handling.

## Workstream 7 — Observability

Instrument at least:

```text
Neosis request ID
workspace ID
run ID
source ID
snapshot ID
Open Notebook notebook ID
Open Notebook source ID
engine call latency
projection latency
processing latency
retrieval latency
LLM latency
error class
retry count
```

Open Notebook identifiers are internal telemetry attributes, not public user-facing identifiers.

## Workstream 8 — Operational reconciliation

Add background checks for:

- missing workspace bindings,
- missing source bindings,
- sources stuck in processing,
- upstream objects deleted unexpectedly,
- canonical source changed without projection,
- failed projection jobs,
- stale orphaned Open Notebook objects.

## Phase 3 tests

Minimum validation:

- citation round-trip test,
- citation completeness tests,
- chat session mapping tests,
- stream adaptation tests,
- retry tests,
- timeout tests,
- duplicate request tests,
- source projection replay tests,
- service outage recovery tests,
- tenant isolation tests,
- secret redaction tests,
- observability correlation tests,
- reconciliation job tests.

## Phase 3 exit gate

Phase 3 passes only when:

- Ground answers return Neosis-native provenance,
- chat works through the native upstream chat workflow where exposed,
- failures are classified and recoverable where appropriate,
- duplicate work is controlled,
- tenant isolation has automated coverage,
- operational telemetry is sufficient to trace a Ground request end to end,
- no Open Notebook internal identifier is required by the public frontend contract.

---

# PHASE 4 — EVALUATE, CUT OVER, DEPRECATE, OPERATIONALIZE

## Phase objective

Demonstrate that the integrated engine preserves or improves Ground behavior relative to the native upstream engine, then make Open Notebook the supported production Ground implementation and retire the custom Ground implementation from the active path.

## Phase 4 invariant

At the end of Phase 4:

> **Open Notebook is the supported Ground engine, Neosis remains the canonical product layer, and the old Ground implementation is no longer silently competing with it.**

## Workstream 1 — Three-way evaluation

Evaluate three systems:

```text
A. Existing Neosis Ground implementation
B. Standalone Open Notebook
C. Neosis + Open Notebook integration
```

Do not compare only A vs C.

B establishes the upstream behavioral baseline.

## Workstream 2 — Evaluation dimensions

At minimum measure:

- retrieval relevance,
- citation correctness,
- citation completeness,
- answer correctness,
- unsupported claim rate,
- source attribution accuracy,
- multi-document questions,
- multi-hop questions,
- long-document questions,
- noisy-source questions,
- empty-evidence questions,
- latency,
- failure rate,
- retry rate,
- duplicate projection rate.

Where possible, use deterministic datasets and regression fixtures.

## Workstream 3 — Integration parity gate

The integrated system should remain sufficiently close to standalone Open Notebook behavior for the capabilities intentionally delegated to Open Notebook.

Neosis integration must not introduce unexplained quality regressions through:

- incorrect source projection,
- truncated files,
- broken source binding,
- citation mapping loss,
- altered request semantics,
- unintended retrieval filtering,
- incorrect workspace scoping,
- model configuration mismatch.

Any regression must be traced to a concrete integration cause before cutover.

## Workstream 4 — Shadow comparison

Where practical, run the old Ground implementation and the new Ground engine against the same evaluation corpus and compare:

- retrieved evidence,
- final answer,
- citations,
- latency,
- errors.

This does not mean maintaining two production engines forever. It is a migration validation mechanism.

## Workstream 5 — Cutover

Once the evaluation gate passes:

1. Open Notebook becomes the primary Ground engine.
2. Existing Neosis Ground retrieval becomes non-primary.
3. Feature flags/rollbacks remain available for a controlled migration period.
4. New development must target the Open Notebook boundary, not the old custom Ground implementation.

## Workstream 6 — Deprecation

Deprecate, rather than immediately delete, the old Ground implementation.

Possible retained components include:

- `HybridRetrievalService`,
- document blocks,
- local vector/FTS retrieval,
- test fixtures,
- migration tools.

These can remain because they serve other architecture areas and future evaluation needs.

What should be retired is the concept that this path is the canonical production Ground engine.

## Workstream 7 — Documentation update

Update architecture documentation to state clearly:

```text
Ground Mode = Open Notebook execution substrate
Research Mode = separate research execution substrate
Neosis = canonical product, memory, state, provenance, workspace and graph fabric
```

Document:

- service topology,
- binding model,
- source projection lifecycle,
- failure behavior,
- deployment requirements,
- rollback process,
- evaluation results.

## Workstream 8 — Operational readiness

Document:

- how to start the stack,
- how to recover a failed Open Notebook service,
- how to rebuild a workspace projection,
- how to replay a source projection,
- how to repair stale bindings,
- how to inspect traces,
- how to rollback the Ground engine feature flag,
- how to upgrade the pinned upstream Open Notebook version.

Upstream upgrades must be treated as controlled migrations, not automatic dependency bumps.

## Phase 4 exit gate

Phase 4 passes only when:

- evaluation coverage exists,
- integrated behavior is understood relative to standalone Open Notebook,
- no unresolved major citation/provenance regression exists,
- tenant isolation passes,
- rollback is tested,
- Open Notebook is the active Ground engine,
- old Ground code is no longer part of the canonical request path,
- documentation reflects the actual architecture,
- the upstream commit/version is explicitly recorded,
- operations can reproduce and recover the system.

---

# 3. Hard Dependencies Between Phases

## Phase 1 → Phase 2

Required evidence:

- upstream Open Notebook boots,
- source processing verified,
- Ask/search verified,
- model configuration verified,
- upstream identifiers and API contracts inspected.

Without this, Phase 2 must not invent compatibility behavior.

## Phase 2 → Phase 3

Required evidence:

- workspace binding exists,
- source projection works,
- Ground requests successfully execute through Open Notebook,
- Neosis API response mapping works,
- tenant isolation is already proven at the basic integration level.

## Phase 3 → Phase 4

Required evidence:

- provenance works,
- retries/idempotency work,
- observability is complete enough for debugging,
- chat/streaming works where required,
- outage and recovery paths are tested.

---

# 4. What the Agent Must NOT Do During Any Phase

The following are explicit architecture violations:

1. Build a new Neosis RAG pipeline that reproduces Open Notebook retrieval.
2. Copy Open Notebook source-processing logic into `app/` instead of integrating the real code.
3. Rewrite the Open Notebook Ask graph in LangGraph under a new Neosis namespace.
4. Replace Open Notebook citation logic with an unrelated citation implementation merely because the output shape differs.
5. Put the Open Notebook database inside PostgreSQL solely to simplify integration.
6. Make `workspace_id == notebook_id`.
7. Treat Open Notebook as the canonical source store.
8. Inject the entire Neosis memory fabric into every Ground prompt.
9. Inject all eight Neosis state objects into Open Notebook's internal graph state.
10. Make every Ground interaction mutate the Research Output KG.
11. Add a second supervisor agent inside Ground.
12. Add STORM, GPT Researcher, or Open Deep Research as competing Ground orchestration layers.
13. Delete existing Neosis retrieval code before evaluation.
14. Change unrelated architecture components because they are “cleaner” after inspection.
15. Resolve missing implementation details by guessing.

---

# 5. Completion Definition

Chapter 2 is complete only when the following statement is true:

> NeosisLM presents one coherent product and public API. Ground Mode is executed by the actual pinned Open Notebook engine. Neosis retains canonical workspace/source ownership, shared memory and state, provenance, versioning, graph projection, tenant isolation, observability, and product contracts. Open Notebook-specific behavior is accessed through a thin, well-tested compatibility layer. The integration has passed regression/evaluation gates and the previous custom Ground path is no longer the active canonical implementation.

---

# 6. Recommended Agent Execution Order

```text
Read main Chapter 2 specification
        |
        v
Inspect live repository
        |
        v
Build implementation inventory
        |
        v
PHASE 1 — Acquire / Isolate / Boot
        |
        v
Phase 1 exit gate
        |
        v
PHASE 2 — Bind / Project / Replace Ground
        |
        v
Phase 2 exit gate
        |
        v
PHASE 3 — Provenance / Chat / Reliability / Observability
        |
        v
Phase 3 exit gate
        |
        v
PHASE 4 — Evaluate / Cut Over / Deprecate / Operationalize
        |
        v
Chapter 2 completion gate
```

At every stage the agent must use:

```text
inspect → implement → test → verify → document → continue
```

Never use:

```text
assume → rewrite → continue
```

---

# 7. Final Authority Rule

This file is a phase roadmap.

`NEOSISLM_CHAPTER_2_IMPLEMENTATION_SPEC.md` is the detailed architectural contract.

The live repository is the authority for exact current local code structure.

The pinned Open Notebook source is the authority for exact upstream implementation behavior.

Therefore:

```text
Architecture intent
        +
Live Neosis repository
        +
Pinned Open Notebook implementation
        |
        v
Actual implementation
```

Never replace those three sources with model-generated assumptions.
