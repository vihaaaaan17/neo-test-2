# NeosisLM — Chapter 3 Architecture & Migration Specification
## Research Mode / Advanced Research Engine
## Upstream-First Deep Research Integration + Canonical Neosis Research Fabric

**Document status:** Architecture and migration contract

**Target:** NeosisLM Chapter 3

**Date:** 2026-09-19

**Implementation unit:** Four phases. Detailed phase rulebooks, subphases, work packages, exact implementation steps, commands, and ticket sequencing are intentionally deferred to the separate Chapter 3 phase-rulebook document.

**Primary objective:** Replace the current prototype Research Mode implementation with a production-grade Advanced Research Engine composed from mature upstream research systems while preserving NeosisLM as the product-level system of record, workspace boundary, state owner, evidence/provenance layer, memory router, graph projection owner, API boundary, and operational control plane.

---

# 0. READ THIS BEFORE CHANGING CODE

This document is an architecture and migration contract, not a brainstorming document.

The implementation agent must treat this document as the architectural target for Chapter 3.

The objective is not to make the existing `ResearchModeOrchestrator` bigger.

The objective is to move NeosisLM from the current prototype research loop to a mature, composable Research Engine while keeping the existing NeosisLM product architecture intact.

The most important rule is:

> **Reuse mature upstream research behavior. Do not reimplement upstream research behavior merely because it is possible to build a local version.**

The selected upstream systems are:

```text
Open Deep Research
STORM / knowledge-storm
GPT Researcher
```

They do not automatically become three independent supervisors.

The default architectural direction is:

```text
Open Deep Research
    = primary deep-research execution architecture

STORM
    = optional perspective/question/outlining strategy capability

GPT Researcher
    = reusable retrieval/crawling/research capability
```

Neosis-specific work belongs around those engines:

- research request/API compatibility,
- workspace ownership,
- Research Run / Task lifecycle,
- evidence normalization,
- source identity,
- provenance,
- tags,
- artifact persistence,
- event normalization,
- retry and cancellation behavior,
- resource governance,
- memory eligibility and promotion,
- graph promotion,
- report persistence,
- observability,
- usage/cost accounting,
- evaluation,
- migration,
- rollback,
- tenant isolation,
- security.

The upstream research systems remain responsible for the research behavior they already implement.

---

# 1. MISSION OF CHAPTER 3

NeosisLM has two first-class user-visible modes:

1. **Ground Mode** — strict source-grounded interaction over a workspace's sources.
2. **Research Mode** — autonomous research over external information and the shared Neosis research fabric.

Chapter 2 established the Ground boundary.

Chapter 3 establishes the Research boundary.

The target relationship is:

```text
                              NeosisLM
                                  |
                   +--------------+--------------+
                   |                             |
                 GROUND                       RESEARCH
                   |                             |
                   v                             v
        Open Notebook Engine             Neosis Research Engine
        (actual upstream)                        |
                   |                              v
                   v                    mature research runtimes
        Ground compatibility            Open Deep Research
               layer                    STORM / knowledge-storm
                                         GPT Researcher
                   |                              |
                   v                              v
          Neosis canonical side           research capabilities
                   |                              |
                   +---------------+--------------+
                                   |
                                   v
                    Neosis canonical research fabric
```

The critical separation is:

```text
Ground
    = source-grounded execution over workspace sources

Research
    = autonomous evidence discovery, investigation,
      synthesis, and research artifact generation
```

Do not collapse these into one generic supervisor.

Research Mode may consume selected Ground-visible or workspace sources when explicitly configured, but Research Mode remains an independent product mode.

---

# 2. SCOPE BOUNDARY

## 2.1 In scope

Chapter 3 must establish a production architecture for:

- deep research execution,
- multi-step research planning,
- multi-source evidence gathering,
- web retrieval,
- academic retrieval,
- optional MCP research capabilities,
- source/evidence normalization,
- provenance,
- Research Run state,
- Research Task state,
- report artifacts,
- research events,
- cancellation,
- retries,
- partial research,
- budget enforcement,
- memory promotion,
- Research Output KG promotion,
- evaluation,
- cost accounting,
- observability,
- production cutover.

## 2.2 Explicitly out of scope

The architecture does not authorize:

- redesigning Ground Mode,
- rebuilding Open Notebook,
- turning Open Notebook into the Research Engine,
- creating an unrelated second memory architecture,
- creating an unrelated second graph architecture,
- creating an unrelated second event bus,
- replacing PostgreSQL as canonical state,
- replacing S3 as canonical immutable blob storage,
- replacing Redis/Arq as the current job infrastructure without an explicit architecture decision,
- silently rewriting the whole LLM gateway during Research Mode implementation,
- creating three competing autonomous research supervisors,
- deleting the current Research Mode prototype before evaluation,
- forcing every upstream package through Neosis-specific implementation details when an adapter is sufficient,
- adding arbitrary product features merely because an upstream research package supports them.

---

# 3. CURRENT RESEARCH MODE — VERIFIED BASELINE

The current live repository contains:

```text
app/api/routes/workspaces.py
app/workers/tasks.py
app/orchestration/research_mode.py
app/services/web_search.py
app/services/memory_router.py
app/schemas/graph.py
```

The current public research route is registered under the workspace router:

```text
POST /workspaces/{workspace_id}/research
```

The request model currently contains:

```text
objective
```

The route currently schedules:

```text
run_research_agent_job
```

The current worker lives in:

```text
app/workers/tasks.py
```

and constructs:

```text
ResearchModeOrchestrator
WebSearchTool
```

The current orchestrator is a four-node LangGraph:

```text
planner
   |
   v
executor
   |
   +----> executor
   |
   v
synthesizer
   |
   v
reporter
```

The current context is:

```text
plan
current_task_index
gathered_evidence
```

The current executor calls:

```text
WebSearchTool.search()
```

which currently uses Tavily.

The current synthesizer converts evidence strings into `MemoryItem(type="source")`, uses `MemoryRouterService.build_context()`, and asks the LLM for an `OutputGraph`.

The current reporter produces a human-readable summary.

The current worker publishes progress through Redis and projects the resulting `OutputGraph`.

This implementation is the migration baseline.

It is not the final Research Engine.

---

# 4. CURRENT RESEARCH MODE — ARCHITECTURAL LIMITATIONS

The current implementation is intentionally small and therefore lacks the depth required by the target product.

It currently:

- plans primarily around a small set of search queries,
- executes searches sequentially,
- stores retrieved evidence as formatted strings,
- does not have canonical Research Run state,
- does not have canonical Research Task state,
- does not have first-class Evidence state,
- does not have strong source normalization,
- does not have durable claim/evidence lineage,
- uses memory context as an intermediate representation,
- goes directly from evidence to graph synthesis,
- has limited source deduplication,
- has limited contradiction representation,
- has limited research budgeting,
- has limited cancellation semantics,
- has limited partial-result semantics,
- has limited academic retrieval routing,
- has limited retriever routing,
- has no mature upstream research execution boundary,
- does not preserve sufficient information for later research verification.

Chapter 3 must address those limitations without recreating mature upstream behavior locally.

---

# 5. SOURCE-OF-TRUTH POLICY AND ANTI-DRIFT PROTOCOL

This section is mandatory.

The Research Engine is a composite system.

There are four evidence categories.

## Evidence Level A — Repository-verified

The exact current Neosis source has been inspected.

Examples:

- actual FastAPI route,
- actual worker,
- actual class,
- actual schema,
- actual model,
- actual repository,
- actual test,
- actual dependency,
- actual migration.

Level A is authoritative for exact current local implementation details.

## Evidence Level B — Architecture-documented

The existing Neosis architecture, Chapter 2 contract, Graphify analysis, or current documentation establishes a component or responsibility.

Level B is authoritative for intended architectural responsibility but not for guessed symbol names.

## Evidence Level C — Upstream-verified

The exact pinned upstream implementation has been inspected.

Examples:

- Open Deep Research graph,
- STORM research workflow,
- GPT Researcher retriever interfaces,
- provider adapters,
- MCP adapters,
- academic retrieval adapters.

Level C is authoritative for the behavior of the pinned upstream implementation.

## Evidence Level D — Inference or assumption

Any statement not directly established by A, B, or C.

Level D must not silently become implementation truth.

When unresolved:

```text
discover
   ->
document
   ->
isolate
   ->
test
```

Never:

```text
assume
   ->
spread assumption across code
```

---

# 6. DYNAMIC REPOSITORY-DISCOVERY RULE

Before changing a local component, the implementation agent must:

```text
1. Locate the documented path.
2. Verify the file exists.
3. Inspect the current contents.
4. Identify the current route/class/service names.
5. Identify callers and dependencies.
6. Identify tests.
7. Determine whether the documented responsibility still exists.
8. Record any mismatch in the implementation inventory.
9. Only then make the change.
```

If a file has moved, use the live path.

Do not create a duplicate just to satisfy an old architectural map.

If a class has been renamed, use the live class.

If a route has moved, preserve the live public API unless an explicit API migration is part of Chapter 3.

This rule applies to:

```text
app/api/routes/workspaces.py
app/workers/tasks.py
app/orchestration/research_mode.py
app/services/web_search.py
app/services/memory_router.py
app/services/hybrid_retrieval.py
app/repositories/graph.py
app/models/source.py
app/models/knowledge.py
```

and all future Chapter 3 files.

---

# 7. CHAPTER 2 NON-INTERFERENCE RULE

Chapter 3 must preserve the completed Chapter 2 Ground architecture.

Do not use Research Mode as a reason to redesign Ground.

The intended relationship remains:

```text
GROUND
   |
   v
Open Notebook integration
   |
   v
actual Open Notebook Ground engine
```

and independently:

```text
RESEARCH
   |
   v
Neosis Research Engine
   |
   v
research upstream systems
```

Shared infrastructure may include:

```text
PostgreSQL
S3
Redis/Arq
Neo4j
memory services
source identity
provenance services
LLM gateway
```

but ownership remains separated.

Research must not become a second implementation of Ground retrieval.

Ground must not become dependent on Research Mode.

---

# 8. CURRENT NEOSIS ARCHITECTURAL BASELINE

The current application architecture is:

```text
FastAPI
   |
   +--> API routes
   |
   +--> services
   |
   +--> repositories
   |
   +--> integrations
   |
   +--> workers
```

Supporting infrastructure:

```text
PostgreSQL
    = canonical domain state

S3-compatible object storage
    = immutable source blobs / large artifacts

Redis + Arq
    = background work / pub-sub / transient infrastructure

Neo4j
    = graph projection

Open Notebook
    = Ground execution substrate
```

Research Engine becomes another integration-bound application subsystem.

It does not replace any canonical infrastructure.

---

# 9. SIX MEMORY SYSTEMS

NeosisLM defines six logical memory systems:

1. Source Memory
2. Working Memory
3. Episodic Memory
4. Knowledge Memory
5. Research Memory
6. User/Workspace Memory

Chapter 3 must preserve the distinction.

A research artifact is not automatically memory.

A retrieved source is not automatically Knowledge Memory.

A report is not automatically Research Memory.

Promotion occurs explicitly.

---

# 10. EIGHT STATE SYSTEMS

NeosisLM defines eight logical state systems:

1. Workspace State
2. Research State
3. Plan State
4. Task State
5. Run State
6. Evidence State
7. Graph State
8. Version State

These are product-level state concepts.

They must not be collapsed into one upstream LangGraph state object.

Correct:

```text
Neosis Research State
    = durable product lifecycle

upstream LangGraph state
    = execution state

Redis job
    = worker transport/execution state

Neo4j
    = projection state
```

---

# 11. EXECUTION STATE VS CANONICAL PRODUCT STATE

This distinction is a hard rule.

Do not make:

```text
LangGraph State == ResearchRun
```

Do not make:

```text
job payload == canonical ResearchRun
```

Do not make:

```text
Neo4j graph == canonical research database
```

A research runtime can be replaced or restarted without invalidating the product-level research identity.

---

# 12. TARGET RESEARCH DOMAIN MODEL

The target conceptual model is:

```text
Workspace
    |
    +--> ResearchRun
           |
           +--> ResearchTask
           |      |
           |      +--> ResearchArtifact
           |
           +--> ResearchEvidence
           |
           +--> ResearchSource
           |
           +--> ResearchReport
           |
           +--> ResearchGraphCandidate
           |
           +--> ResearchMemoryCandidate
           |
           +--> ResearchUsage
           |
           +--> ResearchEvent
```

A run is the durable execution identity.

A task is a bounded unit within a run.

Evidence records observed support.

Artifacts are normalized outputs.

Reports are user-facing synthesized artifacts.

Graph and memory outputs are promotion candidates.

Usage records operational economics.

Events describe lifecycle.

---

# 13. CANONICAL RESEARCH ENTITIES

The exact SQLAlchemy layout must be determined after repository inspection.

The architectural responsibilities are mandatory.

Potential model organization:

```text
app/models/research.py
```

or:

```text
app/models/research_run.py
app/models/research_task.py
app/models/research_evidence.py
app/models/research_artifact.py
app/models/research_source.py
app/models/research_usage.py
```

The implementation agent must choose the repository-consistent layout.

Do not create dozens of model files without need.

Do not create a single giant JSONB research record as a substitute for canonical relational identity.

---

# 14. RESEARCH RUN

`ResearchRun` represents one user-visible research execution.

Conceptual fields include:

```text
run_id
workspace_id
owner_id
objective
status
engine
engine_revision
configuration_version
created_at
started_at
completed_at
parent_run_id
error metadata
usage summary
```

The exact names may differ.

The following concepts are mandatory:

- stable run identity,
- workspace ownership,
- objective,
- lifecycle,
- engine provenance,
- configuration provenance,
- timestamps,
- explicit terminal state,
- failure/cancellation representation.

Do not use an upstream session ID as the canonical run ID.

---

# 15. RESEARCH TASK

`ResearchTask` represents a bounded unit of research.

Examples:

```text
Investigate market structure
Find primary evidence
Investigate historical context
Validate conflicting statistics
Analyze academic literature
```

It should preserve enough information to answer:

```text
What was the engine attempting to investigate?
Which run owned the task?
What was the task's result?
What failed?
What evidence was collected?
```

Possible concepts:

```text
task_id
run_id
parent_task_id
objective
sequence
status
strategy
created_at
started_at
completed_at
failure metadata
usage
```

---

# 16. RESEARCH RUN LIFECYCLE

The final state vocabulary should follow existing project conventions.

The architecture requires support for concepts equivalent to:

```text
CREATED
PLANNING
RESEARCHING
SYNTHESIZING
FINALIZING
COMPLETED
PARTIAL
FAILED
CANCELLED
```

The implementation must not use absence of a worker as a state.

A terminal state is durable.

A partial run is not a completed run.

---

# 17. RESEARCH TASK LIFECYCLE

Tasks may have states equivalent to:

```text
PENDING
RUNNING
COMPLETED
PARTIAL
FAILED
CANCELLED
SKIPPED
```

The task state must explain why a task did not complete.

If a parent task is expanded into subtasks, the relationships must remain traceable.

---

# 18. RESEARCH OBJECTIVE INTEGRITY

The original objective of a run is immutable.

If the user materially changes the objective:

```text
create a new run
```

or an explicitly versioned continuation.

Do not silently rewrite the objective mid-execution.

This is required for auditability.

---

# 19. RESEARCH PLAN INTEGRITY

A research plan is an execution artifact.

It is not ground truth.

A plan may change as research discovers new facts.

The architecture should allow:

```text
planned
expanded
revised
pruned
completed
```

but should retain enough history to understand what changed where product-level auditability requires it.

---

# 20. PRIMARY RESEARCH ENGINE BOUNDARY

Neosis should expose one product-owned abstraction:

```text
ResearchEngine
```

Conceptually:

```text
ResearchEngine
    + start(...)
    + execute(...)
    + stream(...)
    + cancel(...)
    + collect_artifacts(...)
    + collect_evidence(...)
    + report_usage(...)
```

The exact interface must be derived from the live repository and actual upstream runtime.

The non-negotiable property is:

> Product code depends on a Neosis research contract, not directly on upstream internal graph/node/class structures.

---

# 21. TARGET INTEGRATION DIRECTORY

Preferred responsibility boundary:

```text
app/
    integrations/
        research_engine/
            __init__.py
            engine.py
            config.py
            open_deep_research.py
            storm.py
            gpt_researcher.py
            retrievers.py
            normalizers.py
            provenance.py
            events.py
            errors.py
            schemas.py
            health.py
```

This is a target responsibility map.

The live repository may dictate a different literal location.

Do not put the whole Research Engine in:

```text
app/orchestration/research_mode.py
```

Do not put it in:

```text
app/workers/tasks.py
```

---

# 22. PRODUCT ORCHESTRATION BOUNDARY

The existing:

```text
app/orchestration/research_mode.py
```

should become a thin product-level compatibility boundary during migration.

Target concept:

```text
Research API
    |
    v
Research Service / facade
    |
    v
ResearchEngine
    |
    +--> Open Deep Research
    +--> STORM capability
    +--> GPT Researcher capability
    +--> Retriever layer
```

The orchestration layer owns:

- workspace policy,
- authorization,
- configuration,
- quota,
- run creation,
- engine selection,
- cancellation,
- lifecycle,
- persistence coordination.

It does not own upstream research loops.

---

# 23. OPEN DEEP RESEARCH — ROLE

Open Deep Research is the primary deep-research runtime candidate.

It provides a mature research architecture involving LangGraph, research iterations, configurable models, search tools, and MCP-oriented tool use.

The current upstream graph entry point is:

```text
src/open_deep_research/deep_researcher.py:deep_researcher
```

The current project configuration declares Python 3.11.

The repository was archived by its owner on 2026-08-21.

Therefore:

> **Open Deep Research must be pinned and treated as a reference/runtime snapshot, not as an uncontrolled floating dependency.**

---

# 24. OPEN DEEP RESEARCH — REUSE RULE

Where compatible with the product architecture, reuse upstream behavior for:

- planning,
- researcher iteration,
- parallel/concurrent research units,
- tool invocation,
- MCP integration,
- compression/summarization,
- final report generation,
- research model configuration.

Do not reproduce those behaviors in a Neosis graph under different names.

If an adapter is required, adapt at the boundary.

---

# 25. STORM — ROLE

STORM provides perspective-driven research/question asking, retrieval-oriented exploration, outlining, and citation-aware writing capabilities.

Its role in Neosis is:

```text
optional research-strategy capability
```

not:

```text
second end-to-end product supervisor
```

Use it when it provides a concrete benefit such as:

- perspective diversification,
- question expansion,
- research outline generation,
- multi-angle exploration.

Do not run it unconditionally as a competing autonomous researcher.

---

# 26. GPT RESEARCHER — ROLE

GPT Researcher provides:

- planning/execution patterns,
- crawling,
- multiple retriever backends,
- custom retriever capability,
- MCP capability,
- academic retrieval options,
- report-oriented research infrastructure.

Its role in Neosis is:

```text
secondary reusable research/retrieval capability
```

Use the specific mature capability required.

Do not embed the entire GPT Researcher architecture inside Neosis merely because it contains useful retrievers.

---

# 27. NO THREE-SUPERVISOR ARCHITECTURE

The following architecture is prohibited:

```text
Neosis Supervisor
    |
    +--> Open Deep Research Supervisor
    |
    +--> STORM Supervisor
    |
    +--> GPT Researcher Supervisor
```

This causes:

- duplicated planning,
- duplicated retrieval,
- conflicting research paths,
- inconsistent provenance,
- unnecessary cost,
- difficult cancellation,
- ambiguous state ownership.

Target composition:

```text
Neosis Research Engine
        |
        +--> optional strategy layer
        |       |
        |       +--> STORM capability
        |
        +--> primary execution layer
        |       |
        |       +--> Open Deep Research
        |
        +--> retrieval/tool layer
                |
                +--> GPT Researcher retrievers
                +--> academic retrievers
                +--> web retrievers
                +--> MCP
```

The exact composition is still subject to Phase 1 verification.

---

# 28. UPSTREAM OWNERSHIP

Upstream code remains upstream-owned.

If source-level integration is required, isolate it under a clearly identified vendor/third-party convention such as:

```text
third_party/
    open-deep-research/
```

For each upstream system record:

```text
repository
revision
version
license
retrieval date
local modifications
patch reason
```

Do not silently copy upstream source into:

```text
app/services/
```

---

# 29. UPSTREAM PATCH POLICY

An upstream patch is allowed only when:

```text
1. Adapter-only integration is technically insufficient.
2. The exact upstream code was inspected.
3. The patch is minimal.
4. The patch is isolated.
5. The patch is documented.
6. A regression test exists.
7. The pinned revision is recorded.
```

Document:

```text
upstream file
original behavior
required behavior
why adapter-only integration was insufficient
exact modification
maintenance impact
```

---

# 30. UPSTREAM REVISION REGISTRY

Create:

```text
docs/CH3_UPSTREAM_REVISION.md
```

or the repository-equivalent.

It must track at least:

```text
Open Deep Research
    repository
    revision
    archive status
    license
    local patches

STORM
    repository
    version/revision
    license
    local patches

GPT Researcher
    repository
    version/revision
    license
    local patches
```

Never use:

```text
latest
main
floating branch
```

as the only reproducibility mechanism.

---

# 31. RETRIEVER ABSTRACTION

Research Mode must have a provider-neutral retriever boundary.

Conceptually:

```text
ResearchRetriever
    + search(...)
    + retrieve(...)
    + metadata(...)
    + health(...)
```

Potential families:

```text
WebSearchRetriever
AcademicRetriever
ArxivRetriever
PubMedRetriever
SemanticScholar/OpenAlex-style retriever
MCPRetriever
CustomRetriever
```

The exact implementation should follow the existing repository and selected upstream libraries.

The planner should not know provider-specific HTTP details.

---

# 32. RETRIEVER RESPONSIBILITY BOUNDARY

Retriever adapters own:

- provider communication,
- provider authentication,
- query execution,
- raw result parsing,
- provider-specific errors.

The Research Engine owns:

- retriever selection,
- policy,
- deduplication,
- source normalization,
- evidence normalization,
- provenance,
- workspace access,
- usage accounting.

Do not put planning logic into every retriever.

Do not put provider HTTP logic into the planner.

---

# 33. ACADEMIC RETRIEVAL

Research Mode must have a first-class academic path.

The architecture must support configured academic providers such as:

```text
ArXiv
PubMed / PubMed Central
Semantic Scholar / OpenAlex-like providers
other verified scholarly sources
```

GPT Researcher currently documents ArXiv and PubMed Central retrieval support.

Open Deep Research documentation includes academic retrieval options.

The exact enabled providers must be selected from verified upstream capabilities and product constraints.

Academic retrieval is not merely:

```text
web search + "paper"
```

It requires provider-aware metadata and provenance.

---

# 34. MCP RESEARCH

Research Mode may use MCP when it materially improves research capability.

Upstream systems may provide MCP support.

Neosis owns the policy:

```text
which servers are allowed
which workspaces may use them
which credentials are available
which operations are allowed
whether outputs may be persisted
```

Upstream runtimes may execute MCP calls.

They do not own Neosis authorization.

---

# 35. MCP SECURITY

MCP secrets must never be placed in:

```text
prompts
evidence
graph properties
memory
citations
normal logs
```

A document or research result must not be able to grant itself a new MCP permission.

Tool access is policy-controlled.

---

# 36. RESEARCH REQUEST CONTRACT

The existing public request begins at:

```text
app/api/routes/workspaces.py
```

with:

```text
ResearchRequest
    objective
```

The route remains engine-neutral.

Conceptually:

```text
ResearchRequest
    workspace
    objective
    optional product policy/configuration
```

Do not expose upstream internal state as the public contract.

Avoid public API dependence on:

```text
OpenDeepResearchState
StormState
GPTResearcherState
```

---

# 37. RESEARCH CONFIGURATION

Research configuration should represent stable Neosis policy concepts.

Potential dimensions:

```text
research_depth
research_breadth
max_iterations
max_concurrency
retriever_policy
academic_policy
mcp_policy
model_policy
token_budget
time_budget
cost_budget
citation_policy
source_quality_policy
workspace_source_policy
output_policy
```

The exact schema should be repository-consistent.

A Research Run must retain enough configuration provenance to explain how it was executed.

Do not rely solely on current global configuration.

---

# 38. ENGINE SELECTION

The product should expose logical research strategies rather than implementation names where possible.

Examples:

```text
default
fast
deep
academic
structured
```

The logical strategy may map to:

```text
Open Deep Research
STORM-assisted planning
specific retriever policies
model policies
```

Do not force the public product to depend on one upstream name.

---

# 39. EVIDENCE MUST BE FIRST-CLASS

The current prototype stores evidence as strings.

That is insufficient.

Target concept:

```text
ResearchEvidence
```

An evidence item should identify, where available:

```text
evidence_id
run_id
task_id
workspace_id
source_id/reference
source_url
source_snapshot/reference
retrieval_provider
retrieval_query
retrieved_at
content
content locator
checksum/fingerprint
quality/status
provenance metadata
```

The schema should remain minimal and extensible.

Do not make every provider-specific field mandatory.

---

# 40. EVIDENCE IDENTITY

Evidence identity must not depend on search result positions.

Do not use:

```text
result [3]
array index
LLM-generated citation number
```

as canonical IDs.

A conceptual identity may be derived from:

```text
source identity
+
snapshot/version
+
content fingerprint
+
locator
```

The exact algorithm can evolve.

---

# 41. SOURCE NORMALIZATION

External sources should be normalized into canonical Neosis source concepts.

Potential metadata:

```text
canonical_url
provider
title
publisher
author
publication date
retrieval date
mime/type
content fingerprint
external provider identifier
```

Provider IDs remain metadata.

They must not replace canonical Neosis identity.

---

# 42. USER-PROVIDED VS EXTERNAL SOURCES

Research may consume:

```text
USER_PROVIDED
WORKSPACE_CANONICAL
EXTERNAL_WEB
ACADEMIC
MCP
SYSTEM_REFERENCE
```

The exact enum should follow repository conventions.

The distinction is important for:

- authorization,
- trust,
- retention,
- citation,
- graph promotion,
- memory promotion,
- evaluation.

Do not flatten all sources into one undifferentiated pool.

---

# 43. SOURCE SNAPSHOT RULE

Neosis already distinguishes:

```text
Source
SourceSnapshot
```

Chapter 3 should preserve this idea for research evidence.

The system should distinguish:

```text
logical source
observed snapshot
transient retrieval response
```

Evidence should reference the observed source state where practical.

---

# 44. RAW UPSTREAM OUTPUT RULE

Raw upstream output must never become canonical state directly.

Prohibited:

```text
upstream result
    ->
PostgreSQL JSON
```

without normalization.

Prohibited:

```text
upstream graph
    ->
Neo4j
```

without canonical provenance.

Required:

```text
raw upstream output
    ->
normalized evidence/artifact
    ->
canonical persistence
```

---

# 45. EVIDENCE NORMALIZATION PIPELINE

Required flow:

```text
upstream raw result
        |
        v
source normalization
        |
        v
evidence extraction
        |
        v
deduplication
        |
        v
canonical identity
        |
        v
tagging
        |
        v
provenance
        |
        v
canonical persistence
```

Only after this point may evidence be treated as product-level research input.

---

# 46. CLAIM VS EVIDENCE

A claim is not evidence.

```text
Evidence
    = what a source actually provided

Claim
    = normalized statement derived from evidence

Synthesis
    = higher-level interpretation from claims

Report
    = user-facing presentation
```

These layers must remain distinguishable.

Do not persist only the final report.

---

# 47. CLAIM PROVENANCE

Claims should point to one or more evidence IDs.

Evidence points to source identity and retrieval metadata.

Conceptually:

```text
Report
  |
  +--> Claim
         |
         +--> Evidence A
         |      |
         |      +--> Source A / Snapshot A
         |
         +--> Evidence B
                |
                +--> Source B / Snapshot B
```

This is the minimum structure needed for future verification and contradiction detection.

---

# 48. TAGGING MODEL

Normalized research artifacts should carry machine-readable tags.

The taxonomy should support concepts such as:

```text
research
evidence
source
claim
finding
hypothesis
contradiction
synthesis
report
memory_candidate
graph_candidate
academic
web
mcp
user_provided
workspace_derived
external
```

The exact final vocabulary should be a controlled taxonomy.

Do not turn tags into arbitrary free-form strings with no governance.

---

# 49. PROVENANCE STATUS

Important research artifacts should have explicit provenance status.

Possible concepts include:

```text
complete
partial
unresolved
synthetic
user_asserted
external
verified
unverified
```

The exact vocabulary must follow product semantics.

The hard rule is:

> **Never represent incomplete provenance as complete provenance.**

---

# 50. PROVENANCE RECONSTRUCTION

For a representative finding the system should be able to reconstruct:

```text
objective
    ->
research run
    ->
task
    ->
retrieval operation
    ->
source
    ->
snapshot
    ->
evidence
    ->
claim
    ->
report / graph / memory candidate
```

If this chain cannot be reconstructed, the missing link must be explicit.

---

# 51. CITATION IS NOT A SEPARATE GRAPH

Do not create a citation graph.

Citation/provenance is a cross-cutting capability.

The canonical relations belong in:

```text
evidence
source
artifact
claim
report
promotion metadata
```

Neo4j may project provenance relations.

Neo4j is not the only provenance store.

---

# 52. RESEARCH REPORT

A report is a user-facing research artifact.

It should be able to represent:

```text
run identity
objective
status
summary
findings
citations
source references
limitations
warnings
generation metadata
version
```

It is derived from canonical evidence.

It is not canonical source truth.

---

# 53. REPORT VERSIONING

A new report version may be generated because:

```text
new evidence arrived
research was rerun
synthesis changed
source was corrected
user requested refinement
verification changed
```

Do not overwrite old reports without version semantics where product auditability requires history.

---

# 54. RESEARCH OUTPUT KG

Neosis maintains:

```text
Internal KG
    = operational/machine graph

Research Output KG
    = curated/user-visible semantic graph
```

The Research Engine may create graph candidates.

It must not treat Neo4j as canonical storage.

Required pattern:

```text
research finding
    ->
canonical artifact
    ->
validation/promotion
    ->
graph candidate
    ->
Neo4j projection
```

---

# 55. GRAPH CURATION RULE

The Research Output KG should remain useful.

Do not create nodes for:

```text
every sentence
every result index
every search call
every tool call
every temporary model state
```

unless a product requirement explicitly requires it.

The output graph should represent:

```text
important entities
important concepts
meaningful relationships
traceable provenance
```

---

# 56. GRAPH PROVENANCE

Every user-visible graph element produced from research must be traceable to canonical research artifacts.

A graph node or edge must not contain fabricated provenance.

The existing:

```text
app/schemas/graph.py
```

provenance contract can be extended carefully.

---

# 57. MEMORY PROMOTION

Research does not equal memory.

Required flow:

```text
research evidence
    |
    v
claim/finding
    |
    v
validation
    |
    v
memory candidate
    |
    v
promotion policy
    |
    v
Knowledge / Research Memory
```

The existing:

```text
app/services/memory_router.py
```

remains the product-level memory boundary.

Do not write KnowledgeMemory directly from an upstream adapter.

---

# 58. MEMORY TYPE DISTINCTION

Research can produce:

```text
working context
episodic summary
research artifact
knowledge candidate
```

These are different concepts.

In particular:

```text
research evidence != knowledge memory
research report != verified knowledge
```

---

# 59. SCRATCHPAD / WORKING MEMORY

Working Memory and Scratchpad remain product-owned.

Upstream agent state must not automatically become permanent memory.

A user-created scratchpad item must not automatically become an external research source.

Promotion must be explicit.

---

# 60. MEMORY AND GRAPH PROMOTION ARE INDEPENDENT

A research finding may be:

```text
graph-worthy
```

but not:

```text
memory-worthy
```

and vice versa.

Therefore:

```text
research artifact
    |
    +--> memory promotion policy
    |
    +--> graph promotion policy
```

These are independent decisions.

---

# 61. RESEARCH EVENT MODEL

Research needs Neosis-owned lifecycle events.

Conceptual events:

```text
research.started
research.planning
research.task.started
research.task.completed
research.retrieval.started
research.retrieval.completed
research.evidence.added
research.evidence.updated
research.claim.created
research.synthesis.started
research.report.updated
research.graph_candidate.created
research.memory_candidate.created
research.completed
research.partial
research.cancelled
research.failed
```

Exact names must follow repository-wide conventions.

---

# 62. EVENT NORMALIZATION

Required flow:

```text
upstream event
    |
    v
adapter
    |
    v
Neosis ResearchEvent
    |
    v
Redis / pub-sub / SSE
```

Do not expose raw upstream node names or event JSON as the long-term public event contract.

---

# 63. CURRENT WORKER BOUNDARY

The current research worker is:

```text
run_research_agent_job
```

in:

```text
app/workers/tasks.py
```

Chapter 3 should retain asynchronous execution.

The worker should become an execution shell.

Target concept:

```text
run_research_agent_job
    |
    v
ResearchService
    |
    v
ResearchEngine
    |
    v
upstream runtimes
```

Do not move deep-research implementation into the worker.

---

# 64. CURRENT API BOUNDARY

The existing public route:

```text
POST /workspaces/{workspace_id}/research
```

should remain a Neosis route unless an explicit API migration is approved.

The route should handle:

```text
authentication
authorization
validation
ResearchRun creation
job scheduling
immediate response
```

It should not construct:

```text
OpenDeepResearch(...)
STORM(...)
GPTResearcher(...)
```

inside the endpoint.

---

# 65. RUN ID VS JOB ID

The current implementation uses a worker `job_id`.

Chapter 3 must establish canonical `run_id`.

The distinction is:

```text
job_id
    = infrastructure execution identifier

run_id
    = product research identity
```

A run may have multiple jobs due to:

```text
retry
recovery
continuation
worker restart
```

Do not make product history dependent on one ephemeral job ID.


# 66. RESEARCH EXECUTION VS RESEARCH ARTIFACTS

A research runtime may produce transient execution material:

```text
messages
tool outputs
search results
agent thoughts
temporary summaries
intermediate outlines
```

These are not automatically canonical.

The canonical layer should preserve only information required for:

```text
user experience
recovery
provenance
evaluation
auditing
future verification
versioning
```

The implementation should avoid copying entire upstream state trees into PostgreSQL.

---

# 67. RAW TRACE RETENTION

Raw upstream traces may be useful for debugging.

They must remain separate from canonical research state.

Potential retention locations include:

```text
object storage
observability backend
debug artifact storage
```

If raw traces are retained, define:

```text
retention
security
access control
redaction
size limits
workspace scope
```

Do not make raw traces the only record of research state.

---

# 68. SOURCE-OF-TRUTH HIERARCHY

The final system has a strict ownership hierarchy.

```text
PostgreSQL
    |
    +--> canonical ResearchRun / Task / Evidence / Artifact metadata

S3
    |
    +--> immutable large source/artifact blobs

Redis / Arq
    |
    +--> job execution / pub-sub / transient transport

Upstream runtime
    |
    +--> research execution state

Neo4j
    |
    +--> graph projection

Search/Academic/MCP providers
    |
    +--> external information
```

No upstream service database becomes canonical merely because it is convenient.

---

# 69. CANONICAL WRITE RULE

The canonical write path is:

```text
API / worker
    ->
ResearchService
    ->
ResearchEngine
    ->
upstream runtime
    ->
normalized output
    ->
canonical repository
```

The inverse direction is not allowed:

```text
upstream database
    ->
direct canonical mutation
```

unless an explicit reconciliation adapter is required.

---

# 70. DATABASE OWNERSHIP

PostgreSQL remains canonical for:

```text
ResearchRun
ResearchTask
ResearchEvidence
ResearchSource metadata
ResearchArtifact metadata
ResearchReport metadata
ResearchUsage
durable ResearchEvent records where required
promotion status
version metadata
```

PostgreSQL should not store giant raw upstream execution trees solely because they are available.

Large immutable content should remain in object storage when appropriate.

---

# 71. NO UPSTREAM DATABASE COUPLING

Open Deep Research, STORM, GPT Researcher, or their dependencies may have their own storage assumptions.

Do not make those databases mandatory for the core Neosis research data model unless there is a concrete reason.

Prefer:

```text
upstream runtime
    ->
adapter
    ->
Neosis persistence
```

The product must not require users to understand upstream storage systems.

---

# 72. RESEARCH RETRIEVAL POLICY

The Research Engine owns policy over retrievers.

A policy may consider:

```text
query type
topic domain
academic requirement
source quality
workspace restrictions
provider health
provider cost
provider latency
research strategy
```

The policy must be deterministic enough to debug.

Do not hide routing inside an LLM prompt.

---

# 73. RETRIEVER REGISTRY

The integration should maintain a central retriever registry or equivalent.

Conceptually:

```text
RetrieverRegistry
    |
    +--> web
    +--> academic
    +--> arxiv
    +--> pubmed
    +--> custom
    +--> mcp
```

The registry should provide:

```text
capability metadata
health
configuration
selection
```

Do not make each upstream engine maintain an independent Neosis provider registry.

---

# 74. RETRIEVER PROVIDER IDENTITY

Every evidence item should be able to identify the retriever that produced it.

Examples:

```text
tavily
google
brave
arxiv
pubmed
custom
mcp:<server>
```

These are metadata values, not canonical source identities.

---

# 75. NO HIDDEN PROVIDER PREFERENCE

The engine must not silently hardcode one search provider as the universal source.

Tavily may remain an enabled provider.

However:

```text
Tavily != Research Engine
```

Provider choice must be observable.

---

# 76. PROVIDER HEALTH

Provider state should distinguish:

```text
available
degraded
rate_limited
misconfigured
unavailable
disabled
```

A disabled provider must not be retried indefinitely.

Provider failure should trigger policy-defined behavior:

```text
fallback
partial
failure
```

---

# 77. PROVIDER FALLBACK

A provider-level fallback is allowed when it is:

```text
policy-controlled
observable
provenance-preserving
budget-aware
```

For example:

```text
primary web provider
    ->
secondary web provider
```

is valid.

The actual run should record both the primary failure and the fallback provider.

Do not hide provider fallback from the run record.

---

# 78. ENGINE FALLBACK

Engine-level fallback is more significant.

If:

```text
Open Deep Research
```

cannot execute, the system may select an alternate configured research strategy only if product policy permits.

The run must record:

```text
requested strategy
actual engine
actual engine revision
reason for fallback
```

There must be no silent switch to the legacy prototype.

---

# 79. NO SILENT LEGACY FALLBACK

Prohibited:

```text
new Research Engine fails
    ->
legacy ResearchModeOrchestrator silently executes
```

Allowed:

```text
new engine fails
    ->
retry
    ->
configured alternate upstream capability
    ->
PARTIAL / FAILED
```

If the legacy engine is intentionally used for rollback:

```text
engine = legacy
```

must be visible in execution metadata.

---

# 80. RESEARCH CONTEXT SELECTION

Research context may include:

```text
user objective
selected workspace sources
approved memory
prior research artifacts
fresh external evidence
```

The context should be assembled by explicit policy.

Do not automatically include:

```text
all six memory systems
all workspace knowledge
all historical research
```

in every prompt.

---

# 81. MEMORY ROUTER BOUNDARY

The current:

```text
app/services/memory_router.py
```

remains responsible for memory routing.

The Research Engine may request:

```text
selected memory context
```

through a product-level interface.

It should not directly execute SQL queries against:

```text
KnowledgeMemory
EpisodicMemory
```

or other memory tables.

---

# 82. CURRENT MEMORY CONTEXT IMPLEMENTATION

The current `MemoryRouterService.build_context()` provides:

```text
token estimates
budget
eviction
priority
```

This is useful as a shared context-budget primitive.

It must not become the canonical research state.

Research evidence remains:

```text
ResearchEvidence
```

even if a temporary context bundle represents it as:

```text
MemoryItem
```

inside a prompt.

---

# 83. TOKEN GOVERNANCE

Research execution must be bounded by explicit token policy.

At minimum support conceptual controls for:

```text
input token budget
output token budget
per-task budget
per-run budget
compression budget
```

The exact implementation depends on the selected runtime/provider.

When precise usage is unavailable:

```text
estimated
```

must be distinguished from:

```text
reported
```

---

# 84. CONTEXT GOVERNANCE

Long research creates context growth.

The system should use:

```text
compression
summarization
evidence selection
task-local context
```

where provided by the upstream runtime.

Do not reimplement a competing compression algorithm in Neosis unless the upstream runtime cannot provide the required product boundary.

---

# 85. TOKEN BUDGET DOES NOT MEAN EVIDENCE DELETION

Budget reduction must not silently delete canonical evidence.

Correct:

```text
canonical evidence
    remains persisted

context builder
    selects bounded subset
```

Incorrect:

```text
budget exceeded
    ->
delete old evidence
```

Canonical storage and prompt context are separate concerns.

---

# 86. TIME BUDGET

Each Research Run should have a maximum duration policy.

The policy may be:

```text
default time budget
workspace override
plan-specific budget
system hard cap
```

A timeout should produce explicit state.

Do not leave a run in:

```text
RESEARCHING
```

forever.

---

# 87. CONCURRENCY BUDGET

Concurrency should be bounded at:

```text
run level
task level
provider level
worker level
workspace level
```

Do not trust an upstream planner to respect Neosis infrastructure limits automatically.

The adapter must enforce outer bounds.

---

# 88. BACKPRESSURE

The target flow is:

```text
research request
    ->
queue
    ->
bounded worker execution
    ->
bounded research concurrency
    ->
bounded provider concurrency
```

Do not introduce an additional queue system.

Reuse Redis/Arq unless a documented scale requirement necessitates another system.

---

# 89. RATE LIMITING

The Research Engine must respect:

```text
provider rate limits
workspace quota
user quota
system quota
```

429 responses should be represented as:

```text
RATE_LIMITED
```

with retry metadata where applicable.

Do not immediately retry indefinitely.

---

# 90. COST BUDGET

Research may be significantly more expensive than Ground.

Support a cost budget concept.

Potential policy levels:

```text
per request
per run
per workspace/day
per user/day
```

The actual quota model should use existing quota infrastructure where possible.

---

# 91. USAGE ACCOUNTING

Every run should record enough information to answer:

```text
How many model calls?
How many input tokens?
How many output tokens?
How many search requests?
How many retrieved documents?
How many MCP calls?
How long did it run?
Which provider incurred cost?
```

Usage records should be append-friendly and aggregatable.

---

# 92. USAGE VS BILLING

Usage accounting is not necessarily billing.

Do not invent a billing subsystem in Chapter 3 merely because cost data exists.

The current objective is:

```text
measurement
budgeting
optimization
```

Billing remains a separate product concern unless already established elsewhere.

---

# 93. RESEARCH EVENT CORRELATION

Every important event should carry:

```text
event_id
workspace_id
run_id
task_id where applicable
timestamp
event type
```

and where available:

```text
request_id
upstream execution ID
retriever
provider
model
```

This is required for debugging.

---

# 94. TRACE CORRELATION

The preferred trace hierarchy is:

```text
request_id
   |
   +--> run_id
          |
          +--> task_id
                 |
                 +--> upstream execution
                        |
                        +--> retriever/tool call
```

Do not log sensitive source contents merely to make traces easier to interpret.

---

# 95. LOGGING RULE

Do not log:

```text
API keys
MCP secrets
private credentials
full private source documents
unredacted auth headers
```

unless an explicit audited debugging system permits it.

Use structured identifiers:

```text
run_id
task_id
workspace_id
provider
status
latency
error class
```

---

# 96. CACHING

Caching may be used for:

```text
source metadata
retrieval results
provider metadata
research intermediate outputs
```

but:

> A cache is never canonical research state.

Canonical evidence must survive cache eviction.

---

# 97. CACHE SCOPE

Private research cache keys must include sufficient scope.

Do not use:

```text
query_hash
```

alone when private workspace information may be involved.

Consider:

```text
workspace_id
source policy
configuration version
retriever
query hash
```

---

# 98. SOURCE FRESHNESS

Research evidence must preserve temporal information where available.

Distinguish:

```text
publication date
source modification date
retrieval date
research run date
```

These are not interchangeable.

---

# 99. TEMPORAL RESEARCH

The Research Run should preserve temporal constraints such as:

```text
latest
as of date
during period
before event
after event
historical snapshot
```

The research planner may convert them into queries, but the canonical run should preserve the original semantics.

Do not silently remove temporal requirements.

---

# 100. EXTERNAL CONTENT MUTABILITY

Web pages can change.

Evidence should preserve enough information to explain what was observed:

```text
retrieved_at
source URL
excerpt
content fingerprint
locator
```

where technically available.

Do not imply that current page content is identical to historic retrieved content.

---

# 101. SOURCE QUALITY

Source quality and citation existence are separate.

A source can be:

```text
citable
```

without being:

```text
authoritative
```

Potential metadata:

```text
official
primary
academic
secondary
aggregator
unknown
```

The final taxonomy should be explicit and evidence-based.

Do not hardcode subjective rankings into foundational source identity.

---

# 102. NO HIDDEN SOURCE PREFERENCE

Do not silently privilege:

```text
one publisher
one search provider
one academic provider
```

unless the preference is an explicit policy.

Provider choices must be observable.

---

# 103. CLAIM SUPPORT REQUIREMENT

A user-visible research claim should be supported by evidence when it is presented as factual research.

Possible statuses:

```text
supported
partially_supported
unsupported
conflicting
uncertain
```

The exact vocabulary should be chosen during detailed implementation.

The core requirement is to distinguish unsupported claims from supported evidence.

---

# 104. CONTRADICTION PRESERVATION

If two sources disagree:

```text
Source A -> X = 10
Source B -> X = 12
```

do not silently convert them into one value.

The canonical model must preserve:

```text
claim A
claim B
evidence A
evidence B
source identity
resolution status
```

The full contradiction engine may be implemented in a later chapter.

Chapter 3 must retain the information needed for it.

---

# 105. CONTRADICTION STATUSES

Possible conceptual states:

```text
unresolved
contextual
resolved
superseded
source-disputed
```

Do not pretend the system has resolved a contradiction merely because the LLM selected one answer.

---

# 106. VERIFICATION HOOK

Chapter 3 should preserve enough structure for later:

```text
research critic
claim verification
citation verification
source-quality scoring
contradiction detection
fact checking
```

Do not flatten evidence into a report and delete its lineage.

---

# 107. ACADEMIC METADATA

When academic providers expose metadata, preserve relevant fields such as:

```text
title
authors
venue
publication date
DOI
ArXiv ID
PubMed/PMC ID
URL
retrieval timestamp
```

Never fabricate identifiers.

Unknown values remain unknown.

---

# 108. WEB METADATA

Web evidence should preserve, where available:

```text
canonical URL
title
publisher/domain
retrieval time
provider
query
content fingerprint
```

Do not invent canonical URLs from incomplete provider results.

---

# 109. RETRIEVAL QUERY PROVENANCE

Research evidence should retain:

```text
retriever
query
query variant
retrieved_at
```

This matters because one source can be found for multiple independent reasons.

Do not flatten the research history into one source list.

---

# 110. MULTI-QUERY RESEARCH

A mature research run may perform many queries.

The canonical relationship should be:

```text
ResearchTask
    ->
ResearchQuery
    ->
Retriever
    ->
Evidence
```

A separate query entity may be used if the repository requires it.

If not, query provenance can be embedded in task/evidence metadata.

The architectural requirement is traceability.

---

# 111. EVIDENCE WINDOWING

Retrieved documents may be too large for relational inline storage.

Use:

```text
source/object storage
+
locator
+
excerpt
+
fingerprint
```

rather than duplicating full source content into every evidence record.

The exact storage strategy should follow existing object-store conventions.

---

# 112. OBJECT STORAGE RULE

Use:

```text
app/services/storage.py
```

or the repository's existing storage abstraction for large immutable content.

Do not create direct S3 clients in every research adapter.

This preserves portability and reduces infrastructure duplication.

---

# 113. IMMUTABILITY RULE

Research observations that represent what was actually retrieved should be append-oriented.

In particular:

```text
retrieval evidence
retrieval metadata
source snapshot references
execution events
usage observations
```

should not be rewritten merely because a source later changes.

Corrections should create explicit new versions/corrections where needed.

---

# 114. REPORT CORRECTION

Reports can be revised.

The evidence should remain historically accurate.

Correct:

```text
new report version
    ->
same evidence or new evidence set
```

Incorrect:

```text
mutate old evidence
    ->
pretend historic report used the new evidence
```

---

# 115. RESEARCH VERSIONING

Research artifacts should align with the existing Neosis version model.

Do not invent an unrelated version-control system.

Conceptually:

```text
Workspace version
    |
    +--> research artifact state
```

The exact integration should be derived from the live workspace commit model.

---

# 116. WORKSPACE VERSION ATTACHMENT

A research run should record the relevant workspace version/commit when workspace data was used.

This protects against:

```text
source changed while research was executing
```

and supports reproducibility.

Do not silently use the latest workspace state after a run started.

---

# 117. SOURCE CHANGES DURING RUN

If a workspace source changes while a run is active, the run should continue referencing the source snapshot actually observed.

If the product intentionally refreshes the source during research, the refresh must be a recorded event.

---

# 118. RESEARCH-TO-GROUND BOUNDARY

Research output does not automatically become Ground truth.

Correct:

```text
Research artifact
    ->
explicit promotion
    ->
Knowledge / approved source
    ->
Ground visibility
```

Incorrect:

```text
Research report
    ->
automatic Ground source
```

This prevents autonomous research claims from silently becoming trusted Ground information.

---

# 119. GROUND-TO-RESEARCH BRIDGE

If Research Mode consumes Ground/workspace sources, it should do so through canonical Neosis source/evidence interfaces.

Do not let the research planner query Open Notebook's internal database.

The bridge should be:

```text
Research policy
    ->
selected workspace sources
    ->
canonical evidence/source service
    ->
research context
```

---

# 120. RESEARCH MEMORY

Research-specific durable memory may be represented by the existing memory taxonomy.

It must observe:

```text
workspace ownership
provenance
versioning
promotion
status
```

Do not create a separate Research Memory database disconnected from Neosis.

---

# 121. EPISODIC MEMORY

A completed research run may produce an episodic summary.

That summary should identify:

```text
run_id
workspace_id
objective
summary
important events
```

It remains a summary.

It does not replace evidence.

---

# 122. KNOWLEDGE MEMORY PROMOTION

The existing KnowledgeMemory model already supports:

```text
provenance
confidence
tags
entities
domain
version
```

Research promotion may populate these concepts.

But promotion must be explicit.

A report must not automatically become KnowledgeMemory.

---

# 123. RESEARCH GRAPH SERVICE

A dedicated responsibility may exist under:

```text
app/services/research_graph.py
```

or the repository equivalent.

It should own:

```text
candidate extraction
graph validation
promotion
projection dispatch
```

It should not own:

```text
research retrieval
research planning
database-wide memory access
```

---

# 124. RESEARCH MEMORY SERVICE

A dedicated responsibility may exist under:

```text
app/services/research_memory.py
```

or repository equivalent.

It should own:

```text
candidate generation
promotion rules
provenance attachment
```

It should delegate persistence to existing memory repositories.

---

# 125. PROVENANCE SERVICE

A dedicated service may exist under:

```text
app/services/research_provenance.py
```

It should centralize:

```text
evidence lineage
source resolution
claim support
citation normalization
provenance status
```

Do not implement separate incompatible provenance semantics in each upstream adapter.

---

# 126. NORMALIZATION SERVICE

A dedicated service may exist under:

```text
app/services/research_normalization.py
```

It should normalize:

```text
raw retrieval result
raw upstream artifact
raw upstream report
raw citation metadata
```

into canonical Neosis representations.

Unknown useful provider metadata may live in controlled metadata.

---

# 127. EVENT ADAPTER

A dedicated responsibility may live under:

```text
app/integrations/research_engine/events.py
```

It maps:

```text
upstream events
    ->
Neosis events
```

It must not simply proxy arbitrary JSON.

---

# 128. ERROR ADAPTER

A dedicated responsibility may live under:

```text
app/integrations/research_engine/errors.py
```

It maps:

```text
upstream exception
    ->
stable Neosis error
```

The public API should not leak:

```text
library stack traces
provider internals
upstream object names
```

---

# 129. HEALTH ADAPTER

A Research Engine health boundary should expose:

```text
engine availability
retriever availability
provider health
MCP health
configuration status
```

Do not make every health check perform an expensive full research run.

---

# 130. SERVICE CONFIGURATION

Configuration should be namespaced.

Conceptual examples:

```text
RESEARCH_ENGINE_ENABLED
RESEARCH_ENGINE_DEFAULT_STRATEGY
RESEARCH_ENGINE_TIMEOUT_SECONDS
RESEARCH_ENGINE_MAX_CONCURRENCY
RESEARCH_ENGINE_MAX_TOKENS
RESEARCH_ENGINE_MAX_COST
RESEARCH_ENGINE_MAX_RESEARCH_TIME
RESEARCH_ENGINE_ACADEMIC_ENABLED
RESEARCH_ENGINE_MCP_ENABLED
```

Exact names must follow project configuration conventions.

Do not hardcode production secrets.

---

# 131. FEATURE FLAGS

Potential flags:

```text
research_engine_enabled
shadow_research_enabled
storm_strategy_enabled
gpt_researcher_retrievers_enabled
academic_retrieval_enabled
mcp_research_enabled
legacy_research_enabled
```

Centralize flags.

Do not scatter conditional logic throughout the repository.

---

# 132. WORKSPACE-SCOPED RESEARCH

Every ResearchRun must belong to:

```text
workspace_id
owner_id
```

Every descendant object must be traceable to its workspace.

This includes:

```text
tasks
evidence
sources
artifacts
reports
events
memory candidates
graph candidates
usage
```

---

# 133. AUTHORIZATION ORDER

The request flow must be:

```text
authenticated actor
    |
    v
workspace authorization
    |
    v
research quota/policy
    |
    v
ResearchRun creation
    |
    v
execution
```

Do not begin upstream research before workspace authorization succeeds.

---

# 134. CLIENT CANNOT SELECT INTERNAL IDs

The user-facing API should accept:

```text
workspace_id
run_id
logical source IDs
```

not:

```text
upstream session ID
retriever provider object ID
internal graph node ID
MCP runtime ID
```

The server resolves internal mappings.

---

# 135. TENANT-SCOPED EVENT STREAMS

A research stream must be scoped to:

```text
workspace_id
run_id
owner
authorization
```

Do not allow a client to subscribe to:

```text
research:{arbitrary_job_id}
```

without authorization.

---

# 136. RESEARCH STATUS API

The product should provide a stable status representation containing concepts such as:

```text
run status
current task
progress
evidence count
artifact count
report state
warnings
errors
usage summary
timestamps
```

The final endpoint path should follow existing API conventions.

---

# 137. PROGRESS SEMANTICS

Progress should be meaningful.

Prefer:

```text
planning
researching
collecting evidence
validating
synthesizing
finalizing
```

over raw:

```text
node_7
tool_23
LangGraphStep
```

The UI must not be coupled to upstream execution topology.

---

# 138. STREAMING

The product may expose SSE/streaming.

The architecture should normalize:

```text
upstream progress
    ->
Neosis event
    ->
SSE
```

The existing Redis job-stream approach may be reused.

If direct streaming is added, preserve a stable Neosis event contract.

---

# 139. CANCELLATION

Cancellation is first-class.

Target flow:

```text
Neosis cancellation
    ->
stop scheduling new work
    ->
interrupt upstream execution where supported
    ->
persist completed evidence
    ->
mark CANCELLED or PARTIAL
```

Do not delete collected evidence.

---

# 140. PARTIAL RESEARCH

Example:

```text
5 tasks planned
3 completed
1 failed
1 not started
```

This should produce explicit state:

```text
PARTIAL
```

with the successful evidence retained.

Do not manufacture a complete conclusion from incomplete research without clear status.

---

# 141. RETRY POLICY

Retry only operations that are safe.

Retry candidates:

```text
transient provider failure
network timeout
429 rate limit with backoff
idempotent retrieval
worker delivery failure
```

Do not blind-retry:

```text
invalid requests
schema failures
unsupported provider configurations
non-idempotent external mutations
```

---

# 142. AMBIGUOUS OUTCOME

If an upstream operation may have executed before timing out:

```text
attempt
    ->
timeout/ambiguous
    ->
reconcile
    ->
reuse or retry
```

Do not automatically duplicate the operation.

This is especially important for:

```text
remote job creation
external artifact creation
MCP side effects
```

Research should prefer read-only operations, but the rule still applies where side effects exist.

---

# 143. IDEMPOTENCY

Canonical identities:

```text
run_id
task_id
evidence_id
artifact_id
event_id
```

must be generated and owned by Neosis.

Provider IDs remain external references.

A retry should reuse canonical identities where semantically appropriate.

---

# 144. EVIDENCE DEDUPLICATION

Different queries can return:

```text
same URL
same paper
same content
same provider document
```

Deduplication may use:

```text
canonical URL
normalized URL
content fingerprint
provider identifier
snapshot checksum
```

The algorithm may evolve.

The invariant is:

> Research must not create unlimited duplicate evidence merely because different queries found the same source.

---

# 145. SOURCE RETRIEVAL VS SOURCE TRUST

Retrieval establishes:

```text
found by a provider
```

It does not establish:

```text
true
authoritative
verified
```

Trust status must be represented separately.

---

# 146. SOURCE QUALITY POLICY

Potential quality dimensions:

```text
primary vs secondary
academic vs non-academic
official vs unofficial
publisher quality
recency
source diversity
corroboration
```

The policy must be explicit.

Do not bake subjective source rankings into low-level retrievers.

---

# 147. REPORT QUALITY VS RESEARCH QUALITY

A report can be:

```text
well-written
```

and still:

```text
poorly researched
```

Therefore evaluation must separately measure:

```text
research completeness
evidence quality
claim support
citation quality
report readability
```

Do not use a single “LLM score” as the sole gate.

---

# 148. QUALITY DIMENSIONS

At minimum support measurement of:

```text
planning quality
retrieval relevance
evidence coverage
source diversity
research breadth
research depth
claim support
citation correctness
citation completeness
contradiction coverage
academic coverage
freshness
report quality
```

---

# 149. RESEARCH DEPTH

Research depth represents how far the system investigates beyond first-order retrieval.

Signals may include:

```text
iterative queries
follow-up questions
cross-source verification
secondary evidence
contradiction investigation
```

Depth must remain budget-bounded.

---

# 150. RESEARCH BREADTH

Research breadth represents coverage across relevant dimensions.

It should not simply equal:

```text
number of web pages
```

A hundred redundant sources are not equivalent to broad research.

---

# 151. SOURCE DIVERSITY

Useful research often requires multiple source classes.

Potential diversity dimensions:

```text
publisher
domain
source type
academic vs web
primary vs secondary
geography
date
```

The exact metric can be refined during evaluation.

---

# 152. CURRENT-INFORMATION RESEARCH

The Research Engine must be able to distinguish current-information tasks from historical tasks.

Where current information is requested:

```text
retrieval date
provider
source timestamp
```

become especially important.

Do not rely on a training-data-only answer path when external research is required.

---

# 153. HISTORICAL RESEARCH

Historical research must preserve:

```text
publication dates
event dates
retrieval dates
```

The engine should not confuse source publication date with current page availability.

---

# 154. RESEARCH OBJECTIVE CONSTRAINTS

Research configuration should support constraints such as:

```text
source domain restriction
academic-only
official-only
date range
language
region
maximum depth
maximum cost
```

These are policy inputs.

Do not implement them by prompt text alone when the provider/runtime offers an actual policy mechanism.

---

# 155. USER SOURCE RESTRICTION

If a user asks:

```text
use only my uploaded sources
```

the Research Engine must obey this as a source policy.

This is distinct from Ground Mode.

Research Mode can be workspace-aware while still using research orchestration.

---

# 156. EXTERNAL-ONLY RESEARCH

If the user asks for external research only, workspace-private evidence must not be injected simply because it exists.

Source policy must be explicit.

---

# 157. MIXED RESEARCH

A mixed mode may use:

```text
workspace sources
+
external sources
```

but the final report should retain source type distinctions.

Do not make an internal workspace document look like an external independent source.

---

# 158. REPORT SOURCE DISCLOSURE

The report should be able to expose or summarize:

```text
source types
citation set
limitations
```

The exact UI is separate.

The canonical report artifact must preserve enough metadata for the UI.

---

# 159. NO SOURCE FABRICATION

If a report cites an item:

```text
the item must exist as canonical evidence
```

If an upstream model produces a citation not backed by a retriever result, mark it unresolved or reject it according to the citation contract.

Do not create fake source objects.

---

# 160. FINAL SYNTHESIS GATE

Final synthesis must consume:

```text
canonical evidence
```

rather than raw provider payloads that bypass normalization.

Required conceptual flow:

```text
retrieval
    ->
canonical evidence
    ->
claims
    ->
synthesis
    ->
report
```

This is a hard provenance boundary.

---

# 161. RESEARCH REPORT PERSISTENCE

The report must be persisted as a product artifact.

It must be possible to retrieve it later without rerunning the entire research job.

Report storage may be:

```text
PostgreSQL metadata
+
S3 large content
```

depending on size.

---

# 162. RESEARCH ARTIFACT PERSISTENCE

Artifacts should distinguish at least:

```text
evidence
claim
finding
plan
report
graph candidate
memory candidate
```

Do not store everything as:

```text
artifact.type = "misc"
```

without a controlled vocabulary.

---

# 163. ARTIFACT LIFECYCLE

Artifacts may have states equivalent to:

```text
CREATED
ACTIVE
SUPERSEDED
REJECTED
PROMOTED
ARCHIVED
```

The final state model should follow existing project vocabulary.

---

# 164. ARTIFACT VERSIONING

An artifact update that materially changes its meaning should create a new version.

Do not rewrite evidence to make an updated report appear unchanged.

---

# 165. WORKSPACE COMMIT INTEGRATION

If a report or knowledge artifact becomes part of a workspace commit, its promotion should be explicit.

Do not automatically update workspace commits simply because research completes.

Research output can exist independently until the user/system explicitly promotes it.

---

# 166. USER PROMOTION

Promotion actions may include:

```text
save to knowledge
add to research memory
add to graph
attach to workspace
create workspace commit
```

These should be separate from raw research execution.

---

# 167. RESEARCH-ONLY ARTIFACTS

A user should be able to inspect research artifacts without automatically mutating the durable workspace knowledge model.

This is important for exploratory research.

---

# 168. NO AUTOMATIC KNOWLEDGE POLLUTION

Do not turn research into a continuous firehose of KnowledgeMemory writes.

Memory should represent durable, intentionally retained knowledge.

Research may be exploratory.

---

# 169. NO AUTOMATIC GRAPH POLLUTION

Do not turn every transient research entity into a Research Output KG node.

Graph promotion must be selective.

---

# 170. INTERNAL KG USAGE

Internal KG may contain operational relationships such as:

```text
ResearchRun -> Task
Task -> Evidence
Evidence -> Source
Run -> Artifact
Artifact -> Promotion
```

But it should remain an operational projection, not the only place those relationships exist.

---

# 171. GRAPH REPROJECTION

If Neo4j is lost or rebuilt:

```text
canonical PostgreSQL research state
    ->
graph projection
```

must be possible.

This is why canonical state must be stored outside Neo4j.

---

# 172. MEMORY REPROJECTION

If a memory projection needs repair:

```text
canonical research artifact
    ->
promotion record
    ->
memory layer
```

must remain traceable.

---

# 173. SOURCE REPROJECTION

If external source metadata or derived source artifacts require repair:

```text
canonical evidence/source references
    ->
reconciliation
```

must be possible.

---

# 174. RESEARCH RECOVERY

The system should recover from:

```text
FastAPI restart
worker restart
Redis restart
upstream runtime restart
provider outage
database failure
```

with enough state to determine:

```text
what completed
what failed
what should retry
what is ambiguous
```

---

# 175. WORKER RESTART

A restarted worker must not create:

```text
duplicate ResearchRun
duplicate evidence
duplicate report
```

where idempotency applies.

Existing completed work should be recognized.

---

# 176. DATABASE RESTART

PostgreSQL remains canonical.

A database restart may temporarily block canonical writes, but the system must not silently mark research complete without durable state.

---

# 177. REDIS RESTART

Redis is infrastructure.

If Redis loses transient progress messages:

```text
canonical ResearchRun state
```

must remain the source for status recovery.

Do not make Redis pub/sub history the only record of research progress.

---

# 178. UPSTREAM RUNTIME RESTART

If an upstream runtime crashes:

```text
ResearchRun
```

must retain enough state to:

```text
retry
resume
mark partial
mark failed
```

depending on runtime capability.

---

# 179. PROVENANCE AFTER RETRY

A retried search may retrieve new content.

The system must preserve:

```text
original attempt
retry attempt
retrieval timestamp
provider
evidence identity
```

where needed.

Do not silently overwrite the original observation.

---

# 180. RESOURCE TERMINATION

When a run exceeds:

```text
token budget
time budget
cost budget
concurrency budget
quota
```

the system should terminate or reduce execution explicitly.

The user-facing state should say:

```text
partial / quota / budget exceeded
```

as appropriate.

---

# 181. NO UNBOUNDED AGENTS

No upstream runtime may be configured in a way that allows indefinite recursive research.

Outer Neosis policies must cap:

```text
iterations
tasks
depth
breadth
time
tokens
cost
```

---

# 182. RUNTIME ISOLATION

If upstream dependencies conflict with Neosis:

```text
separate process
separate worker
or internal service
```

may be used.

Do not change the whole Neosis Python environment simply to satisfy one upstream runtime without evaluating isolation first.

---

# 183. PYTHON COMPATIBILITY

Open Deep Research currently documents Python 3.11.

The live Neosis runtime must be verified before integration.

If there is a conflict:

```text
do not silently perform a repository-wide Python migration
```

Evaluate an isolated worker/runtime.

---

# 184. DEPENDENCY ISOLATION

Upstream package dependencies should be isolated where the project tooling allows.

The aim is:

```text
upstream compatibility
```

without:

```text
global dependency pollution
```

---

# 185. LICENSING

For each upstream package record:

```text
license
version/revision
distribution method
local patches
```

Do not lose license notices when vendoring code.

---

# 186. ARCHIVED UPSTREAM POLICY

Open Deep Research is archived.

Therefore:

```text
pin revision
record archive status
retain regression suite
control upgrades
```

A future update to a fork or successor must be an explicit architecture decision.

---

# 187. ACTIVE UPSTREAM POLICY

STORM and GPT Researcher should be monitored according to their current release/maintenance state.

Do not assume active means stable.

A version update still requires:

```text
adapter tests
research regression
provenance regression
cost/latency evaluation
```

---

# 188. UPSTREAM UPDATE PROCESS

A future update requires:

```text
fetch revision
    ->
inspect changes
    ->
update inventory
    ->
run upstream contract tests
    ->
run adapter tests
    ->
run provenance tests
    ->
run benchmark
    ->
review license
    ->
update pin
```

Never upgrade merely because a new tag exists.

---

# 189. RESEARCH IMPLEMENTATION INVENTORY

Create:

```text
docs/CH3_IMPLEMENTATION_INVENTORY.md
```

or the project-equivalent.

Track:

```text
Neosis path
Neosis symbol
verified responsibility
target responsibility
upstream repository
upstream revision
upstream symbol
adapter responsibility
tests
status
open questions
```

This inventory is mandatory because multiple upstream systems are being integrated.

---

# 190. REQUIRED RUNBOOK

Create:

```text
docs/CH3_RESEARCH_MIGRATION_RUNBOOK.md
```

or equivalent.

It should cover:

```text
startup
provider configuration
retriever setup
academic providers
MCP setup
health checks
failure recovery
cancellation
budget controls
benchmark execution
rollback
upstream upgrades
```

---

# 191. IMPLEMENTATION ADR SET

Create ADRs for at least:

```text
ADR-CH3-001 — ResearchEngine boundary
ADR-CH3-002 — Open Deep Research primary runtime
ADR-CH3-003 — STORM capability boundary
ADR-CH3-004 — GPT Researcher capability boundary
ADR-CH3-005 — ResearchRun canonical state
ADR-CH3-006 — Evidence/provenance model
ADR-CH3-007 — Retriever registry
ADR-CH3-008 — Academic retrieval policy
ADR-CH3-009 — MCP policy
ADR-CH3-010 — Memory promotion boundary
ADR-CH3-011 — Research Output KG promotion
ADR-CH3-012 — Runtime isolation
ADR-CH3-013 — Upstream pinning/archive policy
ADR-CH3-014 — Cutover and rollback
```

The exact ADR filenames should follow current repository convention.

---

# 192. CHANGE CONTROL

Each implementation batch must answer:

```text
What architectural boundary changed?
Why?
What upstream behavior was reused?
What was intentionally not reimplemented?
What local component stayed untouched?
What tests prove the change?
What is the rollback path?
```

Do not produce a giant unrelated refactor.

---

# 193. RECOMMENDED COMMIT BOUNDARIES

The implementation may use commit boundaries approximately equivalent to:

```text
research engine foundation
upstream revision registry
canonical ResearchRun/Task models
evidence/source normalization
provenance
retriever integration
Open Deep Research integration
STORM capability integration
GPT Researcher retriever integration
events/streaming
cancellation/recovery
memory promotion
graph promotion
evaluation
cutover
```

These are conceptual boundaries, not mandatory commit messages.

---

# 194. HARD DIRECTORY BOUNDARY

Do not place all research code in:

```text
app/orchestration/research_mode.py
```

Do not place all research persistence in:

```text
app/models/knowledge.py
```

Do not place all research events in:

```text
app/workers/tasks.py
```

Do not place all research retrieval in:

```text
app/services/web_search.py
```

The target architecture is modular.

---

# 195. EXACT CURRENT TOUCHPOINT — API

Verified current touchpoint:

```text
app/api/routes/workspaces.py
```

Current research route:

```text
/{workspace_id}/research
```

Current request:

```text
ResearchRequest
```

Current job:

```text
run_research_agent_job
```

Target:

```text
route -> create canonical run -> enqueue -> return run/job identifiers
```

---

# 196. EXACT CURRENT TOUCHPOINT — WORKER

Verified current touchpoint:

```text
app/workers/tasks.py
```

Current role:

```text
construct ResearchModeOrchestrator
construct WebSearchTool
publish progress
project OutputGraph
```

Target role:

```text
dispatch ResearchService/ResearchEngine
publish normalized events
persist lifecycle
```

The worker must become thinner.

---

# 197. EXACT CURRENT TOUCHPOINT — ORCHESTRATOR

Verified current touchpoint:

```text
app/orchestration/research_mode.py
```

Current four-node graph:

```text
planner
executor
synthesizer
reporter
```

Target:

```text
compatibility/baseline layer
```

It must not become a custom clone of the selected upstream deep-research runtime.

---

# 198. EXACT CURRENT TOUCHPOINT — WEB SEARCH

Verified current touchpoint:

```text
app/services/web_search.py
```

Current implementation:

```text
AsyncTavilyClient
```

This becomes one retriever/provider capability.

It does not define the target Research Engine.

---

# 199. EXACT CURRENT TOUCHPOINT — MEMORY

Verified current touchpoint:

```text
app/services/memory_router.py
```

Current responsibilities include:

```text
KnowledgeMemory routing
graph sync dispatch
context token budgeting
```

Target Chapter 3 responsibility:

```text
product memory boundary
```

It must not learn upstream research runtime internals.

---

# 200. EXACT CURRENT TOUCHPOINT — GRAPH

Verified current touchpoint:

```text
app/schemas/graph.py
app/repositories/graph.py
```

Current output concept:

```text
OutputGraph
    nodes
    edges
    optional provenance
```

Target Chapter 3:

```text
curated research graph candidate
```

The graph remains derived.

---

# 201. EXACT CURRENT TOUCHPOINT — LLM

Verified current touchpoint:

```text
app/api/deps/llm.py
```

Current state is a mock/stub gateway.

The Chapter 3 implementation must not assume production model routing already exists.

Before integrating upstream model requirements:

```text
inspect actual LLM infrastructure
```

Then decide whether the Research Engine:

```text
consumes existing gateway
```

or:

```text
requires an explicitly scoped model adapter
```

Do not silently build a second LLM gateway.

---

# 202. FILE-LEVEL TARGET MAP

Preferred target:

```text
app/
  integrations/
    research_engine/
      __init__.py
      engine.py
      config.py
      open_deep_research.py
      storm.py
      gpt_researcher.py
      retrievers.py
      normalizers.py
      provenance.py
      events.py
      errors.py
      schemas.py
      health.py
```

Canonical product layer:

```text
app/
  services/
    research.py
    research_state.py
    research_normalization.py
    research_provenance.py
    research_memory.py
    research_graph.py
```

Canonical persistence:

```text
app/
  models/
    research.py

  repositories/
    research.py

  schemas/
    research.py
```

The exact layout must follow actual repository conventions.

---

# 203. MODEL FILE GUIDANCE

A compact model layout is preferred initially.

Potential:

```text
app/models/research.py
```

may contain:

```text
ResearchRun
ResearchTask
ResearchEvidence
ResearchArtifact
ResearchSource
ResearchUsage
ResearchEvent
```

If this becomes too large, split it intentionally.

Do not create one file per tiny metadata type simply to avoid thinking about model boundaries.

---

# 204. REPOSITORY FILE GUIDANCE

Potential:

```text
app/repositories/research.py
```

should own canonical persistence only.

It must not execute:

```text
HTTP to research providers
Open Deep Research calls
STORM
GPT Researcher
MCP
```

Repositories persist.

Integrations execute external runtimes.

---

# 205. SCHEMA FILE GUIDANCE

Potential:

```text
app/schemas/research.py
```

should expose product-level DTOs.

Do not copy entire upstream Pydantic schemas.

Public schemas should remain:

```text
engine-neutral
provider-neutral
version-aware
```

---

# 206. RESEARCH SERVICE FILE GUIDANCE

Potential:

```text
app/services/research.py
```

should coordinate:

```text
authorization
configuration
ResearchRun lifecycle
engine invocation
normalization
persistence
promotion
```

It should not implement deep-research algorithms.

---

# 207. RESEARCH STATE FILE GUIDANCE

Potential:

```text
app/services/research_state.py
```

should own:

```text
state transition validation
run lifecycle
task lifecycle
terminal state rules
```

This is product lifecycle, not upstream graph state.

---

# 208. RESEARCH NORMALIZATION FILE GUIDANCE

Potential:

```text
app/services/research_normalization.py
```

should own:

```text
provider-neutral evidence/artifact normalization
source metadata normalization
report normalization
deduplication identity
```

---

# 209. RESEARCH PROVENANCE FILE GUIDANCE

Potential:

```text
app/services/research_provenance.py
```

should own:

```text
lineage
citation references
source resolution
claim support
provenance status
```

---

# 210. RESEARCH MEMORY FILE GUIDANCE

Potential:

```text
app/services/research_memory.py
```

should own:

```text
memory candidate creation
promotion policy
```

It delegates to the existing memory system.

---

# 211. RESEARCH GRAPH FILE GUIDANCE

Potential:

```text
app/services/research_graph.py
```

should own:

```text
graph candidate extraction
validation
promotion
projection
```

It does not become the research reasoning engine.

---

# 212. TEST DIRECTORY MAP

Use repository-consistent test directories.

Preferred logical layout:

```text
tests/
  unit/
    research/
  integration/
    research/
  e2e/
    research/
  eval/
    research/
```

Do not create an entirely new test framework.

---

# 213. TEST LEVEL 1 — UNIT

Unit tests should cover:

```text
state transitions
request mapping
upstream DTO normalization
evidence identity
deduplication
provenance mapping
event mapping
error mapping
retriever selection
budget enforcement
```

Mock external dependencies.

---

# 214. TEST LEVEL 2 — UPSTREAM CONTRACT

Against pinned upstream:

```text
basic research execution
retriever invocation
report output
event behavior
configuration compatibility
MCP behavior where enabled
```

These detect upstream drift.

---

# 215. TEST LEVEL 3 — CANONICAL PERSISTENCE

Test:

```text
ResearchRun persistence
ResearchTask persistence
Evidence persistence
Artifact persistence
Source persistence
Provenance
Tags
Usage
Event persistence
workspace isolation
```

---

# 216. TEST LEVEL 4 — INTEGRATION

Run:

```text
Neosis API
    ->
Redis/Arq
    ->
ResearchEngine
    ->
upstream runtime
    ->
retriever
    ->
PostgreSQL
    ->
memory/graph promotion
```

The full research path must be exercised.

---

# 217. TEST LEVEL 5 — END TO END

Test through the public product boundary.

Validate:

```text
request
run
progress
evidence
report
citations
promotion
workspace isolation
failure behavior
```

---

# 218. TEST LEVEL 6 — EVALUATION

Use a fixed research corpus.

Compare:

```text
legacy prototype
standalone upstream
integrated Research Engine
```

where practical.

---

# 219. MINIMUM RESEARCH TEST MATRIX

| Test | Expected |
|---|---|
| create research run | canonical run created before expensive work |
| unauthorized workspace | request rejected before research |
| duplicate start where idempotency applies | no duplicate canonical run |
| upstream unavailable | explicit stable error |
| retriever unavailable | policy-defined fallback/partial/failure |
| duplicate URL | evidence deduplicated |
| duplicate source content | fingerprint-aware deduplication |
| academic source | canonical academic evidence |
| MCP unavailable | explicit capability failure/fallback |
| contradictory sources | both evidence records preserved |
| partial task failure | run becomes partial where appropriate |
| cancellation | run becomes cancelled/partial |
| worker restart | canonical state survives |
| provider timeout | retry/recovery behavior explicit |
| budget exhausted | controlled termination |
| report generated | report links to canonical evidence |
| graph promotion | canonical artifact exists first |
| memory promotion | explicit policy path |
| cross-workspace access | denied |
| cost accounting | usage captured |
| provenance failure | degraded status visible |


# 220. BEHAVIORAL ACCEPTANCE — MULTI-SOURCE

A research task requiring multiple independent sources must demonstrate:

```text
multiple source identities
multiple evidence records
traceable claim support
```

The report must not collapse all source content into one untraceable string.

---

# 221. BEHAVIORAL ACCEPTANCE — ACADEMIC

For an academic research task:

```text
academic retriever selected where policy permits
academic metadata preserved
citation source identity preserved
retrieval timestamp preserved
```

A web page that merely mentions a paper is not automatically equivalent to the paper.

---

# 222. BEHAVIORAL ACCEPTANCE — CURRENT INFORMATION

For a current-information request:

```text
external retrieval occurs
retrieval timestamps are preserved
source freshness is visible
```

The system must not silently answer from historical training knowledge when the task explicitly requires current research.

---

# 223. BEHAVIORAL ACCEPTANCE — CONFLICT

When two credible sources disagree:

```text
both evidence records survive
conflict is represented
claim status can become conflicting/uncertain
```

The system must not silently select one source solely because the model preferred it.

---

# 224. BEHAVIORAL ACCEPTANCE — TEMPORAL CONSTRAINT

For:

```text
as of YYYY-MM-DD
during period X
before event Y
```

the run must retain the temporal requirement and evaluate retrieved sources against it where possible.

---

# 225. BEHAVIORAL ACCEPTANCE — PARTIAL

If only part of the research completes:

```text
completed evidence survives
completed tasks survive
failed tasks are visible
run is PARTIAL
```

The UI/report layer must not imply complete coverage.

---

# 226. BEHAVIORAL ACCEPTANCE — CANCELLATION

If the user cancels:

```text
new work stops
supported upstream execution is interrupted
completed evidence remains
run becomes CANCELLED or PARTIAL
```

No evidence should be deleted merely because the run was cancelled.

---

# 227. BEHAVIORAL ACCEPTANCE — BUDGET

If a token/cost/time budget is reached:

```text
research terminates predictably
state becomes explicit
existing evidence remains
usage is recorded
```

No indefinite retries.

---

# 228. BEHAVIORAL ACCEPTANCE — CITATION

Every user-visible citation must map to:

```text
canonical evidence
    ->
canonical source
```

No fabricated source IDs.

No fabricated page numbers.

No fabricated DOI.

---

# 229. BEHAVIORAL ACCEPTANCE — MEMORY

A research run that generates findings must not automatically create permanent Knowledge Memory unless the explicit promotion policy says so.

---

# 230. BEHAVIORAL ACCEPTANCE — GRAPH

A research run that creates a semantic graph must not automatically make all generated nodes canonical.

Graph projection occurs only from canonical graph candidates.

---

# 231. BEHAVIORAL ACCEPTANCE — REPROJECTION

Destroying/rebuilding Neo4j must not destroy canonical research evidence.

Destroying the cache must not destroy research state.

Destroying a temporary raw trace must not destroy canonical provenance.

---

# 232. BEHAVIORAL ACCEPTANCE — RETRY

Retried research execution must not create unexplained duplicates.

Each retry should be associated with the same run and appropriate task/attempt metadata.

---

# 233. BEHAVIORAL ACCEPTANCE — PROVIDER FALLBACK

When the primary retriever fails and fallback is enabled:

```text
failure recorded
fallback recorded
actual provider recorded
evidence lineage remains intact
```

---

# 234. EVALUATION BASELINE

The legacy Research Mode baseline is:

```text
app/orchestration/research_mode.py
app/services/web_search.py
app/workers/tasks.py::run_research_agent_job
```

The baseline should be frozen before production cutover.

Do not benchmark against a moving legacy implementation.

---

# 235. STANDALONE UPSTREAM BASELINE

Where feasible, benchmark upstream runtimes independently.

The goal is to distinguish:

```text
upstream research quality
```

from:

```text
Neosis integration quality
```

If standalone output is poor, do not assume a Neosis adapter bug.

If standalone output is strong but integrated output is poor, inspect normalization/context/configuration.

---

# 236. INTEGRATED BASELINE

The final candidate is:

```text
Neosis Research API
    ->
ResearchService
    ->
ResearchEngine
    ->
upstream runtime(s)
    ->
canonical evidence
    ->
report
```

This is the system under evaluation.

---

# 237. QUALITY COMPARISON RULE

Do not declare success simply because:

```text
new report looks longer
```

Measure:

```text
evidence relevance
claim support
citation correctness
coverage
breadth
depth
latency
cost
```

---

# 238. RESEARCH BENCHMARK CORPUS

The benchmark should include at least:

```text
simple factual questions
multi-hop investigations
multi-source synthesis
academic literature
historical questions
current-information questions
contradictory evidence
source-discovery tasks
long-tail topics
date-bounded questions
```

It should contain expected evaluation dimensions rather than requiring a single canonical answer for every open-ended research task.

---

# 239. BENCHMARK STABILITY

External research changes over time.

Therefore benchmarks should preserve:

```text
query
evaluation date
source expectations
acceptable source classes
metric version
```

For time-sensitive tasks, benchmark validity may have an explicit expiration/revalidation policy.

---

# 240. SOURCE SNAPSHOT BENCHMARKS

For deterministic regression testing where possible, use:

```text
stored source snapshots
```

so integration tests can run without depending on live web content.

Live web research remains a separate capability test.

---

# 241. OFFLINE EVALUATION

The Research Engine should support evaluation against:

```text
fixed source corpus
```

without requiring live search.

This is important for:

```text
CI
regression testing
provider outage scenarios
citation tests
provenance tests
```

---

# 242. LIVE EVALUATION

Live provider evaluation should test:

```text
current web
current academic sources
provider health
rate limits
retriever routing
```

It may be scheduled separately from deterministic CI.

---

# 243. COST-AWARE EVALUATION

Expensive deep-research runs should be bounded.

Benchmark runners must support:

```text
sample size
cost limit
time limit
provider selection
model selection
```

Do not allow a regression benchmark to become an uncontrolled bill.

---

# 244. QUALITY REGRESSION RULE

An upstream upgrade is not accepted merely because integration tests pass.

It must also satisfy:

```text
no unacceptable regression in evidence quality
no unacceptable regression in citation correctness
no unacceptable regression in provenance
```

and remain within resource budgets.

---

# 245. CUTOFF CRITERIA

Production cutover requires:

```text
architecture conformity
canonical state correctness
evidence correctness
provenance correctness
workspace isolation
resource governance
quality benchmark
cost benchmark
reliability benchmark
rollback readiness
```

A 200-status API response is not a cutover criterion.

---

# 246. SHADOW MODE

Where economically feasible:

```text
user request
    |
    +--> candidate ResearchEngine
    |
    +--> legacy ResearchMode baseline
```

Compare:

```text
quality
citations
evidence count
latency
cost
failure
```

Do not double-charge user traffic unless explicitly accepted.

---

# 247. SHADOW OUTPUT IS NOT USER OUTPUT

Shadow research must not automatically:

```text
write memory
write graph
mutate workspace
```

unless the shadow architecture explicitly isolates those side effects.

Shadow execution should be side-effect controlled.

---

# 248. CUTOVER MECHANISM

The product should use one centralized decision point.

Conceptually:

```text
ResearchService
    |
    v
ResearchEngineFactory / strategy resolver
    |
    +--> new engine
    +--> legacy baseline
```

Do not put engine flags into individual retrievers or API routes.

---

# 249. LEGACY RETIREMENT

After successful cutover:

```text
legacy research engine
    ->
deprecated
```

It may remain available for:

```text
benchmark
debugging
emergency rollback
```

for a controlled transition period.

Then it can be removed by a separate cleanup task.

---

# 250. ROLLBACK STRATEGY

Rollback must not require:

```text
database downgrade
```

if possible.

The design should allow:

```text
new engine disabled
legacy engine enabled
```

while preserving canonical research state.

---

# 251. ROLLBACK DATA SAFETY

Rollback must not delete:

```text
ResearchRun
ResearchTask
ResearchEvidence
ResearchArtifact
Report
Usage
```

created by the new engine.

If the legacy engine cannot understand new artifact types:

```text
run state remains intact
```

and the product should expose that limitation rather than corrupting data.

---

# 252. FAILURE TAXONOMY

The canonical error taxonomy should support at least:

```text
INVALID_REQUEST
UNAUTHORIZED
QUOTA_EXCEEDED
CONFIGURATION_ERROR
UPSTREAM_UNAVAILABLE
UPSTREAM_TIMEOUT
RETRIEVER_FAILURE
ACADEMIC_RETRIEVER_FAILURE
MCP_FAILURE
SOURCE_RESOLUTION_FAILURE
PROVENANCE_FAILURE
MODEL_FAILURE
RATE_LIMITED
CANCELLED
INTERNAL_ERROR
```

The final enum/vocabulary must follow existing conventions.

---

# 253. ERROR TRANSLATION

Upstream exception:

```text
OpenDeepResearchError
TavilyError
StormError
GPTResearcherError
MCPError
```

must become a stable Neosis error representation.

Do not leak library class names through the public API.

---

# 254. ERROR RETENTION

The system should retain operational error metadata sufficient for debugging:

```text
error class
provider
run_id
task_id
timestamp
attempt
retryability
last message
```

Do not persist full secrets or private request headers.

---

# 255. USER-FACING ERROR MESSAGES

User-visible errors should answer:

```text
what happened
whether the run can retry
whether partial research exists
```

Avoid exposing:

```text
Python exception
upstream stack trace
internal hostnames
```

---

# 256. HEALTH MODEL

Research health should be decomposed.

Conceptually:

```text
research_api
research_worker
primary_engine
retriever:web
retriever:academic
retriever:mcp
llm
database
redis
```

This avoids declaring the entire platform down because one optional provider is unavailable.

---

# 257. DEGRADED MODE

A research capability may be degraded when:

```text
one provider unavailable
academic retrieval unavailable
MCP unavailable
one optional strategy unavailable
```

The platform should still operate where policy permits.

The final run should record degraded capabilities.

---

# 258. NO FALSE HEALTH

Do not return “healthy” for a research component that cannot actually execute a minimal valid configured operation.

Do not run expensive LLM calls for every health probe.

Use layered health checks.

---

# 259. SECURITY BOUNDARY

Research tools are untrusted capability surfaces.

The system must protect:

```text
credentials
workspace data
private source content
MCP secrets
provider keys
system prompts
internal APIs
```

Tool output is data.

Tool output is not authorization.

---

# 260. PROMPT INJECTION BOUNDARY

Research content from:

```text
web
PDF
academic paper
MCP
workspace source
```

must be treated as untrusted content.

A source must not be able to redefine:

```text
workspace authorization
tool permissions
provider credentials
graph write policy
memory policy
system configuration
```

---

# 261. RESEARCH TOOL PERMISSION MODEL

Tool capability should be defined by policy.

Potential categories:

```text
read-only web retrieval
read-only academic retrieval
read-only MCP
user-authorized source access
```

Do not expose arbitrary tools merely because an upstream package can call them.

---

# 262. MCP SIDE-EFFECT POLICY

If an MCP tool is not strictly read-only, it requires explicit policy.

Research Mode should default toward read-only capabilities.

Side-effecting tools should not be reachable through generic research prompts without authorization.

---

# 263. SOURCE SECURITY

Web pages and documents can contain:

```text
malicious instructions
fake citations
prompt injection
tracking links
unexpected payloads
```

The research system must maintain the separation:

```text
source content
!=
system instruction
```

---

# 264. OUTPUT SECURITY

Research reports can contain:

```text
untrusted URLs
external code
instructions
sensitive source excerpts
```

The API/UI layer should treat them as data.

Do not execute report content as code.

---

# 265. PRIVACY

Private workspace research should remain scoped.

Do not use private workspace evidence in shared provider caches.

Do not log raw private evidence by default.

Do not feed one workspace's private source into another workspace's research.

---

# 266. DATA RETENTION

Research artifacts may be larger and longer-lived than ephemeral execution state.

Define retention separately for:

```text
run state
evidence
reports
raw traces
retrieval caches
events
```

Do not assume one global retention period is appropriate.

---

# 267. DELETION

If a workspace is deleted, the Research Engine's canonical records should obey workspace deletion policy.

External provider data should only be deleted if Neosis actually created it and policy permits/required it.

Read-only web retrieval generally does not create deletable external resources.

MCP-created side effects require explicit cleanup semantics.

---

# 268. DELETION RECONCILIATION

If a workspace deletion is asynchronous:

```text
canonical deletion
    ->
research cleanup
    ->
memory/graph cleanup
    ->
external side-effect cleanup where required
```

Canonical deletion must not wait indefinitely for an external provider.

This follows the Chapter 2 philosophy of canonical state first.

---

# 269. RESEARCH REPORT EXPORT

If reports can be exported:

```text
export artifact
    ->
S3/object storage
```

The export should retain:

```text
run identity
report version
generation date
```

Do not treat an exported PDF/Markdown file as canonical state.

---

# 270. RESEARCH SOURCE EXPORT

If evidence/source bundles are exported, the package should include enough provenance to interpret them.

Potential:

```text
manifest
sources
evidence
claims
report
run metadata
```

The exact export format is separate from Chapter 3 core execution.

---

# 271. RESEARCH API IDEMPOTENCY

If a client retries the initial research request, the system must avoid accidental duplicate runs where the product contract expects request idempotency.

A request idempotency key may be introduced if consistent with existing API patterns.

Do not implement ad hoc client-side UUID behavior as the only protection.

---

# 272. CONTINUATION VS RETRY

A new research run may intentionally continue from an earlier run.

Distinguish:

```text
retry
    = same run execution continuation

continuation
    = new run referencing prior run
```

The data model should preserve the relationship.

---

# 273. PARENT RUN

A `parent_run_id` may be useful for:

```text
follow-up research
refinement
verification rerun
user continuation
```

It must remain optional.

Do not force every run into a hierarchical tree.

---

# 274. RESEARCH REFINEMENT

A user may ask:

```text
go deeper
verify this claim
research the opposing view
update with recent data
```

These should become new research tasks or new runs according to product semantics.

Do not mutate historical run intent.

---

# 275. REPORT UPDATE WITH NEW EVIDENCE

A report update should reference:

```text
new evidence
new run/task
new version
```

rather than silently replacing the historical report.

---

# 276. VERIFICATION RUN

A future verification feature may execute a smaller research run against a claim.

The architecture should support:

```text
parent_run
claim reference
verification objective
```

without redesigning the core ResearchRun schema later.

---

# 277. RESEARCH CRITIC HOOK

Chapter 4+ may add:

```text
critic agent
```

The canonical research engine should therefore retain enough artifact granularity for a critic to inspect:

```text
claims
evidence
citations
report
```

Do not store only the final text.

---

# 278. EVALUATION HOOK

Chapter 4+ may add automated research evaluation.

Persist enough data for evaluation:

```text
run config
engine revision
evidence set
report
usage
latency
```

---

# 279. CONTRADICTION ENGINE HOOK

Future contradiction detection requires:

```text
claim identity
claim text
evidence set
source identities
timestamps
```

These must not be discarded in Chapter 3.

---

# 280. ADVANCED KG HOOK

Future advanced KG work may require:

```text
entity normalization
relationship confidence
temporal edges
claim-evidence graph
```

Chapter 3 should preserve raw semantic provenance without prematurely implementing all of this.

---

# 281. RESEARCH MEMORY PROMOTION HOOK

Future memory systems may promote:

```text
verified research claims
stable source summaries
user-approved findings
```

Chapter 3 must provide provenance and status necessary for those decisions.

---

# 282. WORKSPACE KNOWLEDGE PROMOTION HOOK

A research finding may be explicitly promoted into a workspace knowledge set.

The promotion should be:

```text
explicit
traceable
versioned
workspace-scoped
```

---

# 283. USER CONTROL

Autonomous research should not silently make broad durable changes to the user's workspace.

Default assumption:

```text
research reads
research discovers
research proposes
```

Promotion is explicit.

---

# 284. RESEARCH OUTPUT AS PROPOSAL

This principle is especially important for:

```text
memory
graph
workspace knowledge
workspace commits
```

Research outputs should often be treated as:

```text
proposals/candidates
```

until promoted.

---

# 285. PRODUCT CONTRACT VS ENGINE CAPABILITY

The upstream engine may support a feature that Neosis does not want to expose.

That feature remains:

```text
internal upstream capability
```

Do not automatically expose every upstream feature in the public Neosis API.

---

# 286. PROVIDER-AGNOSTIC PRODUCT

Neosis should remain able to replace:

```text
search provider
academic provider
research runtime
model provider
```

without rewriting the public product contract.

This is one of the main reasons for the ResearchEngine boundary.

---

# 287. UPSTREAM-SPECIFIC LEAKAGE AUDIT

Search code for leaked names in product schemas:

```text
OpenDeepResearch
Storm
GPTResearcher
Tavily
LangGraph
```

It is acceptable for integration modules to refer to them.

It is undesirable for core product domain models to become named after them.

---

# 288. CORE MODEL NEUTRALITY

Core entities should remain:

```text
ResearchRun
ResearchTask
ResearchEvidence
ResearchArtifact
ResearchReport
```

not:

```text
OpenDeepResearchRun
StormTask
GPTResearcherEvidence
```

unless an internal adapter-specific DTO requires such names.

---

# 289. INTEGRATION DTO ISOLATION

Upstream-specific models should live at the integration edge.

Example:

```text
OpenDeepResearchResult
StormResearchPlan
GPTResearcherSearchResult
```

may exist under:

```text
app/integrations/research_engine/
```

but should not leak into:

```text
app/models/
app/repositories/
```

as canonical persistence types.

---

# 290. NORMALIZATION CONTRACT

Every upstream adapter should terminate in one of:

```text
canonical research request
canonical research event
canonical research evidence
canonical research artifact
canonical report artifact
```

This is the integration contract.

---

# 291. NO MULTI-ENGINE OUTPUT ARBITRATION BY DEFAULT

If two upstream systems are used, do not automatically make them compete to produce two full reports and ask another model to choose one.

That creates:

```text
duplicated cost
duplicated provenance
ambiguous authority
```

Prefer:

```text
strategy capability
+
primary execution
+
specialized retrievers
```

---

# 292. MULTI-ENGINE PARALLELISM

Parallel use of engines is allowed only when there is a defined purpose such as:

```text
independent verification
benchmark comparison
specialist academic pass
```

and the run metadata clearly records the multi-engine design.

---

# 293. RESEARCH PLAN OWNERSHIP

The Neosis layer owns product policy.

The upstream research runtime owns detailed execution planning.

Correct:

```text
Neosis:
    research constraints
    budgets
    source policies

Upstream:
    how the research plan is operationalized
```

---

# 294. REPORT SYNTHESIS OWNERSHIP

Upstream runtime may generate the report.

Neosis owns:

```text
report artifact identity
provenance normalization
status
version
workspace ownership
```

Do not force all upstream synthesis logic into a Neosis prompt.

---

# 295. REPORT PROMPT OWNERSHIP

If upstream already provides report synthesis prompts:

```text
reuse upstream
```

Do not copy them into Neosis merely to change formatting.

Product-specific presentation can occur through an adapter or post-processing layer when safe.

---

# 296. SOURCE PROCESSING OWNERSHIP

Research retrieval results may require content extraction.

Use mature upstream/provider behavior where available.

Do not build another crawler/parser stack without an explicit capability gap.

---

# 297. CRAWLER OWNERSHIP

GPT Researcher may provide mature crawler capabilities.

If used:

```text
crawler lives behind retriever/source adapter
```

not inside:

```text
ResearchModeOrchestrator
```

---

# 298. WEB SEARCH OWNERSHIP

The existing `WebSearchTool` remains a provider-level abstraction.

It is not the research planner.

Research planning should be upstream or strategy-layer behavior.

---

# 299. MCP OWNERSHIP

The upstream runtime may execute MCP.

Neosis owns:

```text
authorization
credentials
allowed servers
usage
provenance
persistence
```

---

# 300. SOURCE PROVIDER OWNERSHIP

The provider determines:

```text
how to retrieve
what metadata is returned
provider-specific rate limits
```

Neosis determines:

```text
whether provider is allowed
how evidence is normalized
how provenance is stored
```

---

# 301. REPORT CITATION OWNERSHIP

The upstream report may contain citations.

Neosis must validate and map them into canonical evidence references.

A textual URL inside a report is not sufficient canonical provenance.

---

# 302. CITATION FAILURE POLICY

If a citation cannot be resolved:

```text
do not fabricate
do not silently create a new source
do not pretend resolved
```

Represent:

```text
unresolved
partial provenance
```

and make it observable.

---

# 303. REPORT FINALIZATION

A ResearchRun should not become `COMPLETED` until product-defined finalization conditions hold.

Those may include:

```text
tasks finalized
evidence persisted
report persisted
usage persisted
events emitted
promotion jobs scheduled where required
```

Do not use:

```text
model returned a string
```

as the completion condition.

---

# 304. RESEARCH RUN FINAL STATE

A terminal run should expose:

```text
status
completed_at
report reference
evidence summary
task summary
usage summary
warning summary
engine identity
```

This should be retrievable after worker shutdown.

---

# 305. TASK FINAL STATE

A task should expose:

```text
status
completed_at
evidence count
artifact count
failure if any
usage
```

This allows the UI to explain partial work.

---

# 306. EVENT RETENTION

Durable event retention should be proportional to product requirements.

Full event logs may live in:

```text
observability backend
```

while only important lifecycle events remain canonical in PostgreSQL.

Do not store every token delta as a database row without justification.

---

# 307. STREAMING VS DURABLE EVENTS

Streaming events are ephemeral.

Durable lifecycle state is canonical.

The distinction is:

```text
SSE event
    = current experience

ResearchEvent / ResearchRun
    = durable state
```

A user who reconnects should be able to recover current state without replaying every ephemeral token event.

---

# 308. RESEARCH JOB PROGRESS

Progress should be stored at coarse meaningful levels.

Do not store:

```text
10,000 token-level events
```

as relational lifecycle state.

Prefer:

```text
current task
stage
counts
timestamps
```

and external traces for detailed diagnostics.

---

# 309. OBSERVABILITY DASHBOARD TARGETS

Operational dashboards should include:

```text
research runs started
research runs completed
partial runs
failed runs
cancelled runs
average duration
p95 duration
cost per run
evidence per run
citation unresolved rate
provider error rate
retriever error rate
worker queue depth
active concurrency
```

---

# 310. RESEARCH QUALITY DASHBOARD

Quality monitoring may include:

```text
citation correctness
citation completeness
unsupported claim rate
evidence coverage
source diversity
academic retrieval success
contradiction detection coverage
```

Quality metrics should be versioned so metric-definition changes remain explainable.

---

# 311. COST DASHBOARD

Track:

```text
cost by engine
cost by provider
cost by model role
tokens by stage
retrieval calls
average cost per completed run
average cost per partial run
```

---

# 312. PROVIDER DASHBOARD

Track:

```text
provider availability
rate limits
latency
error rate
fallback rate
```

This supports retriever policy decisions.

---

# 313. UPSTREAM REGRESSION MONITORING

Upstream runtime changes can cause:

```text
quality regression
event shape change
retriever behavior change
cost increase
latency increase
```

Contract tests and benchmark suites are required before a pin changes.

---

# 314. CONFIGURATION VERSIONING

Research configuration should have a version or digest.

A ResearchRun should record the configuration version used.

This enables:

```text
reproduce
compare
rollback
audit
```

---

# 315. MODEL VERSIONING

Where provider APIs expose model identifiers, record the logical and provider model.

Conceptually:

```text
logical role
provider
model
version/revision if available
```

Do not make model identity part of the core ResearchRun primary key.

---

# 316. RETRIEVER VERSIONING

Record retriever/provider identity when it affects evidence.

This supports:

```text
provider comparison
debugging
benchmark interpretation
```

---

# 317. RESEARCH ENGINE VERSIONING

Every run should retain:

```text
engine
engine revision
adapter version/config version
```

This is essential because upstream runtimes may change.

---

# 318. RESEARCH CONFIG DIGEST

A stable config digest can be useful.

Conceptually:

```text
normalized config
    ->
hash/digest
```

The exact mechanism should follow repository conventions.

Do not hash secrets directly into user-visible IDs.

---

# 319. REPRODUCIBILITY

Perfect deterministic reruns are not expected.

The system should instead preserve:

```text
objective
configuration
engine revision
retriever set
source observations
evidence
report version
usage
```

That is the meaningful reproducibility contract.

---

# 320. NO FALSE DETERMINISM

Do not claim:

```text
same run will produce identical report
```

merely because the configuration is the same.

Research uses dynamic external information and nondeterministic models.

---

# 321. RESEARCH SOURCE MANIFEST

A completed run should be able to expose a source manifest containing:

```text
source identity
source type
provider
retrieval time
source count
```

This is useful for debugging and export.

---

# 322. EVIDENCE MANIFEST

A completed run should be able to summarize:

```text
evidence count
source count
task association
claim association
provenance status
```

---

# 323. ARTIFACT MANIFEST

A completed run should identify:

```text
plan artifact
research artifacts
claims/findings
report
graph candidates
memory candidates
```

where the product uses those objects.

---

# 324. REPORT LIMITATIONS

The final report should be able to include:

```text
limitations
warnings
partial coverage
unresolved contradictions
unresolved citations
```

This is preferable to hiding uncertainty.

---

# 325. RESEARCH WARNING MODEL

Warnings may represent:

```text
partial source coverage
provider fallback
academic provider unavailable
unresolved citation
budget truncation
partial task failure
```

Warnings are not necessarily run failures.

---

# 326. FAILURE VS WARNING

A run may be:

```text
COMPLETED
with warnings
```

if the product policy considers the result complete.

A run should be:

```text
PARTIAL
```

when important research coverage is missing.

Do not collapse warnings and failures.

---

# 327. REPORT COMPLETENESS

A report should expose whether:

```text
all planned tasks completed
```

or:

```text
some tasks failed/skipped
```

This is important for user trust.

---

# 328. RESEARCH DEPTH CONTROL

Depth may map to logical settings:

```text
shallow
standard
deep
```

Each setting should have explicit bounds.

Do not let “deep” mean “unbounded.”

---

# 329. RESEARCH BREADTH CONTROL

Breadth may control:

```text
number of independent research directions
source diversity
parallel investigation
```

Again:

```text
bounded
observable
configurable
```

---

# 330. RETRIEVER QUALITY CONTROL

Retrieval policy may rank providers based on:

```text
health
quality
topic fit
cost
latency
```

The policy should be deterministic enough to explain.

---

# 331. SOURCE DIVERSITY CONTROL

The Research Engine may intentionally prevent over-reliance on one domain/publisher if product policy requires.

This belongs in a policy layer.

Do not hardcode it into the retriever implementation.

---

# 332. SOURCE LIMITS

Per-run source limits may include:

```text
maximum sources
maximum evidence items
maximum content bytes
maximum academic sources
maximum web sources
```

The exact limits belong to configuration/quota.

---

# 333. CONTENT LIMITS

Evidence content may be truncated for context but must not be silently destroyed from canonical storage when the full source/reference is available elsewhere.

Differentiate:

```text
stored source
stored excerpt
context excerpt
```

---

# 334. LARGE SOURCE HANDLING

Research may encounter large PDFs/web pages.

The system should use:

```text
source snapshot
locator
excerpt
```

instead of injecting entire documents into every synthesis call.

---

# 335. SOURCE EXCERPT PROVENANCE

An excerpt must retain the parent:

```text
source_id
snapshot_id
locator
```

The excerpt cannot become a free-floating text blob.

---

# 336. RESEARCH ARTIFACT CHECKSUM

Immutable artifacts may have checksums.

This supports:

```text
integrity
deduplication
export validation
```

Do not use a checksum as semantic truth.

---

# 337. EVIDENCE FINGERPRINT

Evidence fingerprints may use normalized content plus locator.

The exact algorithm should be stable across retries where possible.

---

# 338. DUPLICATE CLAIMS

Different research paths may produce semantically similar claims.

Claim deduplication should remain separate from evidence deduplication.

Do not merge claims solely because the text strings are similar.

---

# 339. ENTITY NORMALIZATION HOOK

Future graph work may normalize:

```text
OpenAI
OpenAI Inc.
OpenAI, Inc.
```

into one entity.

Chapter 3 should not necessarily implement full entity resolution.

It must preserve entity-bearing fields where they are already produced.

---

# 340. TEMPORAL CLAIM HOOK

Future research may need:

```text
claim valid_at
claim observed_at
source publication_at
```

Do not discard timestamps from evidence.

---

# 341. RESEARCH SOURCE LICENSE HOOK

Academic/web sources may have usage/license constraints.

Where provider metadata exposes licenses or restrictions, preserve the metadata.

Do not assume all retrieved content can be republished verbatim.

---

# 342. SOURCE CONTENT QUOTATION

The report layer should respect applicable source/quote limits.

The architecture should preserve:

```text
source
excerpt
locator
```

rather than unnecessarily copying entire source documents into public reports.

---

# 343. RESEARCH OUTPUT STORAGE

A large final report may be stored:

```text
PostgreSQL metadata
+
S3 content
```

depending on repository patterns.

Do not place huge reports into Redis.

---

# 344. REDIS ROLE

Redis remains:

```text
queue
pub-sub
ephemeral coordination
cache
```

Not:

```text
canonical research archive
```

---

# 345. ARQ ROLE

Arq remains the background worker mechanism unless the project explicitly changes infrastructure.

Do not create a second worker framework for Research Mode.

---

# 346. WORKER CONCURRENCY

Research worker concurrency should be bounded.

Provider-level concurrency should be separately bounded.

A global worker setting must not be the only control.

---

# 347. FAILURE BACKOFF

Retryable work should use bounded backoff.

Do not implement tight retry loops.

Record attempt count where useful.

---

# 348. DEAD-LETTER / TERMINAL FAILURE

If a task permanently fails after controlled retries:

```text
task = FAILED
```

and the run may become:

```text
PARTIAL
```

or:

```text
FAILED
```

according to product policy.

Do not keep retrying forever.

---

# 349. RESEARCH CONTINUATION AFTER PARTIAL

A future continuation may reference:

```text
parent_run_id
```

and reuse selected evidence.

The continuation should still create a new run identity.

---

# 350. RESEARCH ARTIFACT PROMOTION STATUS

Each promotable artifact may need:

```text
eligible
promoted
rejected
pending_review
```

Do not infer promotion from the existence of an artifact.

---

# 351. USER REVIEW HOOK

If the product later requires human review, artifacts should be able to support:

```text
reviewer
decision
timestamp
notes
```

Chapter 3 need not implement a review UI.

---

# 352. RESEARCH OUTPUT VISIBILITY

Research artifacts may have visibility:

```text
workspace
private
shared
```

The exact product policy should follow existing sharing architecture.

The default should not make private research globally visible.

---

# 353. RESEARCH REPORT ACCESS

Only authorized users/workspace members should be able to retrieve:

```text
run
report
evidence
source metadata
```

depending on product sharing rules.

---

# 354. SOURCE ACCESS AFTER DELETION

If a source is later deleted:

```text
historical research evidence
```

must not silently claim the source still exists.

The product should preserve:

```text
tombstoned/deleted
```

or equivalent metadata according to deletion policy.

This is especially important for historical reports.

---

# 355. PROVENANCE AFTER SOURCE DELETION

A citation may become:

```text
valid historical provenance
but source currently unavailable
```

The system should represent that distinction.

Do not fabricate a replacement source.

---

# 356. UPSTREAM SOURCE LOSS

If a provider URL becomes unavailable, the evidence may still remain valid as a historical retrieval observation if its stored excerpt/fingerprint and provenance are retained.

The report should be able to indicate current availability separately.

---

# 357. RESEARCH RUN RECONCILIATION

A reconciliation process should be able to identify:

```text
nonterminal runs without active execution
tasks stuck in RUNNING
reports missing after synthesis
evidence records missing expected lineage
graph candidates without projection state
memory candidates without promotion state
```

This is a product consistency mechanism.

---

# 358. RUN REPAIR

Repair should be conservative.

For a stuck run:

```text
inspect
reconcile
retry or mark terminal
```

Do not silently manufacture success.

---

# 359. ARTIFACT REPAIR

If a report was generated but persistence failed:

```text
retry persistence
```

If evidence is missing:

```text
reconstruct from raw execution only when provenance remains trustworthy
```

Do not fabricate missing evidence.

---

# 360. GRAPH REPAIR

A missing graph projection should be rebuildable from canonical candidate data.

Do not rerun the entire research job solely to restore Neo4j.

---

# 361. MEMORY REPAIR

A missing memory promotion should be rebuildable from:

```text
canonical research artifact
```

rather than requiring another external research run.

---

# 362. RESEARCH ENGINE CONTRACT TESTS

Every engine adapter must satisfy the same high-level contract:

```text
start
execute
stream
cancel
return normalized result
report usage
```

The exact methods may differ.

The behavioral contract must remain consistent.

---

# 363. UPSTREAM ADAPTER CONTRACT

An adapter must provide:

```text
input mapping
output mapping
event mapping
error mapping
usage mapping
capability metadata
```

It must not directly own canonical persistence.

---

# 364. CAPABILITY MATRIX

The integration should maintain a conceptual capability matrix:

| Capability | Open Deep Research | STORM | GPT Researcher | Neosis |
|---|---|---|---|---|
| Deep research execution | primary | optional | available | policy/orchestration |
| Perspective/questioning | possible | primary candidate | possible | policy |
| Web retrieval | supported | retriever ecosystem | broad | routing/policy |
| Academic retrieval | supported options | retrievers | supported | routing/policy |
| MCP | supported | capability dependent | supported | policy |
| Evidence normalization | upstream output | upstream output | upstream output | canonical |
| Provenance | upstream metadata | upstream citations | upstream metadata | canonical |
| Research state | execution | execution | execution | canonical |
| Memory promotion | no | no | no | canonical |
| Graph promotion | no | no | no | canonical |

This matrix should be updated after exact upstream inspection.

---

# 365. RESPONSIBILITY MATRIX RULE

When capability overlaps exist:

```text
Neosis chooses the boundary.
```

Do not duplicate the same capability at two layers without a clear reason.

---

# 366. NO CUSTOM RESEARCH PROMPT LIBRARY BY DEFAULT

Do not create a giant Neosis prompt library that duplicates:

```text
planning prompts
researcher prompts
writer prompts
```

already supplied by the selected upstream runtime.

Product-specific prompts may exist where the product needs unique behavior.

---

# 367. PROMPT VERSIONING

If Neosis-specific prompts are added:

```text
version them
record their version in ResearchRun
test them
```

Do not change prompts silently in production.

---

# 368. PROMPT DATA BOUNDARY

Prompts may contain selected evidence and context.

They must not automatically include:

```text
secrets
full private database rows
all memories
all state
```

Context assembly is deliberate.

---

# 369. SYSTEM INSTRUCTION OWNERSHIP

Neosis owns product-level instructions:

```text
workspace policy
tool policy
security
output contract
```

Upstream engine owns research-specific internal prompts.

Do not mix the two indiscriminately.

---

# 370. RESEARCH RESULT NORMALIZATION ORDER

The canonical order should remain:

```text
upstream result
    ->
parse
    ->
normalize source
    ->
normalize evidence
    ->
deduplicate
    ->
tag
    ->
provenance
    ->
persist
    ->
claim/synthesis
    ->
report/graph/memory candidates
```

Do not move promotion ahead of canonical persistence.

---

# 371. RESEARCH TASK DEPENDENCIES

Tasks may depend on other tasks.

If the upstream runtime exposes such dependencies, preserve them where useful.

Do not encode all task dependencies only inside opaque agent state.

---

# 372. TASK PARALLELISM

Task parallelism must be bounded.

A task graph should support:

```text
parallel independent tasks
serial dependent tasks
```

but must obey workspace/provider budgets.

---

# 373. TASK CANCELLATION

Cancelling a run should propagate to all active tasks where feasible.

A single failed task does not necessarily cancel all siblings.

---

# 374. TASK RETRY

A failed task may be retried independently when safe.

The run remains one canonical run.

Task attempts may be recorded separately if needed.

---

# 375. TASK ATTEMPT MODEL

If implemented, an attempt may contain:

```text
attempt_id
task_id
engine
started_at
ended_at
status
error
usage
```

Do not make attempt identity the same as task identity.

---

# 376. SOURCE RETRIEVAL ATTEMPT

Similarly, retrieval attempts may be represented via event/metadata rather than a dedicated table if that is sufficient.

The architecture requires traceability, not unnecessary tables.

---

# 377. SCHEMA MINIMALITY RULE

Use:

```text
small mandatory core
+
controlled metadata
```

Do not add every upstream field to canonical relational schema.

This preserves evolvability.

---

# 378. METADATA RULE

Metadata is appropriate for:

```text
provider-specific optional fields
debug identifiers
experimental values
uncommon source metadata
```

Metadata must not become a dumping ground for canonical lifecycle identity.

---

# 379. REQUIRED CORE FIELDS

For major canonical entities, prioritize:

```text
identity
ownership
lifecycle
timestamps
provenance
version
```

Then add domain-specific fields.

---

# 380. MIGRATION SAFETY

Schema migrations must be backwards-aware where practical.

During rollout:

```text
old code
new code
```

may temporarily coexist.

Avoid destructive migrations until production cutover is stable.

---

# 381. DATABASE MIGRATION ORDER

Where new tables are required:

```text
migration
    ->
model
    ->
repository
    ->
service
    ->
runtime
```

Do not deploy runtime code that requires tables that do not exist.

---

# 382. BACKFILL POLICY

Historical prototype runs should not be force-migrated automatically unless a concrete requirement exists.

If backfill occurs:

```text
legacy fields
    ->
new canonical objects
    ->
provenance_status = legacy/incomplete
```

Never fabricate historical evidence.

---

# 383. EXISTING RUN COMPATIBILITY

If an existing API returns job IDs without run IDs, the Chapter 3 migration may add run IDs while preserving job IDs for compatibility.

The product should gradually move toward:

```text
run_id
```

as canonical.

---

# 384. API RESPONSE COMPATIBILITY

If existing clients expect:

```text
job_id
status
```

preserve those fields where practical during transition.

Add:

```text
run_id
```

rather than breaking the old client contract abruptly unless an explicit API version change is approved.

---

# 385. RESEARCH STATUS POLLING

Polling should retrieve canonical `ResearchRun` state.

Do not poll upstream runtime directly from the browser.

---

# 386. FRONTEND COUPLING RULE

The frontend must not know:

```text
Open Deep Research node names
STORM classes
GPT Researcher task format
retriever provider object structure
```

It consumes Neosis research state/events.

---

# 387. EXPORT COUPLING RULE

Exports must use canonical Neosis artifact schemas.

Do not expose upstream runtime JSON as a stable export format.

---

# 388. OBSERVABILITY COUPLING RULE

Telemetry may contain upstream metadata.

Product APIs must not.

This keeps observability detailed without coupling product clients.

---

# 389. FEATURE FLAG ROLLBACK

A single central flag/policy should choose:

```text
legacy
new
```

during transition.

Do not create:

```text
USE_NEW_PLANNER
USE_NEW_RETRIEVER
USE_NEW_REPORTER
```

scattered across core services unless those are deliberate centralized capability flags.

---

# 390. MIGRATION STAGES

The architectural migration should feel like:

```text
Prototype
    ->
Boundary
    ->
Canonical state
    ->
Real upstream runtime
    ->
Evaluation
    ->
Cutover
```

not:

```text
Delete everything
    ->
rewrite
    ->
hope
```

---

# 391. PHASE OVERVIEW

Chapter 3 consists of exactly four large phases.

```text
PHASE 1
Research Engine Discovery, Upstream Integration & Foundation

PHASE 2
Neosis Research State, Evidence, Tagging & Provenance Layer

PHASE 3
Production Research Execution & Engine Composition

PHASE 4
Evaluation, Quality/Cost Optimization, Cutover & Operationalization
```

The later phase-rulebook document will define detailed subphases.

This document defines the architecture and phase gates.

---

# 392. PHASE 1 — OBJECTIVE

Phase 1 establishes:

```text
repository understanding
upstream understanding
version pinning
responsibility mapping
runtime feasibility
ResearchEngine boundary
retriever inventory
```

No production cutover should occur here.

---

# 393. PHASE 1 — REQUIRED INVARIANT

At the end of Phase 1:

```text
current Neosis research path is known
upstream systems are pinned
responsibilities are separated
runtime compatibility is tested
public API remains unchanged
```

---

# 394. PHASE 1 — REQUIRED DELIVERABLES

Conceptually:

```text
implementation inventory
upstream revision registry
engine responsibility matrix
retriever capability matrix
runtime compatibility decision
ResearchEngine contract
initial smoke tests
ADR set for major boundary decisions
```

---

# 395. PHASE 1 — EXIT GATE

Phase 1 passes only when:

```text
[ ] live repository inspected
[ ] current research baseline documented
[ ] Open Deep Research pinned
[ ] STORM pinned
[ ] GPT Researcher pinned
[ ] licenses recorded
[ ] upstream roles documented
[ ] runtime compatibility confirmed
[ ] retriever capabilities verified
[ ] ResearchEngine contract established
[ ] no production cutover performed prematurely
```

---

# 396. PHASE 2 — OBJECTIVE

Phase 2 establishes the canonical Neosis research fabric.

The central change is:

```text
raw research output
    ->
canonical evidence/artifact/state
```

before promotion.

---

# 397. PHASE 2 — REQUIRED INVARIANT

Every important durable research object must be:

```text
workspace-owned
canonically identified
lifecycle-managed
tagged
provenanced
version-aware
```

---

# 398. PHASE 2 — REQUIRED DELIVERABLES

Conceptually:

```text
ResearchRun
ResearchTask
ResearchEvidence
ResearchSource
ResearchArtifact
ResearchUsage
ResearchEvent
normalization
provenance
tagging
promotion boundaries
```

---

# 399. PHASE 2 — EXIT GATE

Phase 2 passes only when:

```text
[ ] ResearchRun canonical
[ ] ResearchTask canonical
[ ] evidence first-class
[ ] source identity normalized
[ ] provenance reconstructable
[ ] tags controlled
[ ] events normalized
[ ] usage captured
[ ] memory promotion explicit
[ ] graph promotion explicit
[ ] raw upstream output cannot bypass canonicalization
```

---

# 400. PHASE 3 — OBJECTIVE

Phase 3 makes the mature upstream research systems execute real Research Runs.

Default architecture:

```text
Neosis ResearchEngine
    ->
Open Deep Research
```

with:

```text
STORM
    = optional strategy capability

GPT Researcher
    = optional retrieval/crawling capability
```

---

# 401. PHASE 3 — REQUIRED INVARIANT

The upstream runtime may own research execution complexity.

Neosis continues to own:

```text
state
evidence
provenance
policy
workspace
events
resource control
product output
```

---

# 402. PHASE 3 — REQUIRED DELIVERABLES

Conceptually:

```text
production ResearchEngine
retriever routing
academic routing
MCP routing
evidence normalization
event streaming
cancellation
budget control
partial research
upstream error mapping
report persistence
```

---

# 403. PHASE 3 — EXIT GATE

Phase 3 passes only when:

```text
[ ] real Research Runs execute through ResearchEngine
[ ] Open Deep Research primary runtime integrated
[ ] STORM used only where defined
[ ] GPT Researcher capabilities used only where defined
[ ] evidence persists during execution
[ ] provenance survives execution
[ ] progress is observable
[ ] cancellation works
[ ] budgets work
[ ] partial results work
[ ] legacy orchestrator no longer primary
```

---

# 404. PHASE 4 — OBJECTIVE

Phase 4 proves the new engine is ready for production and retires the prototype path.

---

# 405. PHASE 4 — REQUIRED INVARIANT

No cutover until:

```text
quality verified
evidence verified
provenance verified
cost verified
reliability verified
isolation verified
rollback verified
```

---

# 406. PHASE 4 — REQUIRED DELIVERABLES

Conceptually:

```text
benchmark corpus
baseline metrics
new-engine metrics
shadow comparison
cost/latency report
reliability report
provenance audit
cutover plan
rollback plan
runbook
legacy deprecation
```

---

# 407. PHASE 4 — EXIT GATE

Phase 4 passes only when:

```text
[ ] benchmark completed
[ ] baseline comparison completed
[ ] citation quality acceptable
[ ] evidence quality acceptable
[ ] provenance acceptable
[ ] cost acceptable
[ ] latency acceptable
[ ] reliability acceptable
[ ] workspace isolation verified
[ ] memory promotion audited
[ ] graph promotion audited
[ ] shadow evaluation complete where used
[ ] production cutover complete
[ ] legacy engine deprecated
[ ] rollback documented
```

---

# 408. HARD DEPENDENCIES BETWEEN PHASES

Phase 1 -> Phase 2 requires:

```text
upstream contracts verified
runtime compatibility known
responsibility matrix defined
```

Phase 2 -> Phase 3 requires:

```text
canonical run state exists
evidence exists
provenance exists
workspace isolation exists
```

Phase 3 -> Phase 4 requires:

```text
real execution exists
progress exists
cancellation exists
usage exists
provenance exists
```

Do not skip these dependencies.

---

# 409. WHAT THE AGENT MUST NOT DO DURING ANY PHASE

The following are hard architecture violations:

1. Build a new deep-research framework in parallel with Open Deep Research without a documented capability gap.
2. Turn STORM into a second end-to-end supervisor.
3. Turn GPT Researcher into a second end-to-end supervisor.
4. Make all three upstream systems compete to answer the same request by default.
5. Copy upstream planners into `app/orchestration/research_mode.py`.
6. Copy retriever code into `app/services/web_search.py` merely to “unify” it.
7. Make Neo4j canonical.
8. Make Redis canonical.
9. Make upstream session IDs canonical.
10. Write raw upstream outputs directly into KnowledgeMemory.
11. Automatically write every research result to the Research Output KG.
12. Automatically write every result to durable memory.
13. Put all research code in `app/workers/tasks.py`.
14. Put provider-specific code in API route handlers.
15. Create a second LLM gateway without architecture review.
16. Create a second object store.
17. Create a second queue framework.
18. Create a separate citation graph.
19. Hide provider fallback.
20. Hide engine fallback.
21. Allow unlimited research.
22. Ignore workspace isolation.
23. Fabricate provenance.
24. Delete legacy baseline before evaluation.
25. Guess repository symbols.
26. Create duplicate paths solely to match old documentation.
27. Modify Chapter 2 Ground architecture casually.
28. Treat a polished report as evidence of correctness.
29. Change the architecture without an ADR.
30. Use unpinned upstream code in production.

---

# 410. REQUIRED ARCHITECTURAL AUDIT — OWNERSHIP

Verify:

```text
Does PostgreSQL own canonical ResearchRun?
Does PostgreSQL own canonical Evidence?
Does PostgreSQL own canonical artifact metadata?
Does S3 own large immutable content?
Does Neo4j remain projection?
Does Redis remain infrastructure?
Do upstream engines remain execution substrates?
```

If any answer is no, stop migration and resolve the boundary.

---

# 411. REQUIRED ARCHITECTURAL AUDIT — UPSTREAM

Verify:

```text
Is Open Deep Research actually being reused?
Is STORM used only for a defined capability?
Is GPT Researcher used only for a defined capability?
Are upstream revisions pinned?
Are local patches documented?
```

---

# 412. REQUIRED ARCHITECTURAL AUDIT — RETRIEVAL

Verify:

```text
Is retriever selection policy-controlled?
Is provider identity recorded?
Is academic retrieval distinct?
Is MCP policy controlled?
Is duplicate evidence handled?
```

---

# 413. REQUIRED ARCHITECTURAL AUDIT — PROVENANCE

For a final claim, trace:

```text
report
  ->
claim
  ->
evidence
  ->
source
  ->
snapshot/observation
  ->
retrieval metadata
  ->
task
  ->
run
  ->
workspace
```

---

# 414. REQUIRED ARCHITECTURAL AUDIT — MEMORY

For every promoted memory item:

```text
why promoted?
which research artifact?
which evidence?
which run?
which workspace?
which status?
```

---

# 415. REQUIRED ARCHITECTURAL AUDIT — GRAPH

For every Research Output KG element:

```text
graph candidate
  ->
canonical artifact
  ->
evidence
  ->
source
```

The graph must be rebuildable from canonical state.

---

# 416. REQUIRED ARCHITECTURAL AUDIT — SECURITY

Verify:

```text
no secrets in logs
no secrets in prompts
no secrets in evidence
no arbitrary MCP access
no cross-workspace research
no raw upstream IDs exposed unnecessarily
```

---

# 417. REQUIRED ARCHITECTURAL AUDIT — RELIABILITY

Simulate:

```text
engine unavailable
provider unavailable
academic provider unavailable
MCP unavailable
database restart
Redis restart
worker restart
cancellation
budget exhaustion
partial task failure
ambiguous external outcome
```

Every scenario must produce explicit product state.

---

# 418. REQUIRED ARCHITECTURAL AUDIT — COST

Verify:

```text
token limits
time limits
cost limits
task concurrency
provider concurrency
retrieval limits
```

No uncontrolled research fan-out.

---

# 419. REQUIRED ARCHITECTURAL AUDIT — API

Verify:

```text
public research endpoint remains Neosis-owned
browser does not call upstream systems directly
run ID is product-level
job ID remains infrastructure-level
status comes from canonical state
```

---

# 420. REQUIRED ARCHITECTURAL AUDIT — LEGACY

Verify:

```text
legacy ResearchModeOrchestrator remains available until evaluation
legacy WebSearchTool baseline is measurable
legacy path is not silently used after cutover
legacy removal is explicit
```

---

# 421. REQUIRED FINAL DIRECTORY SHAPE

The target logical shape is:

```text
NeosisLM/
|
+-- third_party/
|   +-- open-deep-research/
|       +-- <pinned upstream when vendored>
|
+-- app/
|   +-- api/
|   |   +-- routes/
|   |       +-- workspaces.py
|   |
|   +-- orchestration/
|   |   +-- research_mode.py
|   |
|   +-- integrations/
|   |   +-- research_engine/
|   |       +-- __init__.py
|   |       +-- engine.py
|   |       +-- config.py
|   |       +-- open_deep_research.py
|   |       +-- storm.py
|   |       +-- gpt_researcher.py
|   |       +-- retrievers.py
|   |       +-- normalizers.py
|   |       +-- provenance.py
|   |       +-- events.py
|   |       +-- errors.py
|   |       +-- schemas.py
|   |       +-- health.py
|   |
|   +-- models/
|   |   +-- research.py
|   |
|   +-- repositories/
|   |   +-- research.py
|   |
|   +-- schemas/
|   |   +-- research.py
|   |
|   +-- services/
|   |   +-- research.py
|   |   +-- research_state.py
|   |   +-- research_normalization.py
|   |   +-- research_provenance.py
|   |   +-- research_memory.py
|   |   +-- research_graph.py
|   |
|   +-- workers/
|       +-- tasks.py
|
+-- tests/
|   +-- unit/
|   +-- integration/
|   +-- e2e/
|   +-- eval/
|
+-- docs/
    +-- CH3_IMPLEMENTATION_INVENTORY.md
    +-- CH3_UPSTREAM_REVISION.md
    +-- CH3_ADR_*.md
    +-- CH3_RESEARCH_MIGRATION_RUNBOOK.md
```

This is a responsibility map.

The live repository remains authoritative for literal placement.

---

# 422. DEFINITION OF DONE

Chapter 3 is not done when:

```text
Open Deep Research runs.
```

It is not done when:

```text
the report looks good.
```

It is not done when:

```text
Neo4j contains research nodes.
```

It is done only when all of the following are true:

```text
[ ] Current Research Mode baseline documented.
[ ] Four-phase architecture respected.
[ ] Open Deep Research revision pinned.
[ ] STORM revision/version pinned.
[ ] GPT Researcher revision/version pinned.
[ ] ResearchEngine boundary implemented.
[ ] No unnecessary upstream behavior reimplemented.
[ ] ResearchRun canonical.
[ ] ResearchTask canonical.
[ ] Evidence first-class.
[ ] Source identity normalized.
[ ] Provenance reconstructable.
[ ] Tags controlled.
[ ] Events normalized.
[ ] Workspace isolation enforced.
[ ] Retriever routing works.
[ ] Academic routing works where enabled.
[ ] MCP routing works where enabled.
[ ] Cancellation works.
[ ] Partial research works.
[ ] Token/time/cost controls work.
[ ] Usage measured.
[ ] Report persisted.
[ ] Citation integrity tested.
[ ] Memory promotion explicit.
[ ] Graph promotion explicit.
[ ] Neo4j remains projection.
[ ] Legacy baseline evaluated.
[ ] New engine evaluated.
[ ] Reliability tested.
[ ] Security tested.
[ ] Rollback tested.
[ ] New engine becomes canonical production path.
[ ] Legacy engine deprecated.
[ ] Implementation inventory complete.
[ ] Upstream revision registry complete.
[ ] Runbook complete.
```

---

# 423. RESEARCH QUALITY COMPLETION GATE

Before production cutover, demonstrate:

```text
evidence quality is acceptable
citation quality is acceptable
research coverage is acceptable
provenance is acceptable
```

against the defined benchmark.

Do not use subjective “it feels better” as the gate.

---

# 424. OPERATIONAL COMPLETION GATE

Before production cutover, demonstrate:

```text
worker recovery
provider fallback
cancellation
budget enforcement
workspace isolation
observability
```

---

# 425. DATA COMPLETION GATE

Before production cutover, demonstrate:

```text
ResearchRun persistence
evidence persistence
report persistence
provenance persistence
graph candidate persistence
memory candidate persistence
```

---

# 426. ARCHITECTURAL COMPLETION GATE

Before production cutover, verify:

```text
Neosis owns product state.
Upstream systems own execution.
Adapters own translation.
No hidden second architecture exists.
```

---

# 427. WHAT COUNTS AS A GOOD IMPLEMENTATION

A good Chapter 3 implementation makes research capability larger while custom Neosis research logic becomes smaller.

After migration:

```text
Open Deep Research
    handles deep-research execution complexity

STORM
    supplies specialized perspective/question capabilities where justified

GPT Researcher
    supplies mature retriever/crawling capabilities where justified

Neosis
    owns product state
    owns evidence
    owns provenance
    owns policy
    owns workspace isolation
    owns memory
    owns graph promotion
    owns observability
    owns API behavior
```

If the repository instead contains:

```text
larger custom planner
larger custom crawler
duplicate retriever framework
three supervisors
duplicate report writers
duplicate evidence stores
```

then the architecture has drifted.

---

# 428. SOURCE BASIS FOR THIS SPECIFICATION

This architecture follows the engineering discipline established by the Chapter 2 implementation specification.

Chapter 2 explicitly defines itself as an implementation contract and requires upstream behavior to be reused rather than recreated. fileciteturn167file0L18-L26

Chapter 2 also establishes the evidence-level and repository-discovery discipline: exact implementation details must be verified rather than guessed. fileciteturn167file0L144-L148

Chapter 3 preserves that structure but applies it to a composite Research Engine.

## Current Neosis source basis

The live repository was inspected for:

```text
app/api/routes/workspaces.py
app/workers/tasks.py
app/orchestration/research_mode.py
app/services/web_search.py
app/services/memory_router.py
app/services/hybrid_retrieval.py
app/api/deps/llm.py
app/schemas/graph.py
app/schemas/context.py
app/models/knowledge.py
app/models/source.py
app/repositories/source.py
app/repositories/graph.py
```

The current Research Mode baseline is therefore repository-derived rather than imagined.

## Upstream basis

Open Deep Research:

```text
https://github.com/langchain-ai/open_deep_research
```

STORM:

```text
https://github.com/stanford-oval/storm
```

GPT Researcher:

```text
https://github.com/assafelovic/gpt-researcher
```

The exact revisions used by implementation must be recorded in:

```text
docs/CH3_UPSTREAM_REVISION.md
```

---

# 429. FINAL AUTHORITY RULE

This file is the Chapter 3 architecture and migration contract.

The later phase-rulebook document will contain:

```text
subphases
work packages
exact file edits
commands
test procedures
acceptance criteria
```

The phase-rulebook must conform to this architecture.

The live repository is authoritative for:

```text
exact current Neosis files
exact symbols
exact route registration
exact schemas
```

The pinned upstream repository is authoritative for:

```text
exact upstream implementation behavior
exact runtime API
exact event format
exact configuration format
```

Therefore:

```text
Chapter 3 architecture
       +
live Neosis repository
       +
pinned upstream implementations
       |
       v
actual implementation
```

Never replace those three sources with model-generated assumptions.

---

# 430. IMPLEMENTATION AGENT OPERATING INSTRUCTIONS

### Rule 1 — Do not drift

You are implementing an existing architecture.

Do not replace it because a local design appears easier.

### Rule 2 — Discover before editing

Always:

```text
inspect
verify
map
implement
test
```

### Rule 3 — Upstream first

Before implementing research behavior locally:

```text
inspect pinned upstream
```

If it exists upstream, reuse it.

### Rule 4 — Adapter, not fork

Keep Neosis-specific logic at the integration boundary.

### Rule 5 — Canonical truth stays canonical

PostgreSQL remains canonical.

### Rule 6 — Evidence before promotion

No memory/graph promotion before canonical evidence exists.

### Rule 7 — No hidden fallback

Engine selection must be observable.

### Rule 8 — No hidden assumptions

If a path/function/schema is unclear:

```text
inspect repository
```

### Rule 9 — Preserve public contracts

Do not expose upstream APIs directly.

### Rule 10 — Keep central nodes thin

Do not turn routes/workers/memory router into research hubs.

### Rule 11 — Pin upstreams

Record exact revisions.

### Rule 12 — Preserve partial results

Do not destroy evidence after partial failure.

### Rule 13 — Enforce budgets

No unlimited research.

### Rule 14 — Preserve workspace isolation

Every canonical research artifact is workspace-scoped.

### Rule 15 — Test every boundary

No phase advances on code compilation alone.

---

# 431. AGENT EXECUTION LOOP

For future phase-rulebook work:

```text
READ architecture section
        |
        v
INSPECT live repository
        |
        v
INSPECT pinned upstream
        |
        v
MAP upstream -> Neosis boundary
        |
        v
IMPLEMENT smallest compatible change
        |
        v
RUN focused tests
        |
        v
RUN integration tests
        |
        v
CHECK provenance
        |
        v
CHECK workspace isolation
        |
        v
CHECK anti-pattern list
        |
        v
UPDATE implementation inventory
        |
        v
CONTINUE
```

Never:

```text
assume
  ->
rewrite
  ->
continue
```

---

# 432. FINAL ARCHITECTURAL SUMMARY

The final target is:

```text
                         +-----------------------+
                         |       NeosisLM        |
                         |                       |
                         | Workspace / Auth      |
                         | Research State        |
                         | Evidence / Provenance |
                         | Memory / State        |
                         | API / SSE             |
                         | Usage / Cost          |
                         +-----------+-----------+
                                     |
                                     v
                         +-----------------------+
                         | Research API /        |
                         | Research Service      |
                         +-----------+-----------+
                                     |
                                     v
                         +-----------------------+
                         | Neosis Research       |
                         | Engine                |
                         +-----------+-----------+
                                     |
                    +----------------+----------------+
                    |                                 |
                    v                                 v
          +----------------------+          +----------------------+
          | Strategy Capability  |          | Primary Execution    |
          |                      |          |                      |
          | STORM (optional)     |          | Open Deep Research   |
          | perspectives         |          | deep research        |
          | questions            |          |                      |
          +----------------------+          +----------+-----------+
                                                       |
                                                       v
                                           +------------------------+
                                           | Retrieval / Tool Layer |
                                           |                        |
                                           | GPT Researcher         |
                                           | retrievers              |
                                           | Web                    |
                                           | Academic               |
                                           | MCP                    |
                                           +-----------+------------+
                                                       |
                                                       v
                                           +------------------------+
                                           | Normalize + Tag +      |
                                           | Evidence + Provenance  |
                                           +-----------+------------+
                                                       |
                            +------------------+--------+----------------+
                            |                  |                         |
                            v                  v                         v
                     PostgreSQL          Memory candidates         Graph candidates
                     canonical           promotion                 promotion
                     state                       |                         |
                            |                    v                         v
                            |              memory system              Neo4j
                            |                                        projection
                            v
                     Report / artifacts
```

The ownership rule is:

> **Upstream systems own research execution. NeosisLM owns canonical research state, evidence, provenance, policy, workspace isolation, memory promotion, graph promotion, observability, and product behavior.**

The integration rule is:

> **Do not build a local research engine merely because the upstream engines are difficult to integrate. Integrate mature upstream behavior behind a stable Neosis boundary.**

The migration rule is:

```text
CURRENT RESEARCH MODE
        |
        v
RESEARCH ENGINE BOUNDARY
        |
        v
MATURE UPSTREAM CAPABILITIES
        |
        v
NEOSIS NORMALIZATION
        |
        +--> state
        +--> evidence
        +--> provenance
        +--> report
        +--> memory candidates
        +--> graph candidates
```

---

# 433. FINAL INSTRUCTION TO THE IMPLEMENTATION AGENT

Do not reinterpret this document as permission to redesign NeosisLM.

Implement Chapter 3 as an integration/migration:

```text
CURRENT NEOSIS
       |
       | preserve product contracts
       v
NEOSIS RESEARCH ENGINE
       |
       | delegate
       v
MATURE UPSTREAM SYSTEMS
       |
       v
CANONICAL NEOSIS RESEARCH FABRIC
```

Whenever there is a choice between:

```text
A. reimplement upstream research behavior
B. adapt to upstream behavior
```

choose **B**, unless a concrete, documented incompatibility makes it impossible.

Whenever there is a choice between:

```text
A. guess repository details
B. inspect the repository
```

choose **B**.

Whenever there is a choice between:

```text
A. store raw upstream output as truth
B. normalize it into canonical evidence/artifacts first
```

choose **B**.

Whenever there is a choice between:

```text
A. automatically promote all research output
B. use explicit promotion boundaries
```

choose **B**.

Whenever there is a choice between:

```text
A. change the architecture to fit a convenient implementation
B. adapt the implementation to the architecture
```

choose **B**.

That is the core engineering discipline of Chapter 3.
