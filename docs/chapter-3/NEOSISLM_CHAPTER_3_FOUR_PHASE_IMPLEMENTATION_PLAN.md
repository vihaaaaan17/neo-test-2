# NeosisLM — Chapter 3 Four-Phase Implementation Plan
## Research Mode / Advanced Research Engine

**Document status:** Implementation plan

**Parent architecture contract:**
`NEOSISLM_CHAPTER_3_RESEARCH_ENGINE_ARCHITECTURE_AND_MIGRATION_STRATEGY.md`

**Scope:** Four implementation phases only. This document intentionally does not define subphases, tickets, or step-by-step work packages. Those can be generated later as a separate phase rulebook from this plan.

**Primary goal:** Execute the Chapter 3 architecture contract as a controlled migration from the current prototype Research Mode to a production-grade, upstream-first Research Engine.

---

# 1. HOW TO USE THIS DOCUMENT

This document is the execution plan for the Chapter 3 architecture.

The architecture document defines:

```text
what the system must become
why the architecture is structured this way
what is canonical
what is delegated
what is prohibited
what invariants must survive
```

This implementation plan defines:

```text
in what four large phases the system should be migrated
what each phase must accomplish
what implementation areas are touched
what artifacts must exist
what tests must pass
what must remain unchanged
where the phase stops
```

It does not replace the architecture document.

It does not authorize deviations from the architecture document.

The implementation agent must read:

```text
1. Chapter 3 Architecture & Migration Strategy
2. this four-phase implementation plan
3. the live Neosis repository
4. the pinned upstream implementations
```

before making major changes.

---

# 2. IMPLEMENTATION PHILOSOPHY

The migration is not:

```text
old research agent
    ->
rewrite everything
```

It is:

```text
current prototype
    ->
formal boundary
    ->
canonical research fabric
    ->
mature upstream execution
    ->
evaluation
    ->
cutover
```

The core implementation principle is:

> **Move complexity out of the custom Neosis research loop and into mature upstream systems while moving canonical state, evidence, provenance, policy, and product ownership into Neosis.**

The final repository should contain less custom research reasoning than the current prototype, even though the overall system is substantially more capable.

---

# 3. TARGET FOUR-PHASE SEQUENCE

```text
PHASE 1
Research Engine Discovery, Upstream Integration & Foundation
        |
        v
PHASE 2
Neosis Research State, Evidence, Tagging & Provenance Layer
        |
        v
PHASE 3
Production Research Execution & Engine Composition
        |
        v
PHASE 4
Evaluation, Quality/Cost Optimization, Cutover & Operationalization
```

The phase order is intentional.

Do not begin full production integration before canonical research state exists.

Do not benchmark before evidence and provenance are durable.

Do not delete the prototype before the new engine is measured.

---

# 4. GLOBAL IMPLEMENTATION RULES

The following rules apply to all four phases.

## Rule 1 — Discover before editing

Before changing a documented local file:

```text
inspect
verify
identify callers
identify tests
map responsibility
then edit
```

Do not create duplicate paths merely because a documented path has moved.

## Rule 2 — Upstream before reimplementation

Before implementing deep-research behavior locally:

```text
inspect the pinned upstream implementation
```

If the capability exists upstream, adapt it.

Do not reproduce it under a new local class name.

## Rule 3 — Canonical state remains Neosis-owned

PostgreSQL remains canonical.

Neo4j remains a projection.

Redis/Arq remains infrastructure.

Upstream runtime state remains execution state.

## Rule 4 — ResearchRun is product identity

`run_id` is the canonical Research Run identity.

`job_id` is infrastructure identity.

Do not reverse these roles.

## Rule 5 — Evidence before synthesis

Normalize research evidence before it becomes durable product-level research input.

## Rule 6 — Provenance cannot be optional in the data model

Not every artifact must have complete provenance, but every artifact that is not fully traceable must be marked accordingly.

## Rule 7 — Memory promotion is explicit

Research output does not automatically become Knowledge Memory or Research Memory.

## Rule 8 — Graph promotion is explicit

Research output does not automatically become Research Output KG truth.

## Rule 9 — No hidden fallback

If another research runtime executes the run, record the actual engine and revision.

## Rule 10 — No three-supervisor architecture

Do not make Open Deep Research, STORM, and GPT Researcher independently plan and execute the same research request by default.

## Rule 11 — Preserve rollback

The legacy Research Mode remains available until evaluation and cutover gates are met.

## Rule 12 — Keep core product APIs engine-neutral

The UI and public API must not depend directly on upstream runtime object shapes.

## Rule 13 — No unbounded research

Tasks, concurrency, time, tokens, provider calls, and cost must be bounded.

## Rule 14 — Keep central files thin

Do not turn these into Research Engine implementations:

```text
app/api/routes/workspaces.py
app/workers/tasks.py
app/services/memory_router.py
```

## Rule 15 — Phase gates are mandatory

No phase is complete because the code "works".

Every phase ends only after its exit gate is executed and recorded.

---

# 5. PHASE 1 — RESEARCH ENGINE DISCOVERY, UPSTREAM INTEGRATION & FOUNDATION

## 5.1 Objective

Phase 1 establishes the factual implementation baseline.

The purpose is to remove uncertainty before new canonical state or production runtime code is built.

Phase 1 must answer:

```text
What exists in the live Neosis repository?
What exactly does the current Research Mode do?
Which upstream capabilities are actually available?
Which upstream versions will be used?
How will they be isolated?
Which system owns which responsibility?
How will the ResearchEngine boundary look?
```

This phase is primarily:

```text
discovery
pinning
compatibility
boundary definition
foundation
```

It is not the production cutover phase.

---

## 5.2 Phase 1 target state

At the end of Phase 1:

```text
Current Research Mode is mapped and frozen as the baseline.
Upstream repositories/versions are inspected.
Upstream revisions are pinned.
Upstream licenses are recorded.
Runtime compatibility is known.
Retriever/academic/MCP capabilities are known.
ResearchEngine responsibility is defined.
Integration boundaries are defined.
Initial smoke tests exist.
No production behavior has been silently replaced.
```

---

## 5.3 Current-code inventory

The implementation agent must inspect at minimum:

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

Also inspect:

```text
existing migrations
existing tests
existing config
existing Docker/runtime configuration
existing Redis/Arq configuration
existing object storage abstraction
existing tracing/observability
existing quota service
existing workspace authorization
```

The exact inventory may be broader after discovery.

---

## 5.4 Freeze the current Research Mode baseline

Before large modifications, capture the current behavior of:

```text
ResearchRequest
POST /workspaces/{workspace_id}/research
run_research_agent_job
ResearchModeOrchestrator
WebSearchTool
OutputGraph projection
Redis progress events
```

The baseline should be reproducible enough to serve as the legacy benchmark.

Do not modify the baseline while simultaneously trying to measure it.

---

## 5.5 Document the current prototype execution path

The inventory should describe:

```text
API request
    ->
job creation
    ->
worker
    ->
ResearchModeOrchestrator
    ->
planner
    ->
executor loop
    ->
WebSearchTool
    ->
synthesizer
    ->
OutputGraph
    ->
reporter
    ->
Redis events
    ->
graph projection
```

This becomes the comparison path for later phases.

---

## 5.6 Inspect Open Deep Research

Inspect the pinned/open-source repository directly.

Determine:

```text
entrypoint
research graph structure
configuration model
tool interfaces
retriever interfaces
MCP support
model interfaces
event/stream behavior
runtime assumptions
Python version
dependency requirements
tests
license
```

Do not implement the adapter from README-level assumptions alone.

---

## 5.7 Pin Open Deep Research

Because the selected upstream is treated as a pinned/reference implementation, Phase 1 must establish:

```text
repository
commit/revision
license
date pinned
runtime compatibility
local patch state
```

Do not depend only on:

```text
main
latest
floating git URL
```

---

## 5.8 Inspect STORM

Determine:

```text
current package/version
module boundaries
research workflow
retriever interfaces
question/perspective interfaces
outline interfaces
citation behavior
model abstraction
LiteLLM compatibility
document grounding support
license
```

The intent is to identify exactly which STORM capability will be reused.

Do not assume STORM becomes the main Research Engine.

---

## 5.9 Inspect GPT Researcher

Determine:

```text
planner/execution boundary
retriever architecture
crawler architecture
custom retriever hooks
academic retrievers
MCP support
reporting flow
provider abstractions
runtime dependencies
license
```

Do not copy the entire framework into Neosis.

---

## 5.10 Build an upstream capability matrix

Create a matrix similar to:

| Capability | Open Deep Research | STORM | GPT Researcher | Neosis responsibility |
|---|---|---|---|---|
| deep-research execution | primary candidate | optional | available | orchestration/policy |
| perspective/question generation | optional | primary candidate | possible | strategy policy |
| web retrieval | supported | supported | broad | routing |
| academic retrieval | supported options | retriever-dependent | supported | routing/policy |
| MCP | supported | capability-dependent | supported | authorization/policy |
| report generation | supported | supported | supported | artifact/provenance |
| evidence normalization | upstream output | upstream output | upstream output | canonical |
| provenance | source metadata | citations | source metadata | canonical |
| ResearchRun state | no | no | no | canonical |
| memory promotion | no | no | no | canonical |
| graph promotion | no | no | no | canonical |

The exact matrix must be corrected against the pinned revisions.

---

## 5.11 Inspect provider/runtime compatibility

Compare:

```text
Neosis Python version
Open Deep Research runtime
STORM runtime
GPT Researcher runtime
dependency versions
async model
http clients
search SDKs
MCP SDKs
```

Do not perform a repository-wide runtime migration merely to satisfy one dependency without evaluating isolation first.

---

## 5.12 Decide upstream runtime isolation

Choose one of:

```text
in-process library
isolated worker
vendored source
internal service
```

based on:

```text
dependency compatibility
runtime conflicts
startup
observability
failure isolation
maintenance
upstream lifecycle
```

The selected approach must be documented.

---

## 5.13 Establish ResearchEngine boundary

Define the product-owned abstraction.

At minimum it must conceptually support:

```text
start
execute
stream
cancel
return normalized output
report usage
```

The exact interface may be refined during implementation.

The public API must depend only on the Neosis boundary.

---

## 5.14 Define engine responsibility matrix

Establish:

```text
Neosis
    owns policy/state/provenance/product output

Open Deep Research
    owns primary deep-research execution

STORM
    owns optional strategy/question/outline capabilities

GPT Researcher
    owns selected reusable retrieval/crawling capabilities
```

If this matrix changes after inspection, record an ADR.

---

## 5.15 Establish revision registry

Create:

```text
docs/CH3_UPSTREAM_REVISION.md
```

or equivalent.

It must contain:

```text
repository
version/revision
license
archive/maintenance state
runtime constraints
local patches
patch reasons
```

---

## 5.16 Establish implementation inventory

Create:

```text
docs/CH3_IMPLEMENTATION_INVENTORY.md
```

with:

```text
Neosis path
verified symbol
current role
target role
upstream path
upstream symbol
adapter responsibility
tests
status
notes
```

The inventory becomes the main place for resolving document/repository mismatches.

---

## 5.17 Establish initial integration skeleton

Only create the integration structure needed to prove the architecture.

Preferred target:

```text
app/integrations/research_engine/
```

with responsibilities such as:

```text
engine
config
open_deep_research
storm
gpt_researcher
retrievers
normalizers
provenance
events
errors
schemas
health
```

Do not implement all logic immediately.

The skeleton exists to establish clean boundaries.

---

## 5.18 Phase 1 tests

At the end of Phase 1, implement/execute:

```text
repository discovery checks
upstream import/startup smoke tests
ResearchEngine interface tests
configuration loading tests
upstream revision verification
runtime compatibility checks
retriever capability smoke tests
```

The tests must prove that the selected upstream systems can actually be loaded or invoked under the selected integration strategy.

---

## 5.19 Phase 1 non-goals

Do not use Phase 1 to:

```text
create final ResearchRun schema
replace the legacy engine
build full evidence persistence
build full memory promotion
build final graph promotion
run production traffic
remove old research code
```

Those belong to later phases.

---

## 5.20 Phase 1 exit gate

Phase 1 is complete only when:

```text
[ ] Current Research Mode is fully mapped.
[ ] Legacy baseline is reproducible.
[ ] Current route/job/orchestrator boundaries are documented.
[ ] Open Deep Research is inspected and pinned.
[ ] STORM is inspected and pinned.
[ ] GPT Researcher is inspected and pinned.
[ ] Licenses are recorded.
[ ] Runtime compatibility is known.
[ ] Retriever capabilities are verified.
[ ] Academic retrieval capabilities are verified.
[ ] MCP capability is verified where enabled.
[ ] Engine responsibility matrix exists.
[ ] ResearchEngine boundary exists.
[ ] Initial integration skeleton exists.
[ ] Implementation inventory exists.
[ ] Upstream revision registry exists.
[ ] Phase 1 tests pass.
```

Do not proceed if the selected upstream runtime is still a guess.

---

# 6. PHASE 2 — NEOSIS RESEARCH STATE, EVIDENCE, TAGGING & PROVENANCE

## 6.1 Objective

Phase 2 establishes the canonical Neosis research fabric.

This is the architectural transition from:

```text
research output as strings
```

to:

```text
research output as canonical domain objects
```

The central implementation principle is:

> **No upstream result should become a durable Neosis research fact before it passes the canonical normalization boundary.**

---

## 6.2 Phase 2 target state

At the end of Phase 2, Neosis should have canonical concepts equivalent to:

```text
ResearchRun
ResearchTask
ResearchEvidence
ResearchSource
ResearchArtifact
ResearchReport
ResearchUsage
ResearchEvent
```

with:

```text
workspace ownership
lifecycle
timestamps
provenance
versioning
tags
```

where applicable.

---

## 6.3 Design the ResearchRun model

Establish the canonical run identity.

It must support:

```text
run_id
workspace_id
owner_id
objective
status
engine
engine_revision
configuration version/digest
created_at
started_at
completed_at
parent_run_id where needed
error metadata
usage summary
```

Do not overfit the model to Open Deep Research.

The model must remain valid if the upstream runtime changes.

---

## 6.4 Design ResearchTask state

The task model must represent:

```text
task_id
run_id
parent_task_id
objective
status
ordering/dependencies
strategy/runtime
timestamps
failure metadata
usage
```

The task model should be able to represent research decomposition without copying an upstream task schema wholesale.

---

## 6.5 Establish run/task state machine

Implement canonical lifecycle handling.

The vocabulary should support concepts equivalent to:

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

and task equivalents.

State transitions must be validated.

Do not allow arbitrary status strings to become the lifecycle model.

---

## 6.6 Define ResearchEvidence

Implement a first-class evidence model.

Core fields should cover:

```text
evidence identity
run/task ownership
source reference
retriever/provider
query
retrieved timestamp
content/excerpt
locator
fingerprint
status
provenance
```

Use a minimal core plus metadata.

---

## 6.7 Define ResearchSource relationship

Reuse the existing Neosis Source/SourceSnapshot concept where applicable.

Do not create a parallel source identity system simply because research sources originate externally.

Define how:

```text
external research source
```

maps to:

```text
Neosis canonical source reference
```

without breaking existing workspace source semantics.

---

## 6.8 Define source types

Establish controlled values for concepts such as:

```text
workspace
user-provided
external web
academic
MCP
system reference
```

The exact vocabulary should follow repository conventions.

---

## 6.9 Evidence identity and deduplication

Implement a canonical evidence identity strategy.

Consider:

```text
source
snapshot
fingerprint
locator
provider ID
canonical URL
```

Do not use search-result ordering as identity.

---

## 6.10 Implement evidence normalization contract

Define:

```text
UpstreamResult
    ->
NormalizedSource
    ->
NormalizedEvidence
```

The normalizer must handle:

```text
provider metadata
URL normalization
retrieval timestamp
content extraction
locator
provider identity
fingerprint
source type
```

---

## 6.11 Implement claim/finding representation

The architecture separates:

```text
evidence
claim
finding
synthesis
report
```

Implement only the minimum canonical structure needed for Chapter 3.

Do not build the full future research-critic or contradiction engine yet.

But do preserve enough relationships for future implementation.

---

## 6.12 Implement tagging

Establish controlled research tags.

At minimum support conceptual categories:

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
academic
web
mcp
memory_candidate
graph_candidate
external
workspace_derived
```

The final taxonomy must be controlled.

---

## 6.13 Implement provenance model

Provenance should be able to trace:

```text
claim
    ->
evidence
    ->
source
    ->
snapshot/observation
    ->
retrieval
    ->
task
    ->
run
    ->
workspace
```

Do not implement provenance independently inside each upstream adapter.

---

## 6.14 Implement provenance status

Support explicit concepts such as:

```text
complete
partial
unresolved
verified
unverified
synthetic
```

Do not pretend missing provenance is complete.

---

## 6.15 Implement citation normalization

The canonical citation layer should resolve:

```text
upstream citation
    ->
canonical evidence
    ->
canonical source
```

Failures should result in:

```text
unresolved/partial provenance
```

not fabricated identifiers.

---

## 6.16 Implement ResearchArtifact

Research artifacts should represent durable product outputs such as:

```text
plan
claim
finding
report
graph candidate
memory candidate
```

The exact artifact taxonomy should remain controlled.

---

## 6.17 Implement ResearchReport

The report model must be able to preserve:

```text
run_id
objective
status
content
citations/evidence references
source summary
limitations
warnings
version
```

Report persistence must be independent from live worker execution.

---

## 6.18 Implement ResearchUsage

Capture at least:

```text
model calls
input tokens
output tokens
retrieval calls
search calls
MCP calls
latency
cost estimate/reported usage
```

Distinguish:

```text
reported
estimated
unavailable
```

where necessary.

---

## 6.19 Implement ResearchEvent

Create a canonical event representation.

Potential lifecycle events:

```text
research.started
research.planning
research.task.started
research.task.completed
research.retrieval.started
research.retrieval.completed
research.evidence.added
research.synthesis.started
research.report.updated
research.completed
research.partial
research.cancelled
research.failed
```

The final vocabulary should follow repository conventions.

---

## 6.20 Establish canonical repositories

Create repository-level persistence for:

```text
run
task
evidence
artifact
source metadata if required
usage
events
```

Repositories must remain database-only.

They must not call upstream providers.

---

## 6.21 Establish ResearchService

Create the service-level boundary that coordinates:

```text
authorization
configuration
run lifecycle
engine execution
normalization
persistence
promotion scheduling
```

It must not implement deep-research algorithms.

---

## 6.22 Establish provenance service

Create or establish the canonical service for:

```text
evidence lineage
citation resolution
source mapping
claim support
provenance status
```

---

## 6.23 Establish normalization service

Create or establish the canonical normalization service for:

```text
upstream results
retriever results
report output
citation metadata
source metadata
```

---

## 6.24 Establish memory promotion boundary

Research output should become:

```text
memory candidate
```

rather than directly becoming KnowledgeMemory.

Use the existing:

```text
app/services/memory_router.py
```

as the product boundary.

No upstream adapter writes directly to `KnowledgeMemory`.

---

## 6.25 Establish graph promotion boundary

Research output should become:

```text
graph candidate
```

before Neo4j projection.

Use:

```text
app/repositories/graph.py
```

or the existing graph abstraction.

---

## 6.26 Establish version linkage

Research artifacts should have enough metadata to connect to:

```text
workspace version/commit
research run version
artifact version
```

Do not invent an unrelated version-control system.

---

## 6.27 Establish migration-safe database changes

Add schema/migrations in a non-destructive order:

```text
database migration
    ->
models
    ->
repositories
    ->
services
```

Do not require the new runtime before the canonical tables exist.

---

## 6.28 Phase 2 unit tests

Test:

```text
ResearchRun creation
state transitions
ResearchTask lifecycle
workspace ownership
Evidence creation
Evidence deduplication
Source mapping
Tag validation
Provenance mapping
Citation normalization
Artifact persistence
Report persistence
Usage recording
Event creation
```

---

## 6.29 Phase 2 integration tests

Run:

```text
API
    ->
PostgreSQL
```

without requiring live upstream research first.

The purpose is to prove canonical state correctness independently from upstream behavior.

---

## 6.30 Phase 2 security tests

Verify:

```text
workspace isolation
owner checks
cross-workspace evidence access denied
cross-workspace report access denied
cross-workspace promotion denied
```

---

## 6.31 Phase 2 non-goals

Do not use Phase 2 to:

```text
make Open Deep Research production-primary
implement final retriever routing
build complete UI streaming
perform final cutover
delete legacy research
```

Those belong to Phase 3/4.

---

## 6.32 Phase 2 exit gate

Phase 2 is complete only when:

```text
[ ] ResearchRun canonical model exists.
[ ] ResearchTask canonical model exists.
[ ] Evidence is first-class.
[ ] Source identity is canonicalized.
[ ] Tags are controlled.
[ ] Provenance is reconstructable.
[ ] Citation normalization exists.
[ ] ResearchArtifact exists.
[ ] Report persistence exists.
[ ] Usage tracking exists.
[ ] Event model exists.
[ ] Research repositories exist.
[ ] ResearchService exists.
[ ] Normalization boundary exists.
[ ] Provenance boundary exists.
[ ] Memory promotion boundary exists.
[ ] Graph promotion boundary exists.
[ ] Workspace isolation tests pass.
[ ] Phase 2 tests pass.
```

Do not begin production research traffic until this gate is met.

---

# 7. PHASE 3 — PRODUCTION RESEARCH EXECUTION & ENGINE COMPOSITION

## 7.1 Objective

Phase 3 connects the canonical Neosis research fabric to real upstream research execution.

The target is:

```text
Research API
    ->
ResearchService
    ->
ResearchEngine
    ->
Open Deep Research
    ->
retrievers/tools
    ->
normalized evidence
    ->
canonical artifacts/report
```

with optional:

```text
STORM capabilities
GPT Researcher capabilities
academic providers
MCP
```

---

## 7.2 Phase 3 target state

At the end of Phase 3:

```text
real Research Runs execute through ResearchEngine
Open Deep Research is primary where approved
STORM is capability-scoped
GPT Researcher is capability-scoped
retrieval is policy-driven
evidence is canonicalized during execution
events are normalized
cancellation works
budgets are enforced
partial research works
legacy prototype is no longer primary
```

---

## 7.3 Integrate ResearchEngine factory/strategy resolver

Create one central selection mechanism.

Conceptually:

```text
ResearchService
    ->
ResearchEngineFactory / strategy resolver
    ->
selected runtime
```

Avoid scattered engine selection.

---

## 7.4 Integrate Open Deep Research

Implement the Open Deep Research adapter.

Responsibilities:

```text
Neosis request
    ->
upstream config/request
```

and:

```text
upstream output
    ->
Neosis event/result DTO
```

The adapter must not directly write PostgreSQL.

---

## 7.5 Integrate Open Deep Research execution state

Where upstream execution IDs exist, map:

```text
Neosis run/task
    ->
upstream execution identifier
```

Store the external ID as metadata.

Do not make it the primary product identity.

---

## 7.6 Integrate Open Deep Research events

Normalize upstream execution events into:

```text
Neosis ResearchEvent
```

Map:

```text
planning
research
tool use
compression
report
completion
error
```

into the Neosis event vocabulary.

---

## 7.7 Integrate STORM capability

Only integrate the STORM functionality selected in Phase 1.

Potential capability:

```text
perspective/question enrichment
outline support
retrieval strategy
```

Do not automatically run a second full report-generation pipeline.

---

## 7.8 Integrate GPT Researcher capability

Only integrate the GPT Researcher capability selected in Phase 1.

Likely candidates:

```text
retriever ecosystem
crawler
academic retrieval
custom retriever interface
MCP integration
```

Do not copy the full planner/executor/reporter architecture.

---

## 7.9 Implement retriever registry

Centralize retriever selection.

Potential categories:

```text
web
academic
arxiv
pubmed
custom
mcp
```

The registry should support:

```text
configuration
health
capability metadata
selection
```

---

## 7.10 Implement retriever policy

The policy should consider:

```text
research strategy
source requirements
topic/domain
provider health
provider cost
provider latency
academic requirement
workspace source restrictions
```

Do not encode routing into prompt text alone.

---

## 7.11 Integrate web retrieval

The existing:

```text
app/services/web_search.py
```

may remain a provider adapter.

It must not remain the only retrieval architecture.

Integrate it into the broader provider-neutral retriever boundary if still used.

---

## 7.12 Integrate academic retrieval

Implement configured academic retrievers.

The exact providers must match Phase 1 verified capabilities.

Ensure metadata contains where available:

```text
title
authors
venue
publication date
DOI
ArXiv ID
PubMed/PMC ID
URL
```

---

## 7.13 Integrate MCP research

If enabled:

```text
Neosis policy
    ->
allowed MCP capability
    ->
upstream MCP execution
```

Enforce:

```text
server allowlist
credentials
workspace permissions
read/write policy
usage accounting
```

---

## 7.14 Implement source policy

Support policy concepts such as:

```text
external-only
workspace-only
workspace + external
selected-source-only
academic-only
```

The policy must be applied before evidence enters research context.

---

## 7.15 Implement context selection

Build bounded research context from:

```text
objective
selected sources
selected memory
canonical evidence
prior artifacts
```

Do not inject all memories automatically.

---

## 7.16 Integrate evidence normalization during execution

The execution pipeline should be:

```text
retrieve
    ->
normalize
    ->
deduplicate
    ->
persist evidence
    ->
continue research
```

Evidence persistence should happen before final synthesis whenever possible.

This reduces provenance loss on partial failure.

---

## 7.17 Integrate claim/finding normalization

When upstream output contains findings or claims:

```text
normalize
    ->
link to evidence
    ->
persist
```

Do not accept unsupported claims as canonical facts.

---

## 7.18 Integrate report normalization

The upstream report must be converted into a Neosis report artifact.

Normalize:

```text
content
citations
evidence references
warnings
limitations
status
version
```

---

## 7.19 Implement report finalization

Do not mark a run complete merely because upstream returned text.

The finalization process should ensure:

```text
tasks resolved
evidence persisted
report persisted
usage recorded
events emitted
promotions scheduled where required
```

---

## 7.20 Implement progress events

Normalize progress into product concepts:

```text
planning
researching
collecting evidence
validating
synthesizing
finalizing
completed
partial
failed
cancelled
```

Do not expose raw upstream node names.

---

## 7.21 Implement streaming

Connect:

```text
ResearchEvent
    ->
Redis/pub-sub
    ->
SSE or equivalent
```

The browser consumes Neosis events.

---

## 7.22 Implement cancellation

Connect:

```text
API cancellation
    ->
ResearchService
    ->
worker
    ->
ResearchEngine
    ->
upstream runtime
```

Stop scheduling new work.

Interrupt active upstream work where supported.

Preserve evidence.

---

## 7.23 Implement partial research

If:

```text
some tasks succeed
some fail
```

preserve successful evidence.

Set:

```text
PARTIAL
```

when policy requires.

The report must expose incomplete coverage.

---

## 7.24 Implement retries

Apply retries to:

```text
transient provider failures
network errors
429s
safe retrieval operations
worker delivery failures
```

Do not duplicate canonical evidence.

---

## 7.25 Implement ambiguous-outcome reconciliation

Where supported, reconcile:

```text
timeout after remote execution
```

before retrying.

This is especially important for remote job creation or external side effects.

---

## 7.26 Implement budgets

Apply outer controls for:

```text
max research duration
max total tokens
max per-task tokens
max cost
max tasks
max concurrency
max retrieval calls
max MCP calls
```

Do not rely solely on upstream limits.

---

## 7.27 Implement workspace isolation in execution

Every execution operation must know:

```text
workspace_id
run_id
```

Evidence and context must be scoped.

Do not let a provider cache private workspace content globally.

---

## 7.28 Implement usage reporting

Record:

```text
tokens
provider/model
retrieval calls
search calls
MCP calls
latency
estimated/reported cost
```

Usage should be updated during or after the run.

---

## 7.29 Implement resource backpressure

Bound:

```text
worker concurrency
run concurrency
task concurrency
provider concurrency
```

Prevent unbounded fan-out from upstream planners.

---

## 7.30 Integrate memory candidates

When the run produces durable findings:

```text
finding
    ->
memory candidate
```

Then:

```text
promotion policy
    ->
MemoryRouter
```

Do not automatically promote everything.

---

## 7.31 Integrate graph candidates

When the run produces graph-worthy findings:

```text
finding
    ->
graph candidate
```

Then:

```text
validation
    ->
graph repository
    ->
Neo4j projection
```

Do not bypass canonical storage.

---

## 7.32 Integrate workspace versions

If a run consumed workspace sources:

```text
record relevant workspace version/commit
```

Do not silently replace source snapshots after the run begins.

---

## 7.33 Legacy path remains available

The legacy:

```text
ResearchModeOrchestrator
```

remains runnable as the benchmark/rollback baseline.

It must no longer be the primary production path once Phase 3 is accepted.

---

## 7.34 Phase 3 unit tests

Test:

```text
engine selection
upstream request mapping
upstream output mapping
event normalization
retriever selection
provider fallback
academic routing
MCP authorization
cancellation propagation
budget enforcement
usage capture
```

---

## 7.35 Phase 3 integration tests

Run:

```text
FastAPI
    ->
ResearchService
    ->
ResearchEngine
    ->
upstream runtime
    ->
retriever
    ->
PostgreSQL
    ->
Redis
```

Validate real lifecycle transitions.

---

## 7.36 Phase 3 end-to-end tests

Test:

```text
start research
observe progress
retrieve evidence
finish report
view citations
view usage
cancel research
handle partial failure
```

---

## 7.37 Phase 3 non-goals

Do not use Phase 3 to:

```text
remove the legacy baseline
perform final quality sign-off
optimize every provider
implement full contradiction detection
implement the future research critic
perform large-scale historical backfill
```

Those belong to Phase 4 or later chapters.

---

## 7.38 Phase 3 exit gate

Phase 3 is complete only when:

```text
[ ] Production ResearchEngine executes real runs.
[ ] Open Deep Research adapter executes successfully.
[ ] Primary engine identity is persisted.
[ ] STORM capability is integrated where approved.
[ ] GPT Researcher capability is integrated where approved.
[ ] Retriever registry works.
[ ] Web retrieval works.
[ ] Academic retrieval works where enabled.
[ ] MCP works where enabled.
[ ] Evidence is normalized during execution.
[ ] Evidence persists before final synthesis where possible.
[ ] Provenance survives execution.
[ ] Events are normalized.
[ ] Streaming/progress works.
[ ] Cancellation works.
[ ] Partial research works.
[ ] Retry/recovery works.
[ ] Budgets work.
[ ] Usage is recorded.
[ ] Workspace isolation passes.
[ ] Memory promotion boundary works.
[ ] Graph promotion boundary works.
[ ] Legacy ResearchModeOrchestrator is no longer primary.
[ ] Phase 3 tests pass.
```

---

# 8. PHASE 4 — EVALUATION, QUALITY/COST OPTIMIZATION, CUTOVER & OPERATIONALIZATION

## 8.1 Objective

Phase 4 proves the new Research Engine is ready for production.

It is not an implementation phase in the sense of adding the main architecture.

It is the validation, optimization, cutover, rollback, and operational hardening phase.

---

## 8.2 Phase 4 target state

At the end of Phase 4:

```text
quality is measurable
cost is measurable
latency is measurable
failure behavior is tested
provenance is auditable
workspace isolation is proven
shadow/baseline comparison is complete
new engine is production-primary
legacy engine is deprecated
rollback is documented
runbook exists
```

---

## 8.3 Freeze the new candidate

Before final evaluation, freeze:

```text
ResearchEngine code revision
upstream revisions
retriever configuration
model configuration
ResearchRun schemas
provenance rules
evaluation metric definitions
```

Do not continually change the system during the final benchmark window without recording version changes.

---

## 8.4 Establish benchmark corpus

Include:

```text
simple factual research
multi-hop research
multi-source synthesis
academic research
historical research
current-information research
conflicting evidence
source-discovery tasks
long-tail topics
temporal/date-bounded tasks
citation-heavy research
workspace + external mixed research
```

---

## 8.5 Establish baseline measurements

Measure the legacy prototype:

```text
quality
evidence coverage
citations
latency
cost
failure rate
```

The baseline must remain frozen.

---

## 8.6 Establish upstream standalone measurements

Where practical, measure selected upstream runtime independently.

This separates:

```text
upstream quality
```

from:

```text
Neosis integration quality
```

---

## 8.7 Establish integrated measurements

Measure:

```text
Neosis API
    ->
ResearchEngine
    ->
canonical evidence
    ->
report
```

using the same research corpus.

---

## 8.8 Evaluate research breadth

Measure whether research covers relevant dimensions rather than merely generating many sources.

Possible measures:

```text
subquestion coverage
source diversity
topic coverage
```

---

## 8.9 Evaluate research depth

Measure:

```text
iterative exploration
cross-source validation
follow-up research
source triangulation
```

---

## 8.10 Evaluate evidence quality

Measure:

```text
source relevance
source quality
evidence support
evidence completeness
```

---

## 8.11 Evaluate citation correctness

Test:

```text
citation resolves
citation points to correct source
citation supports claim
locator is correct where available
```

---

## 8.12 Evaluate citation completeness

Measure:

```text
factual claims with supporting citation
```

Do not only verify that citations exist.

---

## 8.13 Evaluate provenance completeness

For sampled findings:

```text
report
    ->
claim
    ->
evidence
    ->
source
    ->
retrieval
    ->
task
    ->
run
```

Measure the percentage of links that can be reconstructed.

---

## 8.14 Evaluate contradiction handling

Use benchmark cases where sources disagree.

Verify:

```text
conflict retained
sources preserved
claim status appropriate
report does not silently collapse disagreement
```

---

## 8.15 Evaluate academic retrieval

Measure:

```text
academic source coverage
metadata completeness
citation correctness
retriever reliability
```

---

## 8.16 Evaluate current-information research

Use live tasks only where necessary.

Verify:

```text
retrieval actually occurs
timestamp is retained
fresh sources appear
provider behavior is observable
```

---

## 8.17 Evaluate cost

Measure:

```text
cost per run
tokens per run
retrieval calls
provider calls
MCP calls
cost by model role
```

---

## 8.18 Evaluate latency

Measure:

```text
time to first progress
time to first evidence
time to report
total run duration
p50
p95
```

---

## 8.19 Evaluate reliability

Test:

```text
worker restart
Redis restart
database restart
upstream restart
provider failure
retriever failure
academic provider failure
MCP failure
LLM timeout
rate limit
budget exhaustion
cancellation
partial task failure
```

---

## 8.20 Evaluate isolation

Prove:

```text
workspace A cannot see workspace B research state
workspace A cannot access workspace B evidence
workspace A cannot access workspace B reports
workspace A cannot promote workspace B memory
workspace A cannot promote workspace B graph
```

Also test cache and event-stream isolation.

---

## 8.21 Evaluate memory promotion

Audit:

```text
why was a memory candidate created?
what evidence supports it?
was promotion explicit?
is workspace ownership correct?
```

---

## 8.22 Evaluate graph promotion

Audit:

```text
graph candidate exists
canonical artifact exists
evidence exists
Neo4j projection is derived
reprojection is possible
```

---

## 8.23 Shadow evaluation

Where cost permits:

```text
same research request
    |
    +--> legacy baseline
    |
    +--> new ResearchEngine
```

Compare:

```text
quality
citations
evidence
latency
cost
failure
```

Shadow outputs must not mutate production memory/graph/workspace state unless explicitly isolated.

---

## 8.24 Determine cutover thresholds

Define thresholds before final sign-off.

Examples:

```text
citation correctness
provenance completeness
workspace isolation
maximum failure rate
maximum p95 latency
maximum cost
minimum evidence quality
```

The exact numerical thresholds are implementation/evaluation decisions.

They must be recorded before using the results to justify cutover.

---

## 8.25 Cost optimization

After quality is acceptable, optimize:

```text
model routing
compression
retriever selection
concurrency
duplicate suppression
context size
```

Do not optimize cost by silently removing evidence or weakening provenance.

---

## 8.26 Latency optimization

Optimize:

```text
parallel research tasks
retriever concurrency
connection reuse
event publication
context compression
```

Do not exceed provider/resource limits.

---

## 8.27 Provider optimization

Measure which providers provide:

```text
quality
cost
latency
reliability
```

Then encode policy rather than hardcoding arbitrary provider preference.

---

## 8.28 Report optimization

Improve:

```text
report structure
citation placement
warning visibility
partial-result presentation
```

without changing canonical provenance semantics.

---

## 8.29 Operational runbook

Complete:

```text
docs/CH3_RESEARCH_MIGRATION_RUNBOOK.md
```

Include:

```text
startup
provider configuration
health checks
run investigation
failure recovery
cancellation
budget issues
provider rotation
rollback
upstream upgrade
benchmark execution
```

---

## 8.30 Observability

Operational dashboards should include:

```text
runs started
runs completed
partial runs
failed runs
cancelled runs
average duration
p95 duration
cost/run
evidence/run
citation unresolved rate
provider errors
retriever errors
worker queue depth
active research concurrency
```

---

## 8.31 Quality monitoring

Monitor:

```text
citation correctness
citation completeness
unsupported claim rate
evidence coverage
source diversity
academic retrieval success
contradiction coverage
```

Metric definitions must remain versioned.

---

## 8.32 Upstream regression policy

Before any upstream revision is accepted:

```text
adapter tests
integration tests
provenance tests
research benchmark
cost benchmark
latency benchmark
isolation tests
```

must be rerun.

---

## 8.33 Cutover preparation

Before switching production traffic:

```text
new engine enabled in controlled environment
legacy baseline preserved
rollback flag verified
database migration verified
monitoring verified
runbook verified
incident procedure verified
```

---

## 8.34 Cutover

The final production decision point should be centralized.

Conceptually:

```text
ResearchService
    ->
ResearchEngineFactory / strategy resolver
    ->
new engine
```

The old path should not remain silently active underneath.

---

## 8.35 Legacy deprecation

After the new engine becomes primary:

```text
legacy ResearchModeOrchestrator
    =
deprecated
```

It may temporarily remain for:

```text
benchmark
debugging
emergency rollback
```

but should stop receiving normal production traffic.

---

## 8.36 Legacy removal

Legacy removal should occur as a separately reviewed cleanup.

Remove only after:

```text
cutover stable
rollback window complete
baseline preserved externally
no active dependency remains
```

---

## 8.37 Rollback test

Actually test:

```text
new engine
    ->
disable
    ->
legacy
```

and verify the product continues to operate.

Do not accept a rollback plan that has never been exercised.

---

## 8.38 Rollback data safety

Rolling back the runtime must not delete:

```text
ResearchRun
ResearchTask
Evidence
Artifacts
Reports
Usage
```

created by the new engine.

If legacy cannot display a new artifact type, preserve the data and expose the limitation explicitly.

---

## 8.39 Phase 4 tests

Run:

```text
benchmark suite
quality suite
citation suite
provenance suite
cost suite
latency suite
reliability suite
isolation suite
rollback suite
promotion audit
```

---

## 8.40 Phase 4 exit gate

Phase 4 is complete only when:

```text
[ ] Benchmark corpus exists.
[ ] Legacy baseline is frozen.
[ ] New engine measurements are complete.
[ ] Standalone upstream measurements are available where useful.
[ ] Research quality threshold is met.
[ ] Evidence quality threshold is met.
[ ] Citation correctness threshold is met.
[ ] Citation completeness threshold is met.
[ ] Provenance threshold is met.
[ ] Contradiction behavior is acceptable.
[ ] Academic research behavior is acceptable.
[ ] Cost threshold is met.
[ ] Latency threshold is met.
[ ] Reliability threshold is met.
[ ] Isolation tests pass.
[ ] Memory promotion audit passes.
[ ] Graph promotion audit passes.
[ ] Shadow evaluation is complete where used.
[ ] Production cutover is complete.
[ ] Legacy path is deprecated.
[ ] Rollback has been tested.
[ ] Runbook is complete.
[ ] Operational dashboards/alerts exist.
```

---

# 9. PHASE DEPENDENCY GRAPH

The phases are sequential because each produces a dependency for the next.

```text
PHASE 1
Repository + upstream truth
        |
        v
ResearchEngine boundary
        |
        v
PHASE 2
Canonical state + evidence + provenance
        |
        v
PHASE 3
Real upstream execution
        |
        v
PHASE 4
Evaluation + cutover
```

Do not invert this order.

---

# 10. GLOBAL FILE-LEVEL MIGRATION MAP

## `app/api/routes/workspaces.py`

Phase 1:

```text
inspect/freeze
```

Phase 2:

```text
prepare for run creation
```

Phase 3:

```text
thin ResearchRun creation + enqueue
```

Phase 4:

```text
stable production API
```

Must never become:

```text
research engine implementation
```

---

## `app/workers/tasks.py`

Phase 1:

```text
freeze current research job
```

Phase 2:

```text
prepare lifecycle/event persistence
```

Phase 3:

```text
dispatch ResearchService/ResearchEngine
```

Phase 4:

```text
stable production worker path
```

Must never become:

```text
deep research implementation hub
```

---

## `app/orchestration/research_mode.py`

Phase 1:

```text
baseline inspection
```

Phase 2:

```text
new canonical boundaries must not be coupled to its current state representation
```

Phase 3:

```text
becomes compatibility/baseline wrapper or stops being primary
```

Phase 4:

```text
deprecate, then remove later
```

---

## `app/services/web_search.py`

Phase 1:

```text
inspect current provider adapter
```

Phase 2:

```text
define canonical retriever interface around provider output
```

Phase 3:

```text
retain as one provider implementation where appropriate
```

Phase 4:

```text
keep only if still useful
```

---

## `app/services/memory_router.py`

All phases:

```text
remain product-level memory boundary
```

Never:

```text
Open Deep Research-aware
STORM-aware
GPT Researcher-aware
```

---

## `app/services/hybrid_retrieval.py`

Phase 1:

```text
baseline/reference
```

Phase 2:

```text
do not make it canonical research state
```

Phase 3:

```text
retain for existing capabilities/benchmark where useful
```

Phase 4:

```text
evaluate whether still required
```

---

## `app/schemas/graph.py`

Phase 1:

```text
inspect existing OutputGraph
```

Phase 2:

```text
preserve curated graph contract
```

Phase 3:

```text
map research graph candidates into it
```

Phase 4:

```text
audit graph quality and provenance
```

---

## `app/repositories/graph.py`

All phases:

```text
Neo4j projection only
```

Do not make it canonical.

---

## `app/api/deps/llm.py`

Phase 1:

```text
inspect actual state
```

Phase 2:

```text
do not couple canonical domain models to current mock/stub
```

Phase 3:

```text
connect to approved provider/model boundary
```

Phase 4:

```text
measure model cost/latency/reliability
```

---

# 11. PROPOSED NEW FILE RESPONSIBILITIES

The architecture document proposes responsibilities, not mandatory exact paths.

Potential files:

```text
app/integrations/research_engine/engine.py
app/integrations/research_engine/config.py
app/integrations/research_engine/open_deep_research.py
app/integrations/research_engine/storm.py
app/integrations/research_engine/gpt_researcher.py
app/integrations/research_engine/retrievers.py
app/integrations/research_engine/normalizers.py
app/integrations/research_engine/provenance.py
app/integrations/research_engine/events.py
app/integrations/research_engine/errors.py
app/integrations/research_engine/schemas.py
app/integrations/research_engine/health.py
```

Canonical services:

```text
app/services/research.py
app/services/research_state.py
app/services/research_normalization.py
app/services/research_provenance.py
app/services/research_memory.py
app/services/research_graph.py
```

Canonical persistence:

```text
app/models/research.py
app/repositories/research.py
app/schemas/research.py
```

Tests:

```text
tests/unit/research/
tests/integration/research/
tests/e2e/research/
tests/eval/research/
```

Use the live repository convention if it differs.

---

# 12. DATABASE MIGRATION ORDER

When new canonical research tables are required:

```text
1. migration
2. model
3. repository
4. service
5. API/worker wiring
6. runtime integration
7. promotion
8. cutover
```

Avoid:

```text
runtime first
database later
```

---

# 13. TESTING STRATEGY ACROSS ALL PHASES

Testing should progressively increase.

```text
Phase 1
    discovery + upstream smoke

Phase 2
    canonical persistence + provenance

Phase 3
    live integration + lifecycle

Phase 4
    evaluation + reliability + cutover
```

No phase should rely only on end-to-end tests.

---

# 14. TEST DATA STRATEGY

Maintain deterministic test fixtures for:

```text
web source
academic source
duplicate source
contradictory sources
missing citation
partial run
provider failure
MCP failure
workspace source
mixed workspace/external research
```

Where possible, use fixed source snapshots rather than live web content for deterministic tests.

---

# 15. FAILURE TESTING STRATEGY

Every phase must include failure tests appropriate to its scope.

The final system must be tested for:

```text
invalid request
unauthorized workspace
provider outage
retriever timeout
LLM timeout
rate limit
MCP failure
database failure
Redis restart
worker restart
upstream restart
cancellation
budget exhaustion
partial task failure
```

---

# 16. PROVENANCE TESTING STRATEGY

Before Phase 3:

```text
canonical evidence lineage must work
```

During Phase 3:

```text
upstream output must populate lineage
```

During Phase 4:

```text
real reports must pass provenance audits
```

---

# 17. WORKSPACE ISOLATION TESTING STRATEGY

Test at:

```text
API layer
repository layer
event layer
cache layer
research execution layer
memory promotion
graph promotion
```

One isolation test is not sufficient.

---

# 18. RESOURCE CONTROL TESTING STRATEGY

Test:

```text
task concurrency
provider concurrency
token budget
time budget
cost budget
retrieval budget
MCP budget
```

The expected result must be explicit state, not silent truncation.

---

# 19. COST/USAGE TESTING STRATEGY

Test whether usage is captured for:

```text
successful runs
partial runs
failed runs
cancelled runs
retried runs
fallback runs
```

Do not only measure successful completion.

---

# 20. ENGINE SELECTION TESTING STRATEGY

Test:

```text
default strategy
deep strategy
academic strategy
fallback strategy
legacy rollback
```

Verify the recorded engine matches what actually executed.

---

# 21. RETRIEVER TESTING STRATEGY

Test:

```text
web provider
academic provider
duplicate provider result
provider fallback
provider rate limit
provider unavailable
```

---

# 22. MCP TESTING STRATEGY

Test:

```text
allowed MCP server
disallowed MCP server
invalid credentials
MCP unavailable
MCP timeout
MCP result normalization
MCP provenance
```

---

# 23. REPORT TESTING STRATEGY

Test:

```text
report persistence
report versioning
citation mapping
partial report
warning handling
report retrieval after worker restart
```

---

# 24. MEMORY PROMOTION TESTING STRATEGY

Test:

```text
candidate creation
promotion eligibility
explicit promotion
workspace ownership
provenance retention
duplicate promotion
```

---

# 25. GRAPH PROMOTION TESTING STRATEGY

Test:

```text
candidate creation
validation
projection
reprojection
workspace ownership
provenance
Neo4j rebuild
```

---

# 26. LEGACY COMPATIBILITY TESTING

Before Phase 4 cutover:

```text
legacy baseline still executes
legacy output still measurable
legacy rollback path still works
```

Do not remove the only known working fallback before production sign-off.

---

# 27. IMPLEMENTATION ORDER WITHIN EACH PHASE

Do not create subphases here, but use this dependency ordering within implementation work:

```text
inspect
    ->
define contract
    ->
create canonical structure
    ->
implement adapters
    ->
connect execution
    ->
test boundary
    ->
test integration
    ->
measure
    ->
advance
```

This ordering does not authorize skipping any architecture gate.

---

# 28. CHANGESET DISCIPLINE

Each major change should be reviewable.

A useful commit boundary should describe:

```text
what changed
what boundary it affects
why
how it is tested
```

Avoid commits that mix:

```text
research engine
Ground refactor
authentication refactor
unrelated UI work
```

---

# 29. ADR REQUIREMENTS

The implementation plan assumes ADRs are created for:

```text
ResearchEngine boundary
Open Deep Research primary role
STORM role
GPT Researcher role
canonical ResearchRun
evidence/provenance
retriever policy
academic retrieval
MCP
memory promotion
graph promotion
runtime isolation
upstream pinning
cutover/rollback
```

ADR work should happen when the decision is made, not after implementation.

---

# 30. PHASE HANDOFF REQUIREMENTS

Before moving from Phase 1 to Phase 2:

```text
implementation inventory complete enough
upstreams pinned
runtime decision known
```

Before moving from Phase 2 to Phase 3:

```text
canonical state exists
evidence/provenance exists
workspace isolation exists
```

Before moving from Phase 3 to Phase 4:

```text
real execution works
events work
cancellation works
usage works
```

---

# 31. GLOBAL ANTI-PATTERN CHECK

At the end of every phase, search the repository for:

```text
custom deep research planner
custom autonomous supervisor
duplicated retriever framework
raw upstream output writes
direct upstream DB access
raw upstream IDs in public schemas
direct Neo4j writes from engine
direct KnowledgeMemory writes from engine
unbounded asyncio.gather
hidden legacy fallback
```

Any new instance requires architectural review.

---

# 32. PHASE 1 REVIEW CHECKLIST

Before Phase 1 sign-off:

```text
[ ] Current route verified.
[ ] Current worker verified.
[ ] Current orchestrator verified.
[ ] Current search adapter verified.
[ ] Current LLM gateway verified.
[ ] Current memory boundary verified.
[ ] Current graph boundary verified.
[ ] Existing tests inventoried.
[ ] Open Deep Research inspected.
[ ] STORM inspected.
[ ] GPT Researcher inspected.
[ ] Revisions pinned.
[ ] Runtime compatibility checked.
[ ] Capability matrix created.
[ ] ResearchEngine boundary documented.
[ ] ADRs created for material decisions.
```

---

# 33. PHASE 2 REVIEW CHECKLIST

Before Phase 2 sign-off:

```text
[ ] ResearchRun exists.
[ ] ResearchTask exists.
[ ] ResearchEvidence exists.
[ ] ResearchSource mapping exists.
[ ] ResearchArtifact exists.
[ ] ResearchReport exists.
[ ] ResearchUsage exists.
[ ] ResearchEvent exists.
[ ] State transitions validated.
[ ] Evidence identity works.
[ ] Deduplication works.
[ ] Tags work.
[ ] Provenance works.
[ ] Citation normalization works.
[ ] Workspace isolation works.
[ ] Memory promotion boundary exists.
[ ] Graph promotion boundary exists.
```

---

# 34. PHASE 3 REVIEW CHECKLIST

Before Phase 3 sign-off:

```text
[ ] ResearchEngine runs actual research.
[ ] Open Deep Research executes.
[ ] STORM role is scoped.
[ ] GPT Researcher role is scoped.
[ ] Web retrievers work.
[ ] Academic retrievers work where enabled.
[ ] MCP works where enabled.
[ ] Evidence persists during execution.
[ ] Provenance persists.
[ ] Events stream.
[ ] Cancellation works.
[ ] Partial runs work.
[ ] Retries work.
[ ] Budgets work.
[ ] Usage works.
[ ] Memory candidates work.
[ ] Graph candidates work.
[ ] Workspace isolation works.
[ ] Legacy is not primary.
```

---

# 35. PHASE 4 REVIEW CHECKLIST

Before Phase 4 sign-off:

```text
[ ] Benchmark corpus fixed.
[ ] Baseline fixed.
[ ] New engine benchmark complete.
[ ] Citation evaluation complete.
[ ] Provenance evaluation complete.
[ ] Evidence evaluation complete.
[ ] Contradiction evaluation complete.
[ ] Academic evaluation complete.
[ ] Cost evaluation complete.
[ ] Latency evaluation complete.
[ ] Reliability evaluation complete.
[ ] Isolation evaluation complete.
[ ] Shadow evaluation complete where used.
[ ] Rollback tested.
[ ] Runbook complete.
[ ] Monitoring complete.
[ ] Cutover complete.
[ ] Legacy deprecated.
```

---

# 36. FINAL FOUR-PHASE EXIT MATRIX

| Phase | Primary question | Must exist before exit |
|---|---|---|
| Phase 1 | Do we know exactly what we are integrating? | pinned upstreams, capability matrix, ResearchEngine boundary, compatibility evidence |
| Phase 2 | Can Neosis safely own the resulting research state? | canonical Run/Task/Evidence/Artifact/Provenance model |
| Phase 3 | Does the mature upstream research actually run through Neosis? | production ResearchEngine execution, normalized events/evidence, cancellation/budgets |
| Phase 4 | Is it safe and justified to make this the production engine? | benchmark evidence, quality/cost/reliability gates, rollback, cutover |

---

# 37. DEFINITION OF DONE

Chapter 3 implementation is complete only when:

```text
[ ] Phase 1 exit gate passed.
[ ] Phase 2 exit gate passed.
[ ] Phase 3 exit gate passed.
[ ] Phase 4 exit gate passed.
```

and:

```text
[ ] Mature upstream research behavior is genuinely executing.
[ ] Neosis owns canonical research state.
[ ] Evidence is first-class.
[ ] Provenance is reconstructable.
[ ] Retrievers are policy-driven.
[ ] Academic research is supported where enabled.
[ ] MCP is policy-controlled where enabled.
[ ] Memory promotion is explicit.
[ ] Graph promotion is explicit.
[ ] Reports are durable artifacts.
[ ] Usage/cost is measurable.
[ ] Research is bounded.
[ ] Cancellation is supported.
[ ] Partial research is explicit.
[ ] Workspace isolation is proven.
[ ] Quality is benchmarked.
[ ] Cost is benchmarked.
[ ] Reliability is benchmarked.
[ ] Rollback is tested.
[ ] Legacy research is deprecated.
```

---

# 38. FINAL IMPLEMENTATION AGENT INSTRUCTIONS

The implementation agent should use this operating loop:

```text
READ architecture section
        |
        v
IDENTIFY current phase
        |
        v
INSPECT live repository
        |
        v
INSPECT pinned upstream
        |
        v
MAP responsibilities
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
VERIFY state/provenance/isolation
        |
        v
UPDATE inventory/ADR/runbook
        |
        v
CHECK anti-patterns
        |
        v
CHECK phase exit gate
        |
        v
CONTINUE
```

Do not use:

```text
assume
    ->
invent
    ->
rewrite
    ->
continue
```

---

# 39. FINAL IMPLEMENTATION PRINCIPLE

The implementation succeeds when the architecture becomes:

```text
NeosisLM
    owns:
        API
        workspace
        policy
        ResearchRun
        ResearchTask
        evidence
        provenance
        report artifacts
        memory promotion
        graph promotion
        usage
        observability
        isolation

Open Deep Research
    owns:
        primary deep-research execution

STORM
    owns:
        selected perspective/question/outline capabilities

GPT Researcher
    owns:
        selected retriever/crawling capabilities

Providers / MCP
    own:
        external retrieval/tool execution
```

The implementation fails architecturally when the repository instead becomes:

```text
Neosis custom research engine
    +
copied Open Deep Research
    +
copied STORM
    +
copied GPT Researcher
```

The goal is composition, not duplication.

---

# 40. FINAL INSTRUCTION

Treat this document and the Chapter 3 Architecture & Migration Strategy as a pair.

The architecture document answers:

```text
what the final system is
```

This document answers:

```text
how to reach it in four large controlled phases
```

The later phase-rulebook may expand each phase into:

```text
subphases
implementation tickets
exact file edits
commands
test commands
acceptance cases
```

but it must not change the architectural ownership rules, canonical-state rules, upstream delegation rules, provenance rules, or four-phase migration sequence defined here.

When implementation choices conflict with convenience:

```text
choose the architecture
```

When repository details conflict with old documentation:

```text
inspect the live repository and update the implementation inventory
```

When upstream behavior exists:

```text
reuse it through the integration boundary
```

When evidence is incomplete:

```text
mark it incomplete
```

When a migration step is not tested:

```text
it is not complete
```
