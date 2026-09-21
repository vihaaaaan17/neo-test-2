# NeosisLM — Chapter 2 Implementation Specification
## Exact Open Notebook Ground Engine Migration + Canonical Neosis Integration

**Document status:** Implementation contract

**Target:** NeosisLM Chapter 2

**Date:** 2026-09-18

**Primary objective:** Replace the current custom Ground/RAG implementation with the actual Open Notebook implementation as the Ground engine, while preserving NeosisLM as the product-level system of record, workspace/memory/state/provenance layer, and public API boundary.

**Implementation unit:** Four phases. Each phase contains subphases, work packages, required invariants, tests, and exit criteria.

---

# 0. READ THIS BEFORE CHANGING CODE

This document is an implementation contract, not a brainstorming document.

The implementation agent must treat this file as the architectural target for Chapter 2. The objective is not to produce a superficially similar RAG system. The objective is to integrate the actual Open Notebook implementation into NeosisLM with the smallest viable compatibility layer.

The most important requirement is:

> **Reuse mature upstream behavior. Do not reimplement upstream behavior merely because it is possible to write a simpler local version.**

In particular, Chapter 2 must not replace Open Notebook's source processing, search/ask graph, vector retrieval, context construction, chat workflow, citation/source handling, model provisioning, prompt templates, or LangGraph orchestration with simplified Neosis-specific equivalents unless a concrete, documented incompatibility makes an adapter necessary.

The Neosis-specific work is the integration around the engine:

- workspace identity and tenant ownership,
- source/snapshot identity,
- object storage,
- source projection/binding,
- API compatibility,
- citation/provenance translation,
- run/job observability,
- memory/state persistence outside the engine,
- lifecycle and retry behavior,
- security and isolation,
- migration and regression evaluation.

The Open Notebook engine itself remains the implementation of Ground-mode notebook/RAG behavior.

---

# 1. MISSION OF CHAPTER 2

NeosisLM has two first-class user-visible modes:

1. **Ground Mode** — strict source-grounded interaction over a workspace's sources.
2. **Research Mode** — autonomous deep research over external information and the shared Neosis research fabric.

Chapter 2 is primarily the Ground Mode engine migration.

The target architecture is:

```text
                           NeosisLM
                              |
                +-------------+-------------+
                |                           |
             GROUND                      RESEARCH
                |                           |
                v                           v
      Open Notebook Engine         Future Research Engine
       (exact upstream)            (planned in later chapter)
                |
                v
       Neosis compatibility layer
                |
        +-------+-----------------------------+
        |                                     |
        v                                     v
  Neosis canonical data                 Neosis shared fabric
  PostgreSQL + S3                       memory/state/provenance
        |
        +------------------+
        |                  |
        v                  v
  Internal KG         Research Output KG
  operational         curated/user-facing
```

The right side of this diagram must not be accidentally pulled into Open Notebook internals.

Open Notebook is an execution substrate for Ground. It is not the owner of NeosisLM's canonical workspace model, six-memory taxonomy, eight-state taxonomy, Git-like version model, Internal KG, or Research Output KG.

---

# 2. SCOPE BOUNDARY

## 2.1 In scope

Chapter 2 must complete all of the following:

- acquire and pin the actual Open Notebook source code,
- run Open Notebook as an isolated internal Ground engine,
- provision its SurrealDB dependency,
- establish a stable Neosis-to-Open-Notebook compatibility boundary,
- bind a Neosis workspace to an Open Notebook notebook without equating their identifiers,
- project Neosis source files into Open Notebook using the actual upstream ingestion path,
- support Ground-mode search/ask through Open Notebook's real workflow,
- support Ground-mode chat through Open Notebook's real workflow where the product requires conversational interaction,
- translate Open Notebook references/citations back to Neosis source/snapshot evidence identifiers,
- preserve Neosis's canonical PostgreSQL/S3 records,
- maintain Neosis tenant isolation,
- maintain existing public Neosis endpoints unless a deliberate API migration is explicitly required,
- preserve existing SSE/job behavior at the Neosis boundary,
- add health checks, retries, idempotency, timeouts, observability, and failure semantics,
- add integration and regression tests,
- compare old Ground, standalone Open Notebook, and integrated Neosis+Open Notebook behavior,
- disable/retire the custom Ground backend only after evaluation passes,
- document the resulting architecture and operational behavior.

## 2.2 Explicitly out of scope for Chapter 2

Do not silently include the following because they are tempting extensions:

- rebuilding Open Notebook's web UI inside Neosis,
- rewriting Open Notebook's vector retrieval into `HybridRetrievalService`,
- moving Open Notebook internals into `app/` as if they were native Neosis modules,
- rewriting Open Notebook prompts,
- rewriting Open Notebook LangGraph workflows,
- replacing Open Notebook's ModelManager/Esperanto provider layer with LiteLLM during the initial migration,
- moving Open Notebook's database schema into Neosis PostgreSQL,
- making Open Notebook the canonical workspace database,
- exposing Open Notebook's SurrealDB IDs directly to users,
- replacing the Neosis six-memory architecture with Open Notebook notes/chat history,
- injecting all six memories into every Open Notebook prompt,
- injecting all eight Neosis state domains into Open Notebook's LangGraph state,
- making Ground answers automatically mutate the Research Output KG,
- creating a separate citation graph,
- redesigning Research Mode in the same implementation pass,
- adding STORM/GPT Researcher/Open Deep Research as competing supervisors inside Ground,
- deleting existing Neosis ingestion/retrieval code before benchmark evidence exists,
- making changes to unrelated product areas simply because the current architecture can be improved.

---

# 3. SOURCE-OF-TRUTH POLICY AND ANTI-DRIFT PROTOCOL

This section is mandatory.

The repository documentation and Graphify report describe the current NeosisLM architecture at file/class/service level. They do not expose every line of every current source file. Therefore this specification intentionally does **not** invent exact local function names where the evidence does not establish them.

The implementation agent must preserve the following rule:

> **When a detail is not explicitly established by the current repository, discover it from the repository before editing it. Never manufacture an exact function name, endpoint, constructor signature, import path, schema field, or dependency relationship from assumption.**

There are four evidence levels.

### Evidence Level A — Repository-verified

The exact current repository source has been inspected.

Examples:

- an actual route registration,
- an actual class definition,
- an actual constructor signature,
- an actual Docker Compose service,
- an actual migration,
- an actual test,
- an actual current import path.

Level A facts may be used to write exact code.

### Evidence Level B — Architecture-documented

The current Neosis architecture documents and Graphify report explicitly describe a file, class, model, relationship, or responsibility.

Examples include:

- `app/models/workspace.py`,
- `app/repositories/workspace.py`,
- `app/services/memory_router.py`,
- `app/services/hybrid_retrieval.py`,
- `app/workers/tasks.py`,
- `app/api/routes/workspaces.py`.

Level B facts establish intended architecture and dependency boundaries, but the agent must still inspect the actual source before coding against an exact symbol that was not exposed in the documentation.

### Evidence Level C — Upstream-verified

The implementation has been inspected in the actual upstream Open Notebook repository/documentation.

Examples:

- Open Notebook source processing workflow,
- Open Notebook Ask workflow,
- Open Notebook chat workflow,
- `/sources` ingestion path,
- search/ask routes,
- model provisioning,
- SurrealDB data model.

Level C facts may be used for integration design, but the agent must still pin and inspect the exact upstream commit used in the build.

### Evidence Level D — Inference/assumption

Any conclusion that is not directly supported by A, B, or C.

Level D content must not silently become implementation truth.

If Level D is required, the agent must first attempt repository/upstream discovery. If the detail remains unresolved, implement through an adapter or placeholder that isolates the uncertainty rather than distributing the assumption throughout the codebase.

---

# 4. THE DYNAMIC REPOSITORY-DISCOVERY RULE

The user explicitly requires this project to remain robust when the current repository differs from the architecture documentation.

The implementation agent must therefore perform a discovery pass before each phase and before modifying a file outside the already verified integration boundary.

The agent must follow this sequence:

```text
1. Locate the documented file.
2. Verify whether the file actually exists.
3. Inspect its current contents.
4. Identify current route/class/service names from source.
5. Identify callers and dependencies.
6. Identify existing tests.
7. Determine whether the documented responsibility still matches reality.
8. Only then patch the integration boundary.
```

If the documented file was renamed or moved, follow the actual repository structure rather than creating a duplicate just to match the documentation.

If the documented class was renamed, use the actual class name and update the architecture mapping document created in Chapter 2.

If an endpoint is different from the architecture documentation, preserve the live public endpoint unless a migration is explicitly part of the task.

For example, current documentation surfaces have referred to Ground endpoints using more than one route shape. This is exactly the kind of discrepancy that must be resolved by source inspection rather than guessed. The agent must inspect the actual FastAPI router registration and preserve the actual public contract.

The same rule applies to file upload endpoints, background job names, dependency injection functions, repository methods, and schema fields.

---

# 5. CURRENT NEOSIS ARCHITECTURAL BASELINE

The current documented NeosisLM stack is:

```text
FastAPI
  |
  +--> services
  |      |
  |      +--> repositories
  |      |
  |      +--> workers
  |
  +--> workers (Arq / Redis)
           |
           v
      repositories
           |
           v
     SQLAlchemy models
           |
           v
 PostgreSQL + pgvector
```

Supporting infrastructure:

- PostgreSQL = canonical source of truth for core Neosis domain data.
- S3-compatible object storage = immutable source blobs and exports.
- Redis + Arq = background work and event/pub-sub infrastructure.
- FastAPI = product API boundary.
- Neo4j = graph projection layer, not canonical source of truth.
- LiteLLM = Neosis provider-agnostic LLM gateway.
- Tavily = current web-search implementation behind an abstraction for Research Mode.

The current architecture is intentionally provider-abstracted. Chapter 2 should preserve that property at the Neosis boundary even though Open Notebook internally uses its own model/provider abstraction.

---

# 6. CURRENT MEMORY AND STATE CONTRACTS

NeosisLM has six logical memory systems:

1. Source Memory
2. Working Memory
3. Episodic Memory
4. Knowledge Memory
5. Research Memory
6. User/Workspace Memory

NeosisLM also has eight logical state systems:

1. Workspace State
2. Research State
3. Plan State
4. Task State
5. Run State
6. Evidence State
7. Graph State
8. Version State

These are product-level abstractions.

Open Notebook has its own internal workflow state and its own persistence/checkpoint behavior. That is acceptable.

Do not force an artificial one-to-one mapping such as:

```text
OpenNotebookThreadState == NeosisRunState
OpenNotebookNotebook == NeosisWorkspace
OpenNotebookChatSession == NeosisConversation
OpenNotebookSource == NeosisSource
```

The correct relationship is:

```text
Neosis canonical object
       |
       | adapter/binding/projection
       v
Open Notebook execution object
```

The distinction matters because one Open Notebook execution object may need to be recreated, migrated, or re-synchronized without changing the canonical Neosis identifier.

---

# 7. CURRENT NEOSIS MODE CONTRACTS

## Ground Mode

Ground Mode is strict source-grounded Q&A.

Required behavioral properties:

- no external web search,
- only workspace-approved source material,
- citations/provenance attached to evidence,
- explicit behavior when evidence is unavailable,
- no unsupported factual answer presented as source-grounded,
- workspace-scoped retrieval,
- user-visible answer should not expose Open Notebook internal IDs.

The current implementation uses a custom Ground pipeline and `HybridRetrievalService`. That pipeline is the backend being replaced, not the product contract itself.

## Research Mode

Research Mode remains a separate system.

It is allowed to use external research tools and will later use the shared memory/state/provenance fabric.

Do not merge Research Mode and Ground Mode into one generic supervisor during Chapter 2.

---

# 8. CURRENT NEOSIS MODEL BASELINE

The current model report documents these important entities:

### Workspace

`app/models/workspace.py`

Key documented fields include:

- `workspace_id`
- `owner_id`
- `status`
- `active_commit_id`
- timestamps

### WorkspaceCommit

`app/models/workspace.py`

Key documented fields include:

- `commit_id`
- `parent_id`
- `workspace_id`
- `active_knowledge_ids`
- `created_at`

### Source

`app/models/source.py`

Key documented fields include:

- `source_id`
- `workspace_id`
- `owner_id`
- `source_type`
- `processing_status`
- timestamps

### SourceSnapshot

Documented as a versioned source representation with fields including:

- `snapshot_id`
- `source_id`
- `file_uri`
- `filename`
- `size`
- `checksum_sha256`
- `created_at`

### DocumentBlock

`app/models/block.py`

Documented as the internal parsed/chunked retrieval unit with:

- `block_id`
- `source_id`
- `snapshot_id`
- `block_type`
- `sequence`
- `text_or_ref`
- `page_number`
- `metadata_`
- vector embedding
- PostgreSQL full-text search representation

### KnowledgeMemory

`app/models/knowledge.py`

Documented as canonical semantic knowledge with provenance, confidence, versioning, and workspace ownership.

### EpisodicMemory

`app/models/episodic.py`

Documented as important past event summaries connected to runs/tasks.

These documented contracts are important because the Open Notebook migration must not erase or replace the existing Neosis source identity and history model.

---

# 9. CURRENT HIGH-CONNECTIVITY FILES — HANDLE CAREFULLY

Graphify identifies several high-connectivity components:

- `Workspace` in `app/models/workspace.py`
- `app/api/routes/workspaces.py`
- `WorkspaceRepository` in `app/repositories/workspace.py`
- `MemoryRouter` in `app/services/memory_router.py`
- `app/workers/tasks.py`

The graph analysis also groups the current system into communities around persistence/models, workspace management, hybrid search/LLM gateway, memory routing, and worker/storage operations.

These components are already architectural backbones.

### Mandatory rule

Do not turn Chapter 2 into a reason to embed Open Notebook-specific business logic directly inside these high-connectivity nodes.

Especially do not:

- add SurrealDB queries to `Workspace`,
- add Open Notebook model assumptions to `WorkspaceRepository`,
- put Open Notebook orchestration logic into `workspaces.py`,
- make `MemoryRouter` know about Open Notebook internals,
- make `workers/tasks.py` contain the entire Open Notebook integration implementation.

Instead, use thin integration modules and have the high-connectivity components call them through narrow interfaces.

---

# 10. TARGET BOUNDARY: OPEN NOTEBOOK AS AN INTERNAL GROUND ENGINE

The target is an isolated subsystem.

Recommended repository boundary:

```text
third_party/
  open-notebook/
    <pinned upstream source>
```

or an equivalent clearly isolated vendor directory if the project already uses a different third-party convention.

Recommended Neosis adapter boundary:

```text
app/
  integrations/
    open_notebook/
      __init__.py
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

Do not assume this exact directory is present. Inspect the repository and use the closest existing integration convention. The responsibilities listed here are more important than the literal filenames.

The adapter layer has six categories of responsibility:

1. Transport
2. Binding
3. Projection
4. Translation
5. Lifecycle
6. Observability

It must not become a second Ground engine.

---

# 11. UPSTREAM OPEN NOTEBOOK FACTS USED BY THIS CHAPTER

The current Open Notebook architecture documentation shows:

- Next.js frontend,
- FastAPI backend,
- SurrealDB database,
- LangGraph workflows,
- source processing workflow,
- chat workflow,
- Ask/search workflow,
- transformations/prompt workflows,
- centralized model management/provider provisioning.

The source workflow performs actual extraction/processing, embedding creation, persistence, and topic/insight-related processing.

The Ask workflow plans searches, performs retrieval, produces per-search answers, and synthesizes a final answer.

The chat workflow maintains a conversation state, builds context, invokes a model, streams responses, and persists conversation state/checkpoint behavior.

Open Notebook's current API exposes source ingestion under `/sources` and search/ask functionality through its search routes. The exact request/response schemas must be taken from the pinned upstream commit used by the project rather than copied from a different version.

Open Notebook currently uses SurrealDB for its own persistence and has its own model/provider management. The initial Chapter 2 migration should preserve those internals rather than immediately replace them.

The Open Notebook architecture documentation is the basis for integration design. The exact pinned commit used in implementation is the runtime truth.

---

# 12. WHY THE SIDECAR/ISOLATION BOUNDARY IS REQUIRED

Open Notebook and NeosisLM have different canonical models.

Neosis:

```text
Workspace
  Source
    SourceSnapshot
      DocumentBlock
  KnowledgeMemory
  EpisodicMemory
  ResearchMemory
  State
  Version
```

Open Notebook:

```text
Notebook
  Source
    SourceEmbedding
  Note
  ChatSession
  Transformation
  SourceInsight
  Relationships
```

Trying to merge these schemas in the first migration would cause two bad outcomes:

1. the upstream engine would need to be rewritten to obey Neosis-specific schemas,
2. the Neosis domain model would become coupled to a third-party implementation.

Both defeat the purpose of using the mature upstream implementation.

Therefore:

> Neosis is the product system of record. Open Notebook is the Ground execution substrate/read model.

---

# 13. CORE IDENTIFIER RULES

Never assume identifiers across systems are interchangeable.

Mandatory mapping:

```text
Neosis workspace_id       <-> Open Notebook notebook_id
Neosis source_id          <-> Open Notebook source_id
Neosis snapshot_id        <-> projected source version/checksum
Neosis conversation_id    <-> Open Notebook chat session identifier
Neosis run_id             <-> Open Notebook execution metadata, when applicable
Neosis evidence reference <-> Open Notebook source/chunk/reference metadata
```

Do not use:

```text
workspace_id == notebook_id
source_id == OpenNotebookSourceId
conversation_id == chat_session_id
```

unless the actual identifier systems independently guarantee that identity relationship, which they currently do not.

The mapping must be explicit and persisted.

---

# 14. REQUIRED BINDING MODEL / MAPPING RECORD

Create an explicit mapping entity through the existing model/repository conventions.

The exact filename must follow the current repository structure. A likely responsibility boundary is:

```text
models/open_notebook_binding.py
repositories/open_notebook.py
```

The binding should contain enough information to answer:

- which Neosis workspace is bound,
- which Open Notebook notebook represents it,
- what Open Notebook service/version is in use,
- which source projection corresponds to each Neosis source/snapshot,
- checksum/version information,
- projection status,
- last successful synchronization,
- last failure/error information where operationally useful,
- schema/mapping version.

Do not create a huge rigid schema. Use minimal mandatory system fields plus controlled metadata.

Recommended mandatory concepts:

```text
binding_id
workspace_id
open_notebook_notebook_id
mapping_version
status
created_at
updated_at
```

For source mapping:

```text
workspace_id
neosis_source_id
neosis_snapshot_id
open_notebook_source_id
checksum_sha256
projection_status
last_synced_at
```

The exact field names must follow actual project conventions after repository inspection.

---

# 15. SOURCE PROJECTION STRATEGY

This is one of the most important decisions in Chapter 2.

When a source exists in Neosis:

```text
User upload
    |
    v
Neosis API
    |
    v
S3 immutable blob
    |
    v
Neosis Source + SourceSnapshot
    |
    v
Projection job
    |
    v
Open Notebook /sources upload
    |
    v
Open Notebook source processing graph
    |
    v
Open Notebook embeddings/index
```

The initial migration must upload the actual source file into Open Notebook's normal source-ingestion pathway.

Do not initially pass only the already-extracted Neosis text unless the upstream API truly requires only text for a given source type.

The reason is architectural fidelity. Passing only Neosis-extracted text would bypass the very Open Notebook processing behavior that the migration is intended to reuse.

The temporary duplication is intentional:

```text
Neosis canonical source representation
        +
Open Notebook execution representation
```

The projection is derived and rebuildable.

If the Open Notebook projection is corrupted, the projection can be removed and recreated from the Neosis source snapshot.

---

# 16. SOURCE PROJECTION MUST BE IDEMPOTENT

The projection process must not create duplicate Open Notebook sources every time a worker retries.

The canonical idempotency input should be based on stable Neosis identity and content version, for example:

```text
(workspace_id, source_id, snapshot_id, checksum_sha256)
```

Do not use timestamps as the primary idempotency key.

Required behavior:

```text
same Neosis snapshot + same checksum
        -> no duplicate projection
        -> existing binding reused

new snapshot/checksum
        -> new projection or controlled replacement
        -> prior projection remains traceable
```

The exact replacement semantics depend on the real Open Notebook source lifecycle. Inspect upstream APIs before deciding whether to update, archive, or create a new source representation.

Never delete the Neosis source snapshot merely because a projection fails.

---

# 17. OPEN NOTEBOOK WORKSPACE BINDING

When a Neosis workspace is first used in Ground Mode:

1. verify workspace ownership and tenant access,
2. look up the Open Notebook binding,
3. create the Open Notebook notebook if no binding exists,
4. persist the binding,
5. ensure required sources are projected,
6. execute Ground against the mapped notebook.

The creation path must be race-safe.

Two concurrent requests must not create two Open Notebook notebooks for one Neosis workspace.

Use one of the repository's existing concurrency/transaction approaches, preferably an existing unique constraint plus retry or lock strategy.

Do not implement ad hoc in-memory locks for a multi-worker deployment.

---

# 18. GROUND ENGINE FACADE

The existing Neosis Ground orchestrator should become a product-level facade.

Current architecture documentation describes:

```text
GroundModeOrchestrator
    -> HybridRetrievalService
    -> grounded answer
```

The new architecture is:

```text
GroundModeOrchestrator / Ground service facade
    -> OpenNotebookGroundEngine
        -> OpenNotebookClient
            -> Open Notebook Ask/Search API
                -> actual upstream Ask LangGraph
                    -> upstream retrieval
                    -> upstream answer synthesis
```

The facade must continue to enforce Neosis product-level concerns:

- workspace authorization,
- mode selection,
- source availability,
- timeout/budget policy,
- run identifiers,
- telemetry,
- error translation,
- provenance translation.

It must not reproduce Open Notebook's internal search strategy.

---

# 19. THE NEW GROUND ENGINE CONTRACT

The engine-neutral Neosis contract should describe the result, not the implementation details.

Conceptually:

```text
GroundRequest
  workspace_id
  conversation_id (optional)
  query
  model override (optional, if already supported)
  execution policy

GroundResponse
  answer
  evidence[]
  citations[]
  source references[]
  engine metadata
  run metadata
  warnings/errors where required
```

The actual Pydantic schema names and fields must be taken from the current repository.

The compatibility layer should translate:

```text
Neosis request
    -> Open Notebook request

Open Notebook response
    -> canonical Neosis response
```

Do not expose raw upstream response shape to the public API unless the public API already intentionally mirrors it.

---

# 20. ASK WORKFLOW: DO NOT REIMPLEMENT

The Open Notebook Ask workflow is part of the implementation to reuse.

Conceptually, its current behavior is:

```text
Question
  |
  v
Strategy generation
  |
  +--> Search 1 -> retrieval -> answer
  +--> Search 2 -> retrieval -> answer
  +--> Search N -> retrieval -> answer
  |
  v
Final synthesis
  |
  v
Answer
```

This parallel search structure is a feature, not accidental complexity.

Do not replace it with:

```text
query -> single vector search -> one prompt
```

inside the Neosis Ground adapter.

Do not copy the upstream prompt into a Neosis prompt file and call that an integration.

The upstream graph itself should execute.

---

# 21. CHAT WORKFLOW: DO NOT REIMPLEMENT

Ground Mode may require a conversational chat path in addition to one-shot Ask.

Where the product UI requires conversation persistence, the adapter should map:

```text
Neosis conversation_id
        -> Open Notebook chat session id
```

and call the upstream Open Notebook chat endpoints/workflow.

The Neosis layer owns:

- workspace/user authorization,
- the mapping,
- external API contract,
- product-level conversation identity.

Open Notebook owns:

- its chat graph,
- context construction,
- message execution,
- model invocation,
- its internal checkpoint/session persistence.

Do not create a parallel Neosis LangGraph chat implementation just to avoid calling the upstream one.

---

# 22. MODEL PROVIDER STRATEGY FOR INITIAL MIGRATION

Neosis currently intends to be provider-agnostic through LiteLLM.

Open Notebook currently has its own provider/model management layer.

Chapter 2 intentionally does not force an immediate provider rewrite.

Initial target:

```text
Neosis API
    |
    v
Open Notebook Ground engine
    |
    v
Open Notebook ModelManager / provider layer
```

Later target:

```text
Neosis API
    |
    v
Open Notebook Ground engine
    |
    v
compatibility model bridge
    |
    v
Neosis LLM Gateway / LiteLLM
```

The bridge must only be introduced after the exact upstream engine is proven integrated.

Do not modify dozens of upstream files simply to make every model call go through LiteLLM during this chapter.

The migration priority is behavior preservation first, unification second.

---

# 23. MODEL OVERRIDE POLICY

Open Notebook supports model configuration/overrides through its own execution path.

Neosis may expose a model override at the product level.

The adapter must translate product-level model selection only where the upstream API supports the equivalent capability.

Do not invent unsupported per-request model semantics.

If a Neosis model identifier cannot be represented by Open Notebook directly, the adapter must return a controlled compatibility error rather than silently selecting a different model.

Later, the model bridge can translate:

```text
Neosis logical model
  -> LiteLLM provider/model
  -> Open Notebook model configuration
```

but that belongs to the later compatibility stage.

---

# 24. MEMORY INTEGRATION RULE

The six Neosis memories remain outside Open Notebook.

Correct pattern:

```text
Ground request
   |
   +--> MemoryRouter determines whether Neosis memory should be accessed
   |
   +--> Open Notebook handles source-grounded execution
   |
   +--> result/evidence is returned
   |
   +--> Neosis records relevant episode/provenance/state
```

Incorrect pattern:

```text
Serialize all six memories
        |
        v
Insert them into Open Notebook system prompt
```

The second pattern causes prompt pollution, unclear provenance, leakage across concerns, and tight coupling.

Memory is a persistence/routing subsystem, not a giant prompt string.

---

# 25. WORKING MEMORY AND SCRATCHPAD RULE

Neosis Working Memory remains product-owned.

Neosis Scratchpad, when implemented or already present, remains product-owned.

A user-created scratchpad item must not automatically become an Open Notebook source merely because it is text.

The only automatic projection into Open Notebook should be source material explicitly designated as Ground-visible source content.

Later, a user-selected note/scratchpad projection may be added. That is a separate capability.

---

# 26. SOURCE-OF-TRUTH RULE

For Chapter 2:

```text
PostgreSQL = canonical Neosis domain truth
S3 = canonical immutable source blobs
Open Notebook SurrealDB = derived Ground engine/read-model/execution state
Neo4j = graph projection
Redis = ephemeral queue/pubsub/cache infrastructure
```

If a conflict exists:

```text
Neosis canonical source metadata
      wins over
Open Notebook projection metadata
```

provided that the field is genuinely owned by Neosis.

If a field is Open Notebook-internal, it belongs to Open Notebook.

Do not copy every Open Notebook field into PostgreSQL just because it exists.

---

# 27. CITATION AND PROVENANCE DESIGN

NeosisLM should not create a third graph just for citations.

Citation/provenance is a cross-cutting data capability.

The adapter must translate Open Notebook source/evidence references into Neosis evidence references.

Desired conceptual mapping:

```text
Open Notebook source
Open Notebook embedding/chunk/reference
        |
        v
citation mapper
        |
        v
Neosis source_id
Neosis snapshot_id
Neosis document/block locator where resolvable
source checksum
page/section/offset metadata where available
```

The user-visible citation should point back to a Neosis source identity, not a SurrealDB record ID.

Do not claim a finer locator than the underlying evidence actually supports.

For example:

```text
page known -> expose page
page unknown -> do not invent page
block known -> expose block reference
block unknown -> expose source-level provenance
```

Every citation emitted by the Ground result must be traceable.

---

# 28. CITATION MAPPER FAILURE POLICY

Citation translation is a high-integrity boundary.

If Open Notebook returns an evidence reference that cannot be resolved to a Neosis canonical source:

- do not fabricate a Neosis ID,
- do not silently drop all provenance,
- do not present the reference as a canonical Neosis citation,
- record a diagnostic event,
- return a safe fallback reference shape if the product contract supports it,
- fail the citation-correctness test.

The answer itself may still be returned depending on product policy, but the system must make the provenance degradation observable.

---

# 29. RESEARCH OUTPUT KG RULE

A Ground answer must not automatically become a Research Output KG update.

Ground is primarily evidence retrieval and response.

Research Output KG changes are driven by Research Mode or explicit user actions that intentionally promote knowledge into research artifacts.

Open Notebook source retrieval should therefore not be wired directly into graph mutation.

Correct:

```text
Ground answer -> evidence -> response
```

Incorrect:

```text
Ground answer -> create graph nodes/edges automatically
```

---

# 30. INTERNAL KG RULE

The Internal KG can represent operational relationships, evidence lineage, source projections, research run events, and other machine-useful relationships.

However, Chapter 2 does not require every Open Notebook internal relationship to be copied into the Internal KG.

Only relationships needed for canonical provenance, synchronization, operational visibility, or later research integration should cross the boundary.

Do not create graph-edge explosion for every internal Open Notebook event.

---

# 31. TEMPORAL / SNAPSHOT RULE

Neosis source identity and source snapshot identity are important because Ground must be reproducible against a known source version.

The projection layer must preserve the distinction:

```text
Source identity = logical document/source
Snapshot = exact source version/content
Projection = current or historical Open Notebook representation
```

At minimum, the binding must preserve the checksum of the projected snapshot.

If a source changes, the system must not silently treat an old Open Notebook representation as the latest Neosis source unless the checksum matches the active source snapshot.

---

# 32. API PRESERVATION RULE

The existing Neosis public API is part of the product contract.

The migration should not expose Open Notebook directly to the frontend.

The frontend should continue calling the Neosis API.

Example target flow:

```text
Browser
  |
  v
Neosis FastAPI
  |
  v
Ground facade
  |
  v
Open Notebook internal API
```

Do not make the frontend call:

```text
Browser -> Open Notebook :5055
```

as the product integration.

Open Notebook must remain an internal service.

---

# 33. SSE / STREAMING RULE

If Neosis already exposes SSE for jobs or Ground responses, preserve that behavior at the Neosis boundary.

Where Open Notebook streams internally, translate its events to the existing Neosis stream protocol rather than exposing raw Open Notebook event names unless those names are already part of the public contract.

The frontend must not need to understand which engine executed Ground.

---

# 34. ERROR TRANSLATION RULE

Create a narrow error mapping layer.

Conceptual categories:

```text
WorkspaceNotFound
WorkspaceUnauthorized
GroundEngineUnavailable
GroundEngineTimeout
SourceProjectionPending
SourceProjectionFailed
CitationMappingFailed
UpstreamInvalidRequest
UpstreamRateLimited
UpstreamModelError
GroundExecutionFailed
```

The actual exception hierarchy must follow existing Neosis conventions.

The adapter must not leak arbitrary stack traces or SurrealDB connection errors through the public API.

Log the detailed upstream exception with correlation identifiers, then return a stable Neosis error contract.

---

# 35. TIMEOUT POLICY

Every network boundary must have an explicit timeout.

At minimum:

```text
Neosis -> Open Notebook API timeout
Open Notebook -> SurrealDB timeout
Open Notebook -> LLM timeout
Neosis source projection upload timeout
source processing job timeout
```

Do not rely on infinite HTTP or worker waits.

The timeout values must be configurable rather than hardcoded throughout the code.

A timeout must produce a recoverable run state, not a permanently ambiguous source state.

---

# 36. RETRY POLICY

Retries must be selective.

Safe to retry when the operation is:

- network transient,
- provider temporary unavailable,
- job delivery failure,
- read-only health operation,
- idempotent projection with a stable key.

Do not blindly retry when the operation may create a duplicate source, notebook, chat session, or database mutation without an idempotency key.

Use exponential backoff where the existing platform conventions support it.

Persist enough state to know whether a projection was already successful.

---

# 37. DOCKER / SERVICE TOPOLOGY

Add Open Notebook as an internal service in the development deployment.

Conceptual topology:

```text
+--------------------------------------------------+
| Neosis deployment                                |
|                                                  |
|  FastAPI                                         |
|     |                                            |
|     +--> PostgreSQL                              |
|     +--> Redis                                   |
|     +--> S3-compatible object store             |
|     +--> Neo4j                                  |
|     +--> Open Notebook API ----------------+     |
|                                           |     |
|                                      SurrealDB   |
|                                                  |
+--------------------------------------------------+
```

Open Notebook frontend is not required for the Neosis backend integration and should not be exposed unless needed for a dedicated development/debug setup.

The Open Notebook API and SurrealDB should be internal-network-only from the product's perspective.

Do not expose SurrealDB publicly.

---

# 38. CONFIGURATION BOUNDARY

Open Notebook configuration belongs under a clearly namespaced configuration section.

Conceptual examples:

```text
OPEN_NOTEBOOK_BASE_URL
OPEN_NOTEBOOK_TIMEOUT_SECONDS
OPEN_NOTEBOOK_API_KEY / AUTH CONFIG if required
OPEN_NOTEBOOK_ENABLED
OPEN_NOTEBOOK_DEFAULT_NOTEBOOK_POLICY
OPEN_NOTEBOOK_PROJECTION_BUCKET/PATH if needed
OPEN_NOTEBOOK_HEALTHCHECK_TIMEOUT
```

Do not hardcode localhost URLs inside services.

Do not place secrets in source code, logs, prompts, state payloads, graph nodes, or citations.

Use the existing Neosis configuration/secrets conventions.

---

# 39. HEALTH CHECKS

The integration must support a health check with distinct signals.

At minimum:

```text
Neosis API healthy
Open Notebook API reachable
Open Notebook SurrealDB reachable
Open Notebook source API functional
Open Notebook ask/search path functional
```

A service-level health endpoint may report:

```text
healthy

degraded

unavailable
```

Do not report the entire Neosis system as healthy merely because the FastAPI process is alive if Ground Mode depends on an unavailable Open Notebook service.

---

# 40. OBSERVABILITY

Every Ground execution must have a Neosis correlation/run identifier.

Recommended trace chain:

```text
request_id
   |
   +-- ground_run_id
         |
         +-- workspace_id
         +-- conversation_id
         +-- OpenNotebook notebook_id
         +-- OpenNotebook execution/session id
         +-- source projection ids
         +-- model/provider metadata where allowed
```

Do not log source contents or secret keys merely for debugging.

Do not log full prompts unless the project's security policy explicitly allows controlled prompt logging.

Operational telemetry should capture:

- latency,
- retrieval/search count if available,
- source projection latency,
- failures,
- timeout count,
- upstream status codes,
- citation translation success rate,
- Ground answer completion rate.

---

# 41. SECURITY BOUNDARY

The Ground system is tenant-sensitive.

Every request must begin with:

```text
authenticated actor
        |
        v
workspace authorization
        |
        v
source eligibility
        |
        v
Open Notebook binding
```

Do not trust an Open Notebook notebook_id supplied by the client.

The client should provide a Neosis workspace identifier, not an arbitrary upstream notebook identifier.

The server resolves:

```text
workspace_id -> binding -> notebook_id
```

This prevents notebook-level cross-tenant confusion.

Secrets must never enter:

- prompts,
- LangGraph state intended for model context,
- source content,
- graph node properties,
- citations,
- regular application logs.

---

# 42. PROMPT-INJECTION BOUNDARY

Open Notebook source material is untrusted content from the user's files or external source ingestion.

The integration must not treat document text as trusted instructions to Neosis itself.

Open Notebook handles the actual Ground prompting/retrieval logic, but Neosis must ensure that product-level system instructions, authorization, and routing decisions are not derived from source content.

Do not allow document text to redefine:

- workspace authorization,
- tool permissions,
- API endpoints,
- secret access,
- model configuration,
- graph write policies.

Do not create a custom prompt “security patch” in the adapter unless there is a concrete verified issue; first identify the actual upstream prompt boundary.

---

# 43. PHASE PLAN OVERVIEW

Chapter 2 consists of exactly four implementation phases.

```text
PHASE 1
Acquire + Isolate + Boot

        |
        v
PHASE 2
Bind + Project + Replace Ground

        |
        v
PHASE 3
Provenance + Chat + Reliability + Observability

        |
        v
PHASE 4
Evaluate + Cut Over + Deprecate + Operationalize
```

No phase should be considered complete merely because the code compiles.

Each phase has a hard exit gate.

---

# 44. PHASE 1 — ACQUIRE, ISOLATE, BOOT

## Phase objective

Bring the exact upstream Open Notebook implementation into the Neosis development environment without coupling it to Neosis internals.

## Phase 1 invariant

At the end of Phase 1:

```text
Open Notebook must run independently.
Neosis must still run independently.
Neither implementation may have been reimplemented into the other.
```

## 44.1 Step 1 — Inspect the actual repository

Before coding, inspect:

- root structure,
- current `pyproject`/requirements system,
- Docker Compose/deployment files,
- existing third-party/vendor conventions,
- current FastAPI lifespan,
- current worker startup,
- existing test conventions,
- existing integration package conventions.

Record actual file paths.

If the docs and repository disagree, repository source wins for literal paths and symbols.

## 44.2 Step 2 — Pin upstream Open Notebook

Acquire the actual upstream Open Notebook repository.

Do not use an unspecified floating branch as the only dependency for a reproducible build.

Record:

```text
repository URL
commit SHA
retrieval date
license
local path
patch status
```

The exact commit must be resolved during implementation and recorded. Do not fabricate a SHA in this specification.

## 44.3 Step 3 — Keep upstream code intact

Preferred structure:

```text
third_party/open-notebook/
```

Do not immediately scatter copied Open Notebook modules through `app/`.

If a change to upstream code is unavoidable, place it in a documented patch or fork workflow with a clear reason.

The default assumption is that upstream files are read-only from Neosis business logic.

## 44.4 Step 4 — Start Open Notebook standalone

Bring up:

- Open Notebook API,
- Open Notebook SurrealDB,
- required upstream runtime dependencies.

Verify:

- health/API readiness,
- source creation/upload,
- source processing,
- search/ask,
- chat if required,
- database persistence,
- streaming where supported.

Do this before integrating a single Neosis endpoint.

## 44.5 Step 5 — Establish local smoke corpus

Create a tiny test corpus representing:

- one short PDF,
- one multi-page document,
- one text/markdown source,
- one source containing repeated terms,
- one source where the answer is absent.

Record expected facts and expected provenance locations.

This corpus becomes the first regression fixture set.

## 44.6 Step 6 — Add service boundary

Add the Open Notebook service to the development deployment.

Verify that Neosis can resolve its configured base URL.

Do not yet route user Ground traffic through it.

## Phase 1 files/components expected

Exact paths are repository-dependent, but responsibilities should include:

```text
third_party/open-notebook/

docker-compose / deployment config

app/integrations/open_notebook/
    config
    client
    health
```

## Phase 1 tests

```text
Open Notebook standalone health test
Open Notebook standalone source ingestion test
Open Notebook standalone ask/search test
Open Notebook standalone chat smoke test if chat is required
Neosis -> Open Notebook network connectivity test
Configuration loading test
Secret isolation test
```

## Phase 1 exit gate

Phase 1 passes only when:

- exact upstream code is pinned,
- upstream service runs independently,
- SurrealDB is healthy,
- at least one source can be ingested through the real Open Notebook endpoint,
- at least one Ask query succeeds through the real Ask workflow,
- the integration client can reach the service,
- no custom Neosis Ground code was copied into the Open Notebook runtime,
- no public Ground traffic has been switched prematurely.

---

# 45. PHASE 2 — BIND, PROJECT, REPLACE GROUND

## Phase objective

Connect Neosis workspaces and sources to Open Notebook and make Open Notebook the actual Ground engine.

## Phase 2 invariant

Neosis remains the product boundary.

Open Notebook becomes the implementation behind that boundary.

## 45.1 Step 1 — Implement workspace binding

Add the explicit mapping record described earlier.

Required behavior:

```text
get_or_create_open_notebook_binding(workspace)
```

The exact method name is not prescribed. Inspect existing repository/service conventions.

Required semantics:

- authorization before resolution,
- idempotent creation,
- persisted mapping,
- no client-provided notebook identity,
- deterministic recovery after process restart.

## 45.2 Step 2 — Implement source binding

For each source snapshot intended for Ground:

1. load the canonical Neosis source/snapshot,
2. verify workspace ownership,
3. verify blob exists,
4. compute/validate checksum,
5. check existing projection binding,
6. upload the actual file through Open Notebook's source API if missing,
7. wait/poll/observe processing status according to upstream behavior,
8. persist projection result,
9. expose projection status to Neosis.

Do not delete canonical Neosis state on projection failure.

## 45.3 Step 3 — Use a worker for projection

Source projection is potentially expensive and must not block the main upload request unnecessarily.

Use the existing Neosis background job system.

The job should be conceptually:

```text
project source snapshot -> Open Notebook
```

Possible job responsibilities:

- upload,
- processing status tracking,
- retry,
- binding update,
- telemetry.

Keep the worker job thin. Put substantive Open Notebook interaction inside the integration service/module, not as dozens of lines inside the central worker registry.

## 45.4 Step 4 — Preserve source lifecycle semantics

Neosis source states and Open Notebook source processing states are different state machines.

The adapter must translate them rather than collapse them.

Conceptual mapping:

```text
Neosis source: pending
   -> projection: pending

Neosis source: processing
   -> projection: uploading/processing

Neosis source: completed
   -> projection: ready

Neosis source: failed
   -> projection: failed / retryable
```

The exact upstream statuses must be discovered from the pinned implementation.

## 45.5 Step 5 — Replace Ground backend through facade

The current Ground orchestrator/service must stop directly invoking the custom `HybridRetrievalService` for the primary Ground execution path.

New path:

```text
Existing Neosis Ground API
    |
    v
existing auth / workspace validation
    |
    v
Ground facade
    |
    v
OpenNotebookGroundEngine
    |
    v
OpenNotebookClient
    |
    v
Open Notebook Ask/Search endpoint
```

Do not change the frontend contract just to make this easier.

## 45.6 Step 6 — Keep old Ground backend available for comparison

Do not delete `HybridRetrievalService` yet.

Retain it as:

- legacy path,
- benchmark baseline,
- potential fallback during migration if product policy permits.

Whether a runtime fallback is enabled should be explicit and observable; it must not silently switch engines without recording the event.

## 45.7 Step 7 — Translate the response

The adapter converts the upstream response into the existing Neosis Ground response schema.

Required output concepts:

- answer,
- evidence,
- citations,
- source identifiers,
- provenance metadata,
- run/execution metadata if the public schema supports it.

Do not expose raw SurrealDB record IDs as the product's canonical references.

## 45.8 Step 8 — Add request-level telemetry

Every request should produce:

```text
Neosis request id
Ground run id
workspace id
binding id
Open Notebook notebook id
upstream request id if available
latency
status
```

## Phase 2 tests

At minimum:

```text
workspace binding creation
workspace binding idempotency
workspace tenant isolation
source projection creation
source projection idempotency
source projection retry
source projection checksum change
Ground request routed to Open Notebook
Ground answer translated to Neosis schema
no Open Notebook internal ID leakage
Ground does not invoke external web search
legacy Ground path still works in isolated benchmark mode
```

## Phase 2 exit gate

Phase 2 passes only when:

- a real Neosis workspace is mapped to one Open Notebook notebook,
- a real Neosis source snapshot is projected through the upstream source API,
- the upstream source workflow processes it,
- the existing Neosis Ground endpoint executes against the Open Notebook Ask workflow,
- the response is translated to the Neosis contract,
- workspace isolation is verified,
- duplicate projections are prevented,
- no custom RAG graph has been rebuilt inside Neosis.

---

# 46. PHASE 3 — PROVENANCE, CHAT, RELIABILITY, OBSERVABILITY

## Phase objective

Move from “it works” to “it is a controlled product subsystem.”

## Phase 3 invariant

Every Ground answer must be traceable, recoverable, observable, and tenant-safe.

## 46.1 Step 1 — Implement citation mapping

Build the citation mapper as a dedicated component.

Responsibilities:

- parse upstream source references,
- resolve them through the source binding table,
- map to Neosis source/snapshot IDs,
- attach page/section/locator metadata where verified,
- report mapping failures.

Do not let citation logic leak into route handlers.

## 46.2 Step 2 — Add evidence contract validation

Before returning a Ground response:

```text
for each evidence reference:
    verify source binding
    verify tenant ownership
    verify source/snapshot integrity if available
```

This is a validation boundary, not a second retrieval engine.

## 46.3 Step 3 — Add Ground chat mapping

If product chat requires persistent multi-turn Ground conversations:

```text
Neosis conversation
       |
       v
binding
       |
       v
Open Notebook chat session
       |
       v
upstream chat graph
```

Implement:

- create/find mapping,
- execute message,
- stream response,
- persist product-level conversation identity,
- recover missing binding if upstream session was deleted.

The recovery policy should be deterministic and documented.

## 46.4 Step 4 — Integrate Neosis episodic events

Record only useful product-level events.

Examples:

```text
GROUND_QUERY_STARTED
GROUND_QUERY_COMPLETED
GROUND_QUERY_FAILED
GROUND_SOURCE_PROJECTED
GROUND_SOURCE_PROJECTION_FAILED
GROUND_CITATION_MAPPING_DEGRADED
```

Do not mirror every Open Notebook internal LangGraph event into EpisodicMemory.

## 46.5 Step 5 — Add state integration

At minimum, preserve product-level state for:

- Run State,
- Task State if projection uses a task,
- Evidence State,
- Workspace State.

Open Notebook execution state remains internal.

Do not duplicate every upstream node state into Neosis PostgreSQL.

## 46.6 Step 6 — Add background projection lifecycle

Required lifecycle operations should be represented as explicit internal integration operations, such as:

```text
project_source
sync_workspace
remove_source_projection
repair_source_projection
health_check
```

The exact method names are not prescribed.

## 46.7 Step 7 — Add repair/reconciliation job

A reconciliation job should be able to answer:

```text
Which Neosis sources should exist in Open Notebook?
Which Open Notebook projections exist?
Which bindings are stale?
Which checksums differ?
Which projections failed?
```

This job should be safe to run repeatedly.

Recommended process:

```text
Neosis canonical state
       |
       v
expected projection set
       |
       v
compare to Open Notebook binding/projection state
       |
       v
repair missing/stale entries
```

## 46.8 Step 8 — Add deep health checks

The health component must test the actual dependency path needed by Ground.

Not merely:

```text
HTTP 200 from /health
```

but, where appropriate:

```text
API reachable
DB reachable
source route reachable
ask route available
configuration valid
```

Do not run an expensive LLM query on every generic health probe unless explicitly configured.

## 46.9 Step 9 — Add observability

Instrument:

- source projection latency,
- source projection failures,
- Ground request latency,
- upstream errors,
- citation translation errors,
- retry counts,
- stale binding counts,
- unrecoverable projection counts.

## Phase 3 tests

```text
citation mapper unit tests
citation tenant isolation tests
unresolvable citation tests
chat binding tests
chat reconnection/recovery tests
SSE translation tests
state event tests
reconciliation dry-run tests
reconciliation repair tests
health checks
retry/backoff tests
timeout tests
secret redaction tests
```

## Phase 3 exit gate

Phase 3 passes only when:

- citations are translated to canonical Neosis references,
- Ground chat works through the actual Open Notebook workflow where required,
- failures are represented in stable Neosis terms,
- projection reconciliation is repeatable,
- health checks detect real dependency failures,
- telemetry provides enough information to debug a single Ground run end-to-end.

---

# 47. PHASE 4 — EVALUATE, CUT OVER, DEPRECATE, OPERATIONALIZE

## Phase objective

Prove that the migration preserved Ground quality and integration correctness, then retire the custom Ground implementation from the active path.

## Phase 4 invariant

No architectural cutover occurs based only on “the endpoint returned 200.”

## 47.1 Evaluation tracks

There must be three comparable execution paths:

```text
A. Current Neosis Ground implementation
B. Standalone Open Notebook
C. Neosis + integrated Open Notebook
```

A and B establish behavioral baselines.

C must be close enough to B while satisfying Neosis product contracts.

## 47.2 Evaluation corpus

Use a fixed evaluation set containing:

- single-document factual questions,
- multi-document questions,
- questions requiring exact terminology,
- long-document questions,
- questions where the answer occurs in a small section,
- questions requiring combining multiple sources,
- questions whose answer is absent,
- questions with conflicting source statements,
- questions requiring source/page provenance,
- noisy documents,
- documents with tables or structured content where supported,
- adversarial prompt-injection-style content.

## 47.3 Core metrics

At minimum measure:

### Retrieval

- recall@k,
- evidence relevance,
- source hit rate,
- latency.

### Answer quality

- factual correctness,
- groundedness,
- unsupported-claim rate,
- answer completeness.

### Citation quality

- citation correctness,
- citation completeness,
- locator correctness,
- unresolved-reference rate.

### Operational quality

- p50 latency,
- p95 latency,
- timeout rate,
- retry rate,
- projection freshness,
- failure recovery rate.

## 47.4 Cutover requirements

Do not cut over merely because Open Notebook performs better or differently.

Cutover requires:

```text
behavior verified
AND
citation integrity verified
AND
tenant isolation verified
AND
source projection verified
AND
observability verified
AND
rollback path verified
```

## 47.5 Shadow mode

Before full retirement of the old Ground path, run controlled shadow comparisons where feasible.

Conceptual flow:

```text
User Ground request
       |
       +----> Open Notebook path (primary candidate)
       |
       +----> legacy Ground path (shadow)
                 |
                 v
           comparison metrics
```

The shadow path must not double-charge the user for an LLM provider unless this is explicitly accepted for the evaluation environment.

Where full shadow execution is too expensive, use an offline benchmark suite instead.

## 47.6 Deprecation policy

Once the integrated path passes the quality and safety gate:

1. mark the legacy Ground path deprecated,
2. stop using it in production traffic,
3. keep it temporarily available behind an explicit internal benchmark/debug flag if useful,
4. remove it only after the migration has stabilized and benchmark artifacts are retained.

Do not delete `HybridRetrievalService` simply because Ground no longer uses it.

It may remain valuable for:

- Research retrieval,
- evidence verification,
- experiments,
- local search,
- future dual-run migration,
- specialized internal retrieval.

## 47.7 Operational documentation

Update:

- setup documentation,
- architecture documentation,
- API integration documentation,
- migration ledger,
- runbook,
- troubleshooting notes,
- environment variable documentation,
- benchmark report.

## Phase 4 exit gate

Chapter 2 is complete only when:

- integrated Ground passes the evaluation gate,
- public API behavior is stable,
- citations map correctly,
- tenant isolation tests pass,
- Open Notebook failure modes are observable,
- recovery/reconciliation exists,
- the old Ground backend is removed from active traffic,
- architecture docs describe the new boundary,
- pinned upstream version is recorded,
- rollback is documented.

---

# 48. EXACT FILE-LEVEL CHANGE MAP

This section is deliberately expressed as responsibilities rather than guaranteed function names.

Before modifying any listed file, inspect the real file.

## `app/orchestration/ground_mode.py`

Target responsibility after migration:

- product-level Ground facade,
- authorization/context propagation,
- Open Notebook engine dispatch,
- error translation,
- run metadata.

Must not contain:

- custom vector query logic,
- custom RRF ranking,
- replacement Ask graph,
- copied upstream prompt templates.

## `app/services/hybrid_retrieval.py`

Do not make this the active Ground backend after cutover.

Do not delete in Chapter 2 Phase 2.

Keep available for other retrieval use cases and benchmark comparison.

## `app/api/routes/workspaces.py`

Keep route handlers thin.

Responsibilities:

- authenticate,
- authorize workspace,
- validate request,
- call Ground facade/service,
- translate response to HTTP schema.

Do not add SurrealDB business logic here.

## `app/workers/tasks.py`

Keep central worker registry thin.

Only dispatch Open Notebook projection/reconciliation jobs.

Implementation logic belongs in the integration module.

This avoids increasing one of the current architecture's identified god nodes.

## `app/services/memory_router.py`

Keep Open Notebook-specific knowledge out of the MemoryRouter.

MemoryRouter should decide memory access, not engine implementation.

## `app/services/storage.py`

Keep S3 abstraction unchanged unless source projection requires a missing capability.

If additional object download/stream capability is required, extend the storage abstraction rather than hardcoding S3 access inside Open Notebook integration code.

## `app/models/source.py` / source snapshot structures

Preserve canonical IDs, checksum, ownership, lifecycle.

Do not add large Open Notebook-shaped schemas to the core source model.

## `app/schemas/ground_mode.py`

Keep the public/product-level response engine-neutral.

Add only fields needed for product contract compatibility.

## `app/repositories/`

Add narrow persistence access for:

- Open Notebook binding,
- source projection mapping,
- conversation mapping if required.

Do not create a generic repository that can execute arbitrary Open Notebook database queries.

## `graph/`

Do not add Open Notebook's internal graph/database model wholesale.

Only add canonical/provenance relations that are useful to Neosis.

## `artifacts/citations/`

This is the preferred boundary for canonical citation translation/normalization.

Do not implement citation mapping in HTTP route handlers.

## `infrastructure/llm_gateway/`

Do not force Open Notebook through LiteLLM in the initial phase unless an exact integration requirement demands it.

Later model bridge work may use this boundary.

---

# 49. RECOMMENDED INTEGRATION MODULE RESPONSIBILITIES

The exact filename layout is flexible. The following responsibilities are not.

## OpenNotebookClient

Only transport and basic API interaction:

- request construction,
- HTTP calls,
- auth/header handling,
- serialization,
- timeout handling,
- upstream status translation.

It should not decide Neosis business policy.

## OpenNotebookConfig

Own configuration parsing and validation.

## OpenNotebookGroundEngine

Translate a Neosis Ground request into the upstream Ask/search workflow and back.

It must not reimplement retrieval.

## OpenNotebookChatEngine

Map Neosis conversation identity into upstream chat execution.

It must not reimplement chat history/context logic.

## OpenNotebookSourceSync

Project canonical source snapshots into Open Notebook.

Own:

- checksum comparison,
- source upload,
- status polling,
- retries,
- idempotency.

## OpenNotebookWorkspaceBinding

Own workspace/notebook identity mapping.

## CitationMapper

Own provenance translation.

## ModelBridge

Initially minimal or inactive.

Later may map Neosis model identities to upstream model configuration.

## Health

Own dependency and functional health checks.

## Schemas

Contain integration DTOs only. Do not clone all upstream models into Neosis schemas.

## Errors

Contain adapter-specific exceptions or translation types.

---

# 50. DO NOT DO THESE THINGS

The implementation agent must treat this list as a hard anti-pattern list.

### Do not build “Neosis RAG v2”

A new hybrid retriever, new search planner, new reranker, new context builder, and new final synthesis chain is not an integration.

### Do not copy Open Notebook code into `app/services/`

That creates an unmaintained fork hidden inside the product.

### Do not change upstream behavior without recording why

If a patch is unavoidable, document:

```text
upstream file
reason
exact change
why adapter-only change is impossible
upstream version
maintenance impact
```

### Do not expose Open Notebook API publicly

Neosis remains the product API.

### Do not use raw upstream identifiers in user-facing citations

Map them.

### Do not equate the memory system with the Open Notebook source store

They solve different architectural problems.

### Do not equate State with LangGraph state

Neosis state is the product-level lifecycle/state model. LangGraph state is execution state.

### Do not equate the Research Output KG with Open Notebook's relationships

They have different purposes.

### Do not automatically write every Ground answer to Knowledge Memory

Only promote information according to explicit product policy.

### Do not delete the old retrieval stack before evaluation

Keep it as a controlled baseline until Chapter 2 passes.

### Do not guess exact current symbols

Inspect them.

### Do not let a generated plan mutate the architecture mid-implementation

The agent is not authorized to replace this architecture merely because another design seems simpler.

---

# 51. ARCHITECTURAL DECISION RECORDS TO CREATE DURING IMPLEMENTATION

The agent must create short ADRs for the following decisions.

### ADR-CH2-001 — Open Notebook boundary

Record why Open Notebook is an internal Ground engine rather than a replacement for Neosis.

### ADR-CH2-002 — Canonical source ownership

Record why Neosis PostgreSQL/S3 remains canonical and Open Notebook is derived.

### ADR-CH2-003 — Workspace binding

Record why `workspace_id` and `notebook_id` are separate identifiers.

### ADR-CH2-004 — Source projection

Record why the actual source file is projected through Open Notebook's source ingestion path.

### ADR-CH2-005 — Model provider strategy

Record why provider unification is deferred until after exact-engine integration.

### ADR-CH2-006 — Citation translation

Record canonical provenance mapping and failure semantics.

### ADR-CH2-007 — Ground cutover

Record benchmark methodology and acceptance criteria.

---

# 52. TESTING STRATEGY

Testing must exist at four levels.

## Level 1 — Adapter unit tests

Test:

- request mapping,
- response mapping,
- binding logic,
- idempotency key generation,
- checksum comparison,
- error translation,
- citation mapping.

Mock the upstream service.

## Level 2 — Open Notebook contract tests

Run against the pinned Open Notebook instance.

Test:

- create notebook,
- ingest source,
- query/ask,
- chat if required,
- status behavior,
- response schemas.

These tests detect upstream drift when the pinned source changes.

## Level 3 — Neosis integration tests

Run:

```text
Neosis API
 -> Postgres
 -> S3
 -> Redis/worker
 -> Open Notebook API
 -> SurrealDB
```

Validate the entire source-to-answer path.

## Level 4 — End-to-end product tests

Test from the actual Neosis public endpoint through the final user-visible result.

Validate:

- workspace isolation,
- source projection,
- answer grounding,
- citations,
- streaming,
- failure behavior.

---

# 53. MINIMUM TEST MATRIX

| Test | Expected |
|---|---|
| Create workspace | Neosis workspace created; no accidental upstream workspace creation until needed |
| First Ground query | Binding created/reused, valid upstream notebook, answer returned |
| Upload source | Source stored canonically, projection job scheduled |
| Re-run projection | No duplicate upstream source |
| Source checksum changes | New projection/version behavior is explicit |
| Unauthorized workspace query | Rejected before upstream access |
| Cross-workspace upstream notebook ID | Not accepted from client |
| Missing source | Controlled source-not-ready behavior |
| Upstream unavailable | Stable Neosis engine-unavailable behavior |
| Upstream timeout | Stable timeout behavior and observable run state |
| Upstream malformed response | Controlled integration error |
| Unresolvable citation | No fabricated canonical citation |
| Empty retrieval | Grounding behavior preserved; no unsupported claim presented as sourced |
| Ground question answered by source | Evidence maps to canonical source |
| Multi-source answer | Multiple evidence records map correctly |
| Multi-turn chat | Session mapping stable |
| Worker retry | No duplicate source/workspace |
| Restart Open Notebook | Neosis bindings remain usable or are repairable |
| Delete Open Notebook projection | Reconciliation recreates it |
| Delete Neosis source | Policy-defined projection cleanup occurs without corrupting unrelated workspaces |
| Legacy Ground benchmark | Still runnable before deprecation |

---

# 54. GROUND BEHAVIORAL ACCEPTANCE TESTS

The following must be explicitly tested.

## Grounding

Question supported by source:

```text
Expected: answer supported by source + valid provenance.
```

Question not supported by source:

```text
Expected: system does not present unsupported information as if it came from workspace sources.
```

## Multi-document evidence

Question requires combining source A and source B:

```text
Expected: response can use both sources and return traceable evidence.
```

## Contradiction

Source A and B disagree:

```text
Expected: response preserves/communicates the disagreement rather than silently manufacturing a single fact.
```

## Citation precision

Question asks for a page/section-specific fact:

```text
Expected: citation points to the correct available locator.
```

## Long-context behavior

Long document question:

```text
Expected: Open Notebook's actual context/retrieval path handles it without the Neosis adapter reimplementing context compression.
```

---

# 55. ROLLBACK STRATEGY

Chapter 2 must be reversible.

Rollback layers:

### API rollback

Route remains unchanged while engine implementation changes behind the facade.

### Engine rollback

Configuration flag may select:

```text
open_notebook
legacy_ground
```

only if the repository's runtime architecture already has a safe feature-flag convention.

Do not create a scattered collection of `if USE_OLD_GROUND` checks.

### Data rollback

Canonical Neosis source and snapshot records are not destroyed by Open Notebook failures.

### Projection rollback

An Open Notebook notebook/source can be recreated from canonical Neosis source state.

### Code rollback

Pinned upstream version and integration commit must be independently revertible.

---

# 56. MIGRATION AND BACKFILL STRATEGY

Existing Neosis workspaces may already have sources indexed by the old system.

Do not automatically rewrite every workspace in one blocking migration.

Use an incremental projection strategy.

Recommended:

```text
existing workspace
       |
       v
mark eligible for Ground migration
       |
       v
create Open Notebook binding
       |
       v
project existing source snapshots
       |
       v
validate projection
       |
       v
switch Ground engine
```

For large workspaces, projection must be asynchronous and resumable.

The backfill should store checkpoints/status so a worker restart does not restart the entire workspace from scratch.

---

# 57. FREE-TIER / RESOURCE CONTROL

NeosisLM is intended to remain practical on free/low-cost infrastructure.

The Open Notebook migration must respect resource limits.

Important controls:

- source count limits,
- file size limits,
- concurrent source projection limits,
- LLM concurrency limits,
- Ground request rate limits,
- storage quotas,
- background worker concurrency,
- Open Notebook database volume.

Do not solve resource problems by silently reducing correctness.

Instead, expose clear “processing” or “quota” states.

---

# 58. BACKPRESSURE

Source projection can become a bottleneck.

The worker system must support:

```text
upload bursts
   -> queue
   -> bounded projection concurrency
   -> Open Notebook
```

Do not create unlimited concurrent source-processing requests.

Similarly, Ground execution must respect LLM/provider concurrency policies.

Use the existing Neosis queue/backpressure mechanisms where possible.

Do not create a second queue system solely for Open Notebook.

---

# 59. DATA CONSISTENCY MODEL

Chapter 2 intentionally introduces eventual consistency between canonical Neosis data and Open Notebook projections.

That is acceptable.

The system must make the state explicit.

Example:

```text
Neosis source = completed
Open Notebook projection = processing

=> source is canonical and valid in Neosis,
   but Ground may temporarily report source-not-ready.
```

Do not falsely mark the projection ready because the Neosis upload succeeded.

Do not falsely mark Neosis source processing complete because Open Notebook accepted an upload.

These are separate state transitions.

---

# 60. RECONCILIATION INVARIANTS

The reconciliation system should enforce these invariants:

### Invariant A
Every active Ground-eligible Neosis source has either:

```text
valid Open Notebook binding
OR
explicit projection failure/pending state
```

### Invariant B
No binding points to a different workspace than the one that owns it.

### Invariant C
Projected snapshot checksum is known.

### Invariant D
Public citations never expose upstream-only identifiers.

### Invariant E
Deleting/recreating the Open Notebook projection cannot destroy the canonical Neosis source.

### Invariant F
Open Notebook failure cannot silently corrupt canonical Neosis state.

---

# 61. CHANGE CONTROL RULES FOR THE IMPLEMENTATION AGENT

The implementation agent must make changes in small, reviewable batches.

Every batch should answer:

```text
What architectural boundary did this change modify?
Why was the change required?
What existing component is intentionally left untouched?
What tests prove the new behavior?
```

Do not produce a giant refactor that changes twenty subsystems simultaneously.

Recommended commit segmentation:

```text
1. Add upstream Open Notebook + runtime
2. Add integration configuration/client
3. Add workspace binding
4. Add source projection
5. Add Ground engine facade
6. Add citation mapping
7. Add chat mapping
8. Add reliability/health/telemetry
9. Add benchmark suite
10. Cut over and deprecate legacy Ground
```

The actual Git commits may differ, but the conceptual boundaries should remain understandable.

---

# 62. WHEN THE AGENT FINDS A MISMATCH

This section is mandatory because the live repository can evolve.

Suppose this document says:

```text
app/services/hybrid_retrieval.py
```

but the repository contains:

```text
app/retrieval/pipeline/hybrid.py
```

The agent must not create a new `app/services/hybrid_retrieval.py` just to match the document.

Instead:

```text
1. Identify current component.
2. Verify responsibility.
3. Update the implementation map.
4. Integrate against the current component.
```

Suppose the documented route differs from the live route.

The agent must preserve the live route unless a product-level API migration is explicitly authorized.

Suppose a documented class no longer exists.

The agent must identify its replacement responsibility rather than inventing a duplicate class.

Suppose Open Notebook's current upstream API has changed.

The agent must adapt the compatibility layer to the pinned upstream version. It must not “fix” the problem by creating a local imitation of the old API.

---

# 63. REQUIRED IMPLEMENTATION NOTES FILE

During Phase 1, create a small Chapter 2 implementation inventory.

Recommended content:

```text
CH2_IMPLEMENTATION_INVENTORY.md

Neosis actual path
Neosis actual symbol
Documented role
Verified role
Open Notebook upstream path
Open Notebook upstream symbol/route
Integration responsibility
Tests
Status
```

This file exists to close the gap between architecture documentation and live repository reality.

It should be updated when the agent discovers a mismatch.

Do not rewrite this primary specification every time a local filename changes. Update the inventory instead.

---

# 64. REQUIRED UPSTREAM PIN FILE

Record the actual Open Notebook revision in a machine-readable and human-readable place.

Conceptual:

```text
third_party/
  open-notebook/
    UPSTREAM_REVISION.md
```

or use the repository's normal vendor/version manifest convention.

Contents should include:

```text
Repository:
Commit SHA:
Date pinned:
License:
Local patches:
Reason for patches:
How to update:
Regression suite required:
```

Do not use “latest” as the only version marker.

---

# 65. UPSTREAM UPDATE POLICY

After Chapter 2 is complete, Open Notebook should not be updated casually.

A future upstream update requires:

```text
fetch new revision
inspect changed APIs
run upstream smoke tests
run adapter contract tests
run Ground regression suite
run citation suite
run tenant-isolation suite
compare benchmark metrics
review migration notes
then update pin
```

Do not upgrade Open Notebook merely because a new commit exists.

The pinned version is part of the product runtime.

---

# 66. RESEARCH MODE NON-INTERFERENCE RULE

Chapter 2 must not convert Research Mode into an Open Notebook workflow.

Research Mode remains conceptually:

```text
research objective
   -> planning
   -> searching
   -> evidence gathering
   -> synthesis
   -> research memory
   -> output KG
```

The future Research Engine may reuse LangChain Open Deep Research and STORM patterns, but that work belongs to a separate chapter/phase.

LangChain Open Deep Research is currently an archived repository as of August 21, 2026. Therefore any future use must be treated as a pinned/reference implementation rather than an uncontrolled long-term runtime dependency.

STORM/knowledge-storm remains a research methodology/reference layer and should not be introduced as a competing Ground supervisor.

GPT Researcher remains a comparative/secondary reference rather than a second autonomous supervisor in Chapter 2.

---

# 67. FUTURE COMPATIBILITY HOOKS

Chapter 2 should leave narrow interfaces for later capabilities.

Potential future adapters:

```text
GroundEngine
ResearchEngine
ChatEngine
SourceProjectionEngine
EvidenceResolver
ModelProviderBridge
```

Do not implement all of them now.

The important thing is that `GroundModeOrchestrator` should depend on a Ground engine interface/contract, not hardcode every Open Notebook HTTP detail throughout the orchestration layer.

---

# 68. EXPECTED FINAL DIRECTORY SHAPE

This is a target responsibility map, not a literal requirement to create every path exactly as written.

```text
NeosisLM/
|
+-- third_party/
|   +-- open-notebook/
|       +-- <pinned upstream>
|       +-- UPSTREAM_REVISION.md
|
+-- app/
|   +-- integrations/
|   |   +-- open_notebook/
|   |       +-- client.py
|   |       +-- config.py
|   |       +-- ground_engine.py
|   |       +-- chat_engine.py
|   |       +-- source_sync.py
|   |       +-- workspace_binding.py
|   |       +-- citation_mapper.py
|   |       +-- model_bridge.py
|   |       +-- schemas.py
|   |       +-- errors.py
|   |       +-- health.py
|   |
|   +-- orchestration/
|   |   +-- ground_mode.py
|   |
|   +-- models/
|   |   +-- open_notebook_binding.py
|   |
|   +-- repositories/
|   |   +-- open_notebook.py
|   |
|   +-- artifacts/
|   |   +-- citations/
|   |
|   +-- workers/
|       +-- <thin projection/reconciliation dispatch>
|
+-- tests/
|   +-- unit/
|   +-- integration/
|   +-- e2e/
|   +-- eval/
|
+-- docs/
|   +-- CH2_IMPLEMENTATION_INVENTORY.md
|   +-- CH2_ADR_*.md
|   +-- CH2_GROUND_MIGRATION_RUNBOOK.md
```

Again: inspect the repository before creating paths. If the codebase already has a superior integration convention, use it.

---

# 69. DEFINITION OF “DONE”

Chapter 2 is not done when:

```text
Open Notebook starts.
```

Chapter 2 is done when all of the following are true:

```text
[ ] Actual upstream Open Notebook is pinned.
[ ] Upstream runs independently.
[ ] Open Notebook SurrealDB is internal-only.
[ ] Neosis can create/reuse a workspace binding.
[ ] Neosis sources can be projected through actual upstream source ingestion.
[ ] Projection is idempotent.
[ ] Projection state is observable.
[ ] Ground requests route through Open Notebook Ask.
[ ] No custom Ground RAG is hidden inside the adapter.
[ ] Ground response maps into Neosis schema.
[ ] Ground citations map into canonical Neosis source/snapshot references.
[ ] No upstream-only IDs leak to users.
[ ] Ground chat uses upstream chat workflow where required.
[ ] Memory remains a Neosis routing/persistence concern.
[ ] State remains a Neosis lifecycle concern.
[ ] Output KG is not polluted by normal Ground answers.
[ ] Tenant isolation tests pass.
[ ] Failure/retry/timeout behavior is explicit.
[ ] Health checks detect dependency failures.
[ ] Observability connects Neosis run to upstream execution.
[ ] Legacy Ground baseline remains available until benchmark gate.
[ ] Integrated system is compared with standalone Open Notebook.
[ ] Regression thresholds are met.
[ ] Legacy Ground is removed from active traffic.
[ ] Architecture docs are updated.
[ ] Upstream revision is recorded.
[ ] Rollback procedure is documented.
```

---

# 70. MANDATORY FINAL AUDIT

Before declaring Chapter 2 complete, the implementation agent must perform a final audit against every item below.

## Architecture audit

```text
Does Open Notebook own Ground retrieval/execution?
Does Neosis own workspace identity?
Does Neosis own canonical source identity?
Does Neosis own provenance normalization?
Does Neosis own user-facing API?
Does Neo4j remain a projection?
Does PostgreSQL remain canonical?
Does S3 remain canonical for source blobs?
```

## Anti-reimplementation audit

Search the Neosis codebase for newly added:

```text
vector search logic in Ground adapter
RRF logic copied into Open Notebook adapter
new source chunking logic for Ground
new answer-synthesis prompts
new Ask LangGraph graph
new chat graph
new Open Notebook replacement model manager
```

Any such code must have an explicit, reviewed architectural justification.

## Isolation audit

Verify no public route exposes:

```text
SurrealDB
Open Notebook notebook_id
Open Notebook source_id
Open Notebook internal API
```

unless the product explicitly requires a debug-only authenticated view.

## Provenance audit

For a real answer, trace:

```text
UI answer
  -> Neosis citation
  -> Neosis source_id
  -> Neosis snapshot_id
  -> canonical S3 blob
  -> corresponding source content
```

## Failure audit

Simulate:

```text
Open Notebook API down
SurrealDB down
source projection failure
LLM failure
citation resolution failure
worker restart
Neosis API restart
Open Notebook restart
```

Verify recoverability and stable user-facing errors.

---

# 71. FINAL ARCHITECTURAL SUMMARY

The final Chapter 2 architecture should look like this:

```text
                         +-----------------------+
                         |      NeosisLM         |
                         |                       |
                         |  Workspace / Auth     |
                         |  Memory / State       |
                         |  Provenance           |
                         |  API / SSE            |
                         +-----------+-----------+
                                     |
                                     v
                           +---------------------+
                           | Ground Facade       |
                           | engine-neutral      |
                           +----------+----------+
                                      |
                                      v
                           +---------------------+
                           | Open Notebook       |
                           | Integration Layer   |
                           +----------+----------+
                                      |
                                      v
                  +------------------------------------------+
                  |           Open Notebook Engine            |
                  |                                          |
                  | Source Processing                         |
                  | Ask/Search LangGraph                      |
                  | Chat LangGraph                            |
                  | Retrieval                                 |
                  | Context Builder                            |
                  | Model Provisioning                        |
                  +-------------------+----------------------+
                                      |
                           +----------+----------+
                           |                     |
                           v                     v
                      SurrealDB             LLM Providers

Neosis canonical side:

PostgreSQL <---- canonical domain state
S3         <---- immutable source blobs
Neo4j      <---- graph projection
Redis/Arq  <---- jobs/events
```

The key design principle is:

> **Neosis owns the product. Open Notebook owns Ground execution. The adapter owns the boundary.**

---

# 72. IMPLEMENTATION AGENT OPERATING INSTRUCTIONS

These instructions are intended to be copied into the IDE agent together with this file.

### Rule 1 — Do not drift

You are implementing an existing architecture, not inventing a new one.

Do not replace the target architecture with a simpler design because it is faster to code.

### Rule 2 — Discover before editing

Before touching a local file, inspect its current source.

Do not rely on the literal function names written in this document when the document intentionally describes responsibilities rather than every exact implementation symbol.

### Rule 3 — Upstream first

Before writing a replacement for an Open Notebook behavior, inspect the pinned upstream implementation.

If the upstream behavior exists, reuse it.

### Rule 4 — Adapter, not fork

Put Neosis-specific translation in the integration boundary.

Do not copy upstream internals into Neosis services.

### Rule 5 — Canonical truth stays canonical

Never make Open Notebook's database authoritative for Neosis workspace/source identity.

### Rule 6 — Preserve public contracts

Do not change existing Neosis API paths or response schemas unless required and explicitly documented.

### Rule 7 — No hidden assumptions

When a repository detail is missing from this document:

```text
inspect -> verify -> document -> implement
```

Do not:

```text
assume -> invent -> spread assumption across codebase
```

### Rule 8 — No premature cleanup

Do not delete the old Ground implementation until the benchmark/cutover gate passes.

### Rule 9 — Keep central nodes thin

Do not turn `workspaces.py`, `Workspace`, `WorkspaceRepository`, `MemoryRouter`, or `tasks.py` into Open Notebook integration hubs.

### Rule 10 — Every phase has an exit gate

Do not move to the next phase by judgment alone. Run the phase tests and record the outcome.

### Rule 11 — Keep an implementation inventory

Update `CH2_IMPLEMENTATION_INVENTORY.md` whenever the real repository differs from the architecture documentation.

### Rule 12 — Preserve reversibility

The system must be able to return to the legacy Ground backend during migration until the final cutover is approved by tests/metrics.

---

# 73. AGENT EXECUTION LOOP

The implementation agent should follow this loop for every work package:

```text
READ relevant Phase section
        |
        v
DISCOVER actual repository state
        |
        v
DISCOVER exact upstream behavior
        |
        v
MAP Neosis object <-> upstream object
        |
        v
IMPLEMENT smallest compatibility change
        |
        v
RUN focused tests
        |
        v
RUN integration tests
        |
        v
UPDATE implementation inventory
        |
        v
CHECK anti-pattern list
        |
        v
MOVE to next work package
```

Never invert the order by designing a large replacement first and checking the existing code later.

---

# 74. WHAT COUNTS AS A GOOD IMPLEMENTATION

A good Chapter 2 implementation should make the architecture feel smaller, not larger.

After the migration:

- Open Notebook handles Ground execution complexity.
- Neosis handles product complexity.
- The adapter handles translation.
- PostgreSQL remains canonical.
- S3 remains canonical for blobs.
- Graph remains a projection.
- Memory remains a shared product abstraction.
- State remains a product lifecycle abstraction.
- Research Mode remains independent.

If Chapter 2 results in a larger custom RAG engine inside Neosis, the migration has failed architecturally even if the endpoint works.

---

# 75. SOURCE BASIS FOR THIS SPECIFICATION

This Chapter 2 specification was constructed from:

## Neosis source/documentation basis

- current Neosis architecture documentation,
- current Agents & Orchestrators documentation,
- current API documentation,
- current project tree,
- `MODEL_ARCHITECTURE_AND_RELATIONS.md`,
- Graphify dependency/community analysis,
- current implementation plan / architecture workbook where relevant.

The local documents establish the Neosis product architecture and current component relationships. They do not expose every current source-file body; therefore the dynamic repository-discovery rule is intentional and mandatory.

## Upstream basis

Open Notebook's current upstream architecture documentation and source behavior were inspected for:

- source ingestion,
- source processing,
- Ask/search workflow,
- chat workflow,
- model provisioning,
- SurrealDB persistence,
- FastAPI backend boundary,
- LangGraph workflows.

Useful upstream references:

- https://github.com/lfnovo/open-notebook
- https://github.com/lfnovo/open-notebook/blob/main/docs/7-DEVELOPMENT/architecture.md

Other project references relevant to later chapters:

- https://github.com/langchain-ai/open_deep_research
- https://github.com/stanford-oval/storm

The Open Deep Research repository is currently archived as of 2026-08-21. It should therefore be treated as a pinned/reference implementation for future Research work rather than an uncontrolled long-term runtime dependency.

---

# 76. FINAL INSTRUCTION TO THE IMPLEMENTATION AGENT

Do not reinterpret this document as permission to redesign NeosisLM.

Implement Chapter 2 exactly as an integration/migration effort:

```text
CURRENT NEOSIS
      |
      | preserve product contracts
      v
THIN COMPATIBILITY LAYER
      |
      | delegate, do not duplicate
      v
ACTUAL OPEN NOTEBOOK
      |
      v
ITS REAL LANGGRAPH + RETRIEVAL + SOURCE PROCESSING
```

The implementation is successful when Open Notebook's mature Ground behavior is genuinely executing inside NeosisLM while the user continues to experience one coherent NeosisLM product and one canonical workspace/memory/provenance system.

Whenever a choice arises between:

```text
A. reimplementing upstream behavior locally
B. adapting to upstream behavior through a narrow compatibility layer
```

choose **B**, unless a concrete technical incompatibility is documented and tested.

Whenever a choice arises between:

```text
A. guessing a repository detail from this document
B. inspecting the live repository
```

choose **B**.

Whenever a choice arises between:

```text
A. changing the architecture to fit a convenient implementation
B. adapting the implementation to the existing architecture
```

choose **B**.

That is the core discipline of Chapter 2.
