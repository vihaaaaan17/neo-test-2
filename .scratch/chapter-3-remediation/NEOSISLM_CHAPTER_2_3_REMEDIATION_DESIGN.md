# NeosisLM — Chapter 2/3 Remediation & Production Hardening Design
## Senior Engineering Audit and Implementation Plan

**Repository audited:** `vihaaaaan17/neo-test-2`  
**Primary implementation surface:** `app/`  
**Audit date:** 2026-09-21  
**Scope:** Chapter 3 Research Engine Integration + Chapter 2 Ground/Open Notebook integration, with a dedicated scalability track for ~1,000 concurrent users.

---

# 1. Executive Decision

Chapter 3 should **not** be treated as complete.

The current implementation contains a real ODR integration and a reasonably good architectural skeleton, but it has not reached the architecture's own completion criteria. Several claims in the progress/handoff documents are stronger than the implementation supports.

The most important correction is conceptual:

> Do not add isolated fixes on top of the current implementation. Restore the canonical execution lifecycle first, then repair evidence/provenance, tool integration, resource governance, event durability, and scalability.

There are three classes of work:

1. **Correctness blockers** — the system can currently fail or corrupt the intended lifecycle.
2. **Architectural drift** — implemented behavior no longer matches the Chapter 3 contract.
3. **Capacity/operational gaps** — the design has no defensible path to 1,000-user production load.

Chapter 2 also requires a separate scalability hardening pass. The existing Open Notebook integration has useful transport-level protections, but it is still fundamentally a synchronous dependency path from FastAPI to an external research service and needs explicit concurrency, timeout, connection-pooling, backpressure, and degradation policies.

---

# 2. Source-of-Truth Hierarchy

When implementing this document, use this order of authority:

1. Chapter 3 architecture document.
2. Chapter 3 four-phase implementation plan.
3. Actual repository implementation in `app/`.
4. Tests and migrations.
5. Existing progress reports and handoff documents.

The progress report and handoff are **status claims**, not architectural authority. Where they disagree with the code, the code wins for audit purposes and the architecture/plan wins for intended behavior.

The uploaded progress report currently declares Chapter 3 "100% complete", but the same repository state contains missing capabilities and broken lifecycle behavior. Treat that completion claim as invalid until the acceptance gates in this document pass.

---

# 3. What Was Done Correctly

The implementation is not a rewrite candidate. The core direction is correct.

The following pieces should be preserved:

- `ResearchEngine` abstraction.
- `ResearchEngineFactory` as the central execution boundary.
- `LegacyResearchEngine` adapter.
- PostgreSQL canonical Research Fabric.
- `ResearchRun`, `ResearchTask`, `ResearchEvidence`, `ResearchArtifact`, `ResearchReport`, `ResearchUsage`, and `ResearchEvent`.
- Repository-level workspace validation.
- Lifecycle service as the owner of state transitions.
- ODR behind a Neosis anti-corruption layer.
- Evidence interception at the retriever/tool boundary.
- Cooperative cancellation.
- Usage tracking infrastructure.
- Budget enforcement infrastructure.
- Retry-context concept.
- Explicit memory/graph promotion boundaries.
- Structured logging.
- Frozen benchmark corpus concept.
- Legacy preservation for rollback.

These are the correct foundations.

Do not replace them with a second orchestration architecture.

---

# 4. Where the Implementation Drifted from the Original Chapter 3 Plan

## 4.1 STORM

The original plan explicitly positioned STORM as a capability-scoped research component for perspective/question enrichment and/or outline support.

Current implementation:

- No STORM integration in `app/`.
- No adapter.
- No capability registration.
- No factory support.
- No runtime policy.
- No tests.

This is a direct implementation gap, not merely documentation drift.

### Required correction

Do **not** make STORM another autonomous research supervisor.

Implement only the selected STORM capability from the original design, behind a capability interface such as:

```text
ResearchStrategyCapability
    └── StormPerspectiveCapability
```

The capability may produce:

- research perspectives,
- question decomposition,
- outline candidates,
- coverage suggestions.

It must not independently own:

- ResearchRun,
- ResearchTask lifecycle,
- evidence persistence,
- final synthesis,
- memory promotion,
- graph promotion.

Neosis remains the control plane and ODR remains the primary execution runtime.

---

# 5. GPT Researcher Drift

Current `GPTResearcherTool` is a raw LangChain tool which creates `GPTResearcher`, conducts research, writes a report, and returns the report string.

That is insufficient for Neosis.

It bypasses:

- canonical evidence persistence,
- Neosis provenance,
- usage accounting,
- workspace authorization,
- cancellation,
- retry semantics,
- event normalization,
- outer budgets.

It therefore violates the core "Neosis owns the product boundary" rule.

### Required design

GPT Researcher must become a **capability provider**, not a black-box report generator.

Target:

```text
ODR
 │
 ├── web_search
 ├── academic_search
 ├── mcp_query
 ├── storm_capability
 └── gpt_researcher_capability
          │
          └── Retriever / crawler capability
```

The GPT Researcher integration must return structured retrieval results, not an opaque final report.

Minimum normalized contract:

```python
@dataclass
class ResearchSourceResult:
    url: str
    title: str | None
    content: str
    query: str
    retriever: str
    metadata: dict
    provenance: dict
```

The Neosis adapter then performs:

```text
external result
    -> normalize
    -> fingerprint
    -> workspace/run validation
    -> ResearchEvidence persistence
    -> usage accounting
    -> event emission
    -> tool result returned to ODR
```

Do not allow GPT Researcher to write directly to PostgreSQL, Neo4j, MemoryRouter, or `ResearchReport`.

---

# 6. Critical Bug: ResearchRun Is Not Created by the API

This is deeper than the reported `owner_id` bug.

The API endpoint currently enqueues:

```text
workspace_id
objective
job_id
```

but does not create a `ResearchRun`.

The worker then contains fallback logic:

```text
run_id supplied?
    yes -> use it
    no  -> generate UUID
```

That violates the canonical lifecycle.

The intended lifecycle is:

```text
POST /research
    |
    v
authorize workspace
    |
    v
resolve engine policy
    |
    v
create ResearchRun(status=pending)
    |
    v
create/enqueue job(run_id)
    |
    v
worker loads existing ResearchRun
    |
    v
transition pending -> planning
    |
    v
execute
```

There must be no runtime-generated "anonymous" ResearchRun.

### Required correction

`POST /workspaces/{workspace_id}/research` must:

1. Verify workspace access.
2. Resolve the selected engine/policy.
3. Create the canonical `ResearchRun`.
4. Persist `owner_id`.
5. Persist `engine`.
6. Persist `engine_revision`.
7. Commit.
8. Enqueue `run_research_agent_job(run_id=...)`.
9. Return `run_id` and job identifier.

The worker must reject jobs without a valid `run_id`.

Remove fallback UUID generation entirely.

---

# 7. Critical Bug: `owner_id` Undefined

`run_research_agent_job` references `owner_id` even though the function signature does not define it.

This is a deterministic runtime failure at the promotion phase.

### Required correction

Do not simply add an `owner_id` argument to the worker and move on.

The canonical `ResearchRun` already owns `owner_id`.

The worker should:

```text
load ResearchRun by (workspace_id, run_id)
read owner_id from ResearchRun
use that owner_id for promotion
```

This prevents duplicated identity inputs from becoming inconsistent.

---

# 8. Critical Bug: `or True`

Any construct equivalent to:

```python
if is_token_limit_exceeded(...) or True:
```

must be removed immediately.

This destroys error classification.

Research errors need to distinguish at least:

```text
budget exceeded
rate limited
provider timeout
provider unavailable
retriever failure
MCP failure
cancellation
invalid upstream state
programming error
unknown fatal error
```

### Required behavior

Create explicit exception classes and an error policy:

```text
Transient provider failure
    -> retry within bounded attempt policy

Rate limit
    -> retry with bounded backoff

Budget exceeded
    -> PARTIAL

Cancellation
    -> CANCELLED

Expected retriever failure
    -> record event + continue only if policy allows

Fatal programming/state error
    -> FAILED

Unknown error
    -> FAILED + full diagnostic event
```

Never convert arbitrary exceptions into successful-looking partial research.

---

# 9. Research Engine Factory Has an Unsafe Fallback

The current factory catches `ImportError` for ODR and falls back to legacy.

This violates the Chapter 3 rule against hidden fallback behavior.

A missing ODR dependency is an operational configuration failure.

It should not silently change the research engine.

### Required correction

Change:

```text
ODR unavailable -> legacy
```

to:

```text
ODR unavailable -> explicit ResearchEngineUnavailable error
```

The legacy path must only be selected by:

- explicit operator configuration,
- explicit workspace policy,
- controlled rollback.

No implicit compatibility fallback.

---

# 10. Research Lifecycle Is Not Single-Writer Correct

The adapter currently performs terminal state transitions, while the worker also unconditionally transitions the run to `completed`.

This creates a race:

```text
ODR adapter:
    budget exceeded -> PARTIAL

worker:
    engine stream ended -> COMPLETED
```

The worker must not blindly finalize the run as completed.

### Required invariant

Only one lifecycle owner performs terminal transition decisions.

Recommended ownership:

```text
ResearchLifecycleService = sole authority
ResearchEngine = reports execution outcome
Worker = coordinates execution and calls lifecycle service
```

The engine should return an explicit outcome:

```python
ResearchExecutionResult(
    terminal_status=PARTIAL,
    report_id=...,
    usage=...,
    reason=...
)
```

The worker then asks the lifecycle service to finalize based on the result.

No component may infer `COMPLETED` merely because an async generator ended.

---

# 11. Event Durability Is Incomplete

Redis streaming events are useful for UI delivery but are not durable.

The architecture requires canonical event history.

Current implementation persists lifecycle transitions, but intermediate execution events are primarily published to Redis.

### Required target

Every meaningful canonical event should have two paths:

```text
ODR event
   |
   +--> PostgreSQL ResearchEvent  (durable)
   |
   +--> Redis Pub/Sub             (live UI)
```

Redis is transport.

PostgreSQL is audit history.

Do not depend on Redis to reconstruct research execution.

Use an event envelope:

```python
ResearchEventEnvelope(
    run_id,
    task_id,
    event_id,
    sequence,
    event_type,
    occurred_at,
    payload,
    engine,
    engine_revision,
)
```

`sequence` should be monotonically increasing per run.

---

# 12. Redis Pub/Sub Must Not Be the Durability Layer

The current approach is acceptable for transient UI progress, but not for replay/recovery.

Redis Pub/Sub has at-most-once delivery semantics; disconnected subscribers can miss messages. Redis Streams are the appropriate option where replay/delivery guarantees become necessary. citeturn865419search1turn865419search7

Recommended design:

```text
Postgres ResearchEvent
        |
        +---- live publisher ---> Redis Pub/Sub
        |
        +---- optional replay ----> API reads Postgres
```

Do not solve this by storing giant event payloads in Redis.

Keep event payloads compact.

---

# 13. Usage Accounting Is Not Yet Complete

Current `ResearchUsage` schema contains:

- model calls,
- tokens,
- retrieval calls,
- search calls,
- MCP calls,
- latency,
- cost.

But several fields are not actually wired.

This means the schema claims more observability than the runtime provides.

### Required correction

Build a single `ResearchUsageTracker` interface used by every capability:

```text
LLM callback
Search retriever
Academic retriever
MCP tool
GPT Researcher capability
STORM capability
Summarization
Crawling
Embedding, if used
```

Every external operation must have:

```text
started
completed
failed
duration
provider
model/tool
request units
tokens, when available
estimated cost
```

The tracker should use one in-memory accumulator and periodic durable checkpoints.

Do not create a new `ResearchUsage` database row for every tiny operation.

Preferred model:

```text
operation counters
     |
     v
in-memory run accumulator
     |
     +--> periodic checkpoint
     |
     +--> final aggregate
```

---

# 14. Search Behavior Drift

The original ODR search path summarizes raw webpage content using an LLM.

The Neosis replacement currently returns substantially less processed content.

This is not automatically wrong, but it is a behavioral change and was not validated against the benchmark.

Two options exist:

### Preferred

Implement normalization that preserves ODR's intended semantic contract without blindly reproducing its internal implementation.

For example:

```text
Tavily raw result
    -> evidence persistence
    -> optional Neosis-controlled summarization
    -> normalized tool result
```

All summarization calls must be counted in `ResearchUsage`.

### Do not do

Do not re-enable the original ODR implementation merely to make outputs look similar.

Do not allow a hidden second LLM gateway that bypasses Neosis budgets.

---

# 15. Dead Upstream Code

The original `tavily_search` implementation remains in upstream `utils.py` while Neosis replaces it.

This creates maintenance ambiguity.

### Required correction

Keep upstream source changes minimal and explicit.

If the original function is no longer part of the runtime:

- either remove the dead function from the maintained integration fork,
- or document clearly that it is intentionally retained upstream-only and cannot be called.

Also add a regression test proving the active search tool is the Neosis-aware adapter.

---

# 16. RetrieverRegistry Is Missing

The Chapter 3 plan explicitly called for centralized retriever policy.

Current implementation effectively hardcodes Tavily through `neosis_web_search`.

This prevents clean support for:

- web,
- academic,
- MCP,
- future providers,
- policy-driven routing,
- provider health,
- provider quotas.

### Required design

Introduce:

```text
RetrieverRegistry
    |
    +-- WebRetriever
    +-- AcademicRetriever
    +-- MCPRetriever
    +-- GPTResearcherRetriever
```

Each retriever implements a common capability contract.

The registry selects providers through a `ResearchRetrievalPolicy`.

Example:

```python
ResearchRetrievalPolicy(
    allow_web=True,
    allow_academic=True,
    allow_mcp=False,
    preferred_web_provider="tavily",
    fallback_web_provider=None,
    max_calls=...
)
```

Routing decisions belong here, not inside API routes or ODR-specific code.

---

# 17. Academic Retrieval Is Missing

The plan explicitly requires an academic path.

Current `app/` implementation does not provide a canonical first-class academic retriever.

Required initial scope can remain deliberately small:

```text
AcademicRetriever
    ├── arXiv
    └── PubMed / PubMed Central
```

The exact providers must be chosen based on the pinned upstream capabilities and actual licensing/availability.

Every academic result must enter the same evidence normalization path as web results.

---

# 18. MCP Research Is Not Yet a Canonical Neosis Capability

The upstream ODR code contains MCP machinery, but that is not equivalent to "Neosis MCP research integration is complete."

Required:

```text
MCP policy
    |
    +-- allowed server
    +-- allowed tools
    +-- auth context
    +-- call budget
    +-- workspace boundary
    +-- audit record
    +-- cancellation
```

A research result must not be able to grant itself additional MCP permissions.

MCP secrets must never be exposed in prompts, evidence, reports, or ordinary logs.

---

# 19. Provenance Is Too Weak

Current evidence persistence frequently stores:

```text
source_id = None
```

This means the canonical chain is incomplete.

The architecture permits unresolved external sources, but they must be explicitly marked unresolved.

### Required provenance model

Every evidence record should retain at least:

```text
run_id
task_id
retriever
query
locator
title
fingerprint
provider
retrieved_at
source_resolution_status
canonical_source_id nullable
raw_provider_reference
```

Where source resolution fails:

```text
source_resolution_status = "unresolved_external"
```

not simply null-without-explanation.

---

# 20. Claim-Level Citation Integrity Is Missing

A report table with citations is not equivalent to claim-level provenance.

The target chain is:

```text
Report
  -> Claim
      -> Evidence
          -> Source
              -> Task
                  -> Run
                      -> Workspace
```

The current `ResearchReport.citations` JSON is too weak to serve as the canonical provenance layer.

### Required design

Do not necessarily add a fully relational Claim table immediately.

For the first hardening pass, introduce a normalized report provenance structure:

```json
{
  "claims": [
    {
      "claim_id": "...",
      "text": "...",
      "evidence_ids": ["..."],
      "citations": ["..."],
      "provenance_status": "verified"
    }
  ]
}
```

Then deterministic validation can assert:

```text
every citation
-> real Evidence
-> same run
-> same workspace
-> valid locator/source mapping
```

---

# 21. Memory Promotion Is Too Broad

The current adapter creates a `memory_candidate` containing the whole final report.

That is not equivalent to carefully selecting reusable memory.

Research output should not automatically become long-term knowledge.

Required pipeline:

```text
ResearchReport
    |
    v
ResearchArtifact(memory_candidate)
    |
    v
promotion policy
    |
    +--> accepted
    +--> rejected
    +--> deferred
```

Promotion should be explicit and independently authorized.

Do not automatically promote all partial reports.

Do not automatically promote every report paragraph.

---

# 22. Graph Promotion Must Stay Independent

Memory promotion and graph promotion are separate concerns.

Keep:

```text
memory promotion != graph promotion
```

A failed graph projection must not invalidate memory.

A memory quota failure must not invalidate the research report.

Promotion must be idempotent.

---

# 23. The Current Worker Is Becoming Too Thick

`run_research_agent_job` currently performs:

- workspace lookup,
- engine resolution,
- engine execution,
- event publication,
- lifecycle transition,
- report completion logic,
- memory promotion,
- graph promotion,
- Redis behavior,
- metrics,
- error handling.

This is precisely the kind of worker drift the original architecture warned against.

### Target

Worker should be an execution shell:

```text
worker
  |
  +--> load Run
  +--> call ResearchService.execute_run()
  +--> publish live events
  +--> return
```

Business policy belongs in services.

---

# 24. Scalability: Current System Is Not Ready for 1,000 Users

The current implementation is not merely "unoptimized". It has several structural capacity problems.

## 24.1 MemorySaver is not a production checkpoint store

`OpenDeepResearchEngine` compiles the LangGraph with `MemorySaver`.

That creates per-process in-memory state.

Problems:

- process-local state,
- restart loss,
- inconsistent state across workers,
- memory growth,
- poor horizontal scaling.

LangGraph explicitly positions Postgres checkpointers as the production option and in-memory checkpointers for experimentation. citeturn865419search3turn865419search5

### Required migration

Use `AsyncPostgresSaver`.

Important implementation requirement:

- initialize/setup checkpoint tables during deployment/bootstrap,
- reuse connection infrastructure appropriately,
- do not create a fresh database connection per event,
- preserve `thread_id = run_id`.

`AsyncPostgresSaver` provides asynchronous Postgres-backed checkpoint persistence and supports production asynchronous graph execution. citeturn865419search0turn865419search8

Do not add another canonical state store. LangGraph checkpoints remain execution state; PostgreSQL ResearchRun/Evidence/etc. remain product state.

---

# 25. Worker Concurrency Is Currently Unbounded

The current `WorkerSettings` does not set `max_jobs`.

ARQ exposes `max_jobs` specifically as the maximum number of jobs a worker runs simultaneously. citeturn865419search6turn865419search13

Do not interpret ODR's:

```text
max_concurrent_research_units = 3
```

as a global concurrency limit.

That only limits fan-out inside one research run.

Required model:

```text
Global research concurrency
    <= worker pool capacity

Per workspace concurrency
    <= workspace quota

Per user concurrency
    <= user quota

Per run fan-out
    <= ODR research-unit limit
```

---

# 26. Research Must Have Queue Backpressure

For 1,000 users, requests should not directly translate into 1,000 active LLM-heavy executions.

Target:

```text
HTTP request
   |
   v
create ResearchRun
   |
   v
admission controller
   |
   +--> ACCEPTED -> queue
   |
   +--> RATE_LIMITED
   |
   +--> QUOTA_EXCEEDED
   |
   +--> QUEUED
```

The system should distinguish:

```text
queued
running
completed
partial
failed
cancelled
rejected
```

Do not use the API worker as the research concurrency governor.

---

# 27. Add Research-Specific Quotas

Existing `QuotaService` covers workspace resources but not research concurrency.

Add research quotas:

```text
per user:
    max active research runs

per workspace:
    max active research runs

global:
    max active research runs

per run:
    max LLM calls
    max search calls
    max academic calls
    max MCP calls
    max wall-clock time
    max estimated cost
```

Potential initial policy for a free tier:

```text
1 active research run / user
2 active research runs / workspace
N global concurrent runs per worker pool
```

The exact values should be configuration, not hardcoded.

---

# 28. Separate Worker Pools by Workload

A single ARQ queue is likely to become a noisy-neighbor bottleneck.

Use logical queues:

```text
research-high
research-standard
ground-projection
source-processing
maintenance
```

At minimum, isolate research execution from ingestion/projection tasks.

A research runaway must not starve:

- uploads,
- parsing,
- Open Notebook projections,
- graph sync,
- deletion cleanup.

---

# 29. Prevent Nested Concurrency Explosion

One research request can already fan out internally.

Approximate concurrency is:

```text
active_runs
× research_units_per_run
× tool_parallelism
× provider_parallelism
```

Example:

```text
50 active runs
× 3 research units
× 3 tool calls
× multiple Tavily requests
```

can create hundreds of external requests.

Therefore there must be a global semaphore/resource budget around external provider calls.

Use bounded concurrency at:

```text
worker level
retriever level
provider level
```

Do not rely on `asyncio.gather()` without an explicit semaphore.

---

# 30. Provider Rate Limiting

Tavily/OpenAI/MCP/academic providers need provider-scoped admission.

Add a `ProviderRateLimiter` abstraction:

```text
ProviderRateLimiter
    |
    +-- openai
    +-- tavily
    +-- academic-provider
    +-- mcp-server
```

The limiter should be distributed.

Do not use only an in-process `asyncio.Semaphore`, because horizontal workers would each bypass it.

Redis-backed token bucket/sliding-window limiting is the appropriate direction.

---

# 31. PostgreSQL Must Be Treated as a Bottleneck

Research execution currently creates many small DB transactions.

Examples:

- evidence insert per result,
- event insert per transition,
- usage checkpoint writes,
- report insert,
- artifact insert.

At scale this becomes write-heavy.

### Required improvements

Evidence:

- use batched inserts where possible,
- deduplicate by fingerprint,
- avoid committing every single result.

Events:

- append in batches,
- use short transactions.

Usage:

- periodic aggregate checkpoint,
- not per-token writes.

Reads:

- index all `run_id`, `workspace_id`, and event sequencing access paths.

Connection pool:

- size deliberately based on deployment capacity,
- never equal to user count.

---

# 32. Evidence Storage Can Become the Largest Database Table

Deep research may produce many large evidence blobs.

Do not assume PostgreSQL is the correct long-term storage location for unlimited raw content.

Recommended separation:

```text
Postgres:
    metadata
    provenance
    fingerprint
    locator
    compact normalized content

S3:
    large raw evidence
    raw crawled pages
    large provider payloads
```

The canonical object remains referenced from PostgreSQL.

Do not put arbitrary giant raw documents into JSONB.

---

# 33. Neo4j Must Remain a Projection

Do not turn Neo4j into the write path for every research event.

Research should write canonical product state to PostgreSQL first.

Graph projection can be asynchronous:

```text
Postgres
   |
   v
graph projection job
   |
   v
Neo4j
```

This also makes graph downtime non-fatal to research execution.

---

# 34. Chapter 2 Scalability Audit

The existing Open Notebook integration has useful transport protections:

- HTTP connection reuse when `request.app.state.http_client` exists.
- timeout handling.
- circuit breaker.
- workspace/request/run correlation headers.
- explicit upstream error mapping.

These should remain.

However, Chapter 2 currently lacks a full capacity model.

## Required Chapter 2 hardening

### A. Do not instantiate new `httpx.AsyncClient` objects for every call

The client already supports a shared app-state client. Standardize on that path.

All high-volume Open Notebook calls must use a shared connection pool.

### B. Add dependency concurrency limits

Create:

```text
OpenNotebookConcurrencyController
```

with separate limits for:

- ingestion,
- search,
- ask,
- chat,
- streaming.

### C. Circuit breaker must be multi-instance aware

The current breaker is process-local.

With multiple API replicas:

```text
pod A thinks dependency is healthy
pod B thinks dependency is down
```

Use local circuit breaking for fast protection, but pair it with deployment-level health/metrics. A distributed breaker is optional; distributed rate limiting is more important.

### D. Protect streaming connections

1,000 users could create 1,000 long-lived HTTP connections.

Measure:

- active streams,
- average stream lifetime,
- upstream connections,
- server file descriptors,
- proxy idle timeout.

Add per-user/workspace stream limits.

### E. Open Notebook must not block API capacity

Prefer:

```text
FastAPI
   |
   v
bounded upstream connection pool
```

and reject/defer when Open Notebook is saturated.

Do not allow 1,000 requests to block indefinitely waiting for external capacity.

---

# 35. Chapter 2 Source Projection Backpressure

`project_to_open_notebook_job` is asynchronous, which is good.

However, it must be isolated from research execution.

Use:

```text
source ingestion queue
        |
        v
Open Notebook projection workers
```

with:

- bounded concurrency,
- retry/backoff,
- idempotent claim,
- dead-letter handling,
- provider health metrics.

A slow Open Notebook must not prevent Research Mode from running.

---

# 36. Connection Pooling and Database Capacity

For a ~1,000-user system, capacity planning must be based on active concurrency, not account count.

Define explicitly:

```text
users
workspaces
API replicas
research workers
max active research runs
DB pool per replica
Redis pool
Neo4j pool
Open Notebook connection pool
LLM concurrency
retriever concurrency
```

The target is not "1,000 simultaneous deep research runs".

The target is:

> 1,000 registered/active users with controlled concurrent workloads and predictable queueing.

---

# 37. Recommended Production Envelope

Do not hardcode these numbers without load testing. Establish them empirically.

A sensible initial architecture:

```text
1000 registered users
   |
   +-- bounded API replicas
   |
   +-- research admission control
   |
   +-- dedicated research worker pool
   |
   +-- bounded LLM concurrency
   |
   +-- bounded retriever concurrency
   |
   +-- Postgres checkpointing
   |
   +-- Redis queue/pubsub
   |
   +-- S3 raw artifacts
   |
   +-- async Neo4j projection
```

The system must degrade through queueing and rejection, not by starting unlimited work.

---

# 38. Benchmarking Is Currently Too Optimistic

The benchmark documentation states that execution is heavily mocked.

That makes the current numbers unsuitable as proof of production latency/cost.

A mocked P95 of ~1.45 seconds and a 3-second production ceiling do not establish that real ODR research satisfies a 3-second SLA.

### Required benchmark layers

## Layer A — deterministic unit benchmark

Mocks:

- LLM,
- search,
- database.

Goal:

- state-machine correctness,
- adapter correctness,
- event normalization.

## Layer B — integration benchmark

Real:

- PostgreSQL,
- Redis,
- checkpointer,
- retriever adapters.

Mock or limited external LLM/search.

Goal:

- system overhead,
- DB pressure,
- checkpoint behavior.

## Layer C — provider benchmark

Real:

- representative LLM,
- real web search,
- real academic provider where enabled.

Goal:

- real latency,
- real cost,
- real provider failure behavior.

## Layer D — load benchmark

Simulate:

```text
10 users
50 users
100 users
250 users
500 users
1000 users
```

Track:

- queue wait time,
- execution time,
- P50/P95/P99,
- DB connections,
- Redis memory,
- CPU,
- RAM,
- provider rate-limit rate,
- error rate,
- partial rate,
- evidence count/run,
- cost/run.

---

# 39. Production Ceilings Need Reinterpretation

The current documented:

```text
cost < $0.10
P95 < 3s
quality > 9
```

should not be treated as absolute production truth until measured with real external dependencies.

The $0.10 cost target may be unrealistic for genuine deep research depending on provider/model/tool usage.

The 3-second P95 is especially unsuitable as a deep-research end-user completion SLA unless the product explicitly promises extremely short research.

Instead define:

```text
API acceptance latency
queue admission latency
queue wait P95
research execution P95
time-to-first-event
time-to-first-evidence
time-to-final-report
```

For long research tasks, the user-facing SLA should focus on progress and bounded completion rather than pretending the whole task is synchronous.

---

# 40. New Reliability Model

Use a two-level reliability model.

## Control-plane reliability

Must be high:

- run creation,
- state persistence,
- queue admission,
- cancellation,
- authorization,
- usage,
- provenance.

## Research-plane reliability

Can degrade partially:

- provider outage,
- one retriever unavailable,
- academic provider failure,
- MCP failure,
- one research unit failure.

The system should preserve useful evidence and produce a truthful partial result when policy permits.

---

# 41. Retry Design

Current retry-context injection is a reasonable starting point, but retry semantics should become explicit.

Use:

```text
ResearchRun
  |
  +-- attempt 1
  +-- attempt 2
  +-- attempt 3
```

Do not overwrite attempt history.

Add a `research_attempt_id` or equivalent attempt record.

Each attempt should retain:

- start/end,
- engine revision,
- provider configuration,
- error,
- usage,
- evidence contribution,
- status.

Canonical `run_id` remains the product identity.

---

# 42. Do Not Retry Everything

Safe retry examples:

- transient HTTP 5xx,
- connection reset,
- bounded provider rate-limit response,
- temporary MCP availability failure.

Do not automatically retry:

- authorization errors,
- invalid input,
- budget exhaustion,
- workspace violations,
- deterministic schema failures,
- programming errors.

---

# 43. Cancellation Must Propagate Through Every Layer

Cancellation currently exists at the ODR task level.

Extend the contract to:

```text
ResearchService
  -> Engine
     -> Retriever
        -> provider request
```

A cancellation should stop:

- pending retries,
- search requests where supported,
- MCP requests,
- report synthesis,
- queued follow-up work.

The final canonical state must be exactly one of:

```text
CANCELLED
PARTIAL
COMPLETED
FAILED
```

and must never be overwritten afterward by generic worker cleanup.

---

# 44. Run Idempotency

Every research request needs a deterministic deduplication model.

Recommended:

```text
request_id
run_id
attempt_id
job_id
```

with distinct semantics.

```text
request_id = client/API request identity
run_id = product-level research identity
attempt_id = execution attempt
job_id = ARQ infrastructure identity
```

Never use `job_id` as the business identity.

---

# 45. Feature Flags

`ACTIVE_RESEARCH_ENGINE` is useful for global rollback.

It should not be the only policy layer.

Target:

```text
Global default
      |
      v
Workspace policy
      |
      v
Research capability policy
      |
      v
EngineFactory
```

Do not put engine-selection logic inside:

- API routes,
- retrievers,
- UI,
- ODR upstream code.

---

# 46. Configuration Must Be Fail-Closed

Production configuration should reject invalid combinations.

Examples:

```text
ODR selected but dependency unavailable -> startup/health failure
Academic enabled without provider config -> capability unavailable
MCP enabled without policy -> disabled
Research queue unavailable -> admission rejection
DB checkpoint unavailable -> research not started
```

Do not silently switch to another engine.

---

# 47. Observability Required

Structured logs are necessary but insufficient as the complete observability model.

Minimum metrics:

```text
research_runs_started
research_runs_queued
research_runs_completed
research_runs_partial
research_runs_failed
research_runs_cancelled

research_queue_wait_ms
research_duration_ms
research_time_to_first_event_ms
research_time_to_first_evidence_ms

research_cost
research_input_tokens
research_output_tokens

research_search_calls
research_academic_calls
research_mcp_calls
research_retriever_failures

research_evidence_per_run
research_citation_coverage
research_unresolved_provenance

research_active_runs
research_active_tasks

provider_rate_limited
provider_timeout
provider_error

postgres_pool_wait
redis_latency
neo4j_projection_lag
open_notebook_active_requests
```

Use the existing structured logging path as the first source.

Add a metrics backend when production deployment has one, but do not block architectural correctness on a vendor-specific SDK.

---

# 48. Alerts

At minimum:

```text
Research failure rate > threshold
Research partial rate > threshold
Provider rate-limit spikes
P95 queue wait too high
P95 research duration too high
DB pool exhaustion
Redis memory/latency anomaly
Checkpoint failure
Evidence persistence failure
Open Notebook dependency error spike
Graph projection lag
```

---

# 49. Security / Tenant Isolation

The repository's `_verify_run_workspace` pattern is useful.

Strengthen it with:

1. Every public research endpoint verifies current-user access to workspace.
2. Every run is bound to exactly one workspace.
3. Every evidence query is scoped through run + workspace.
4. Promotion APIs require workspace ownership.
5. Graph projection always carries workspace ID.
6. Background jobs load identity from canonical records where possible.
7. Never trust `workspace_id`, `owner_id`, or `run_id` supplied independently when a canonical record exists.

The last rule is especially important for the current worker.

---

# 50. Data Model Improvements

Recommended additions:

```text
ResearchAttempt
ResearchEvent.sequence
ResearchEvidence.source_resolution_status
ResearchEvidence.provider
ResearchEvidence.provider_reference
ResearchReport.provenance_version
ResearchReport.status
ResearchRun.request_id
ResearchRun.current_attempt_id
ResearchRun.queue_entered_at
ResearchRun.started_at
ResearchRun.completed_at
```

Potentially later:

```text
ResearchClaim
ResearchCitation
```

Do not introduce the complete relational claim model until the simpler provenance representation is proven insufficient.

---

# 51. Proposed Target Architecture

```text
                         ┌─────────────────────┐
                         │      FastAPI API     │
                         └──────────┬──────────┘
                                    │
                         authorize + create Run
                                    │
                                    v
                         ┌─────────────────────┐
                         │ Research Admission  │
                         │ quotas / rate limit │
                         └──────────┬──────────┘
                                    │
                         enqueue canonical run
                                    │
                                    v
                         ┌─────────────────────┐
                         │ Redis / ARQ Queue   │
                         └──────────┬──────────┘
                                    │
                                    v
                    ┌─────────────────────────────┐
                    │ Dedicated Research Workers  │
                    └─────────────┬───────────────┘
                                  │
                                  v
                       ┌────────────────────┐
                       │  ResearchService   │
                       └─────────┬──────────┘
                                 │
                    ┌────────────┴────────────┐
                    │ Engine Strategy/Factory │
                    └────────────┬────────────┘
                                 │
                         ┌───────┴───────┐
                         │      ODR      │
                         └───────┬───────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          v                      v                      v
      WebRetriever        AcademicRetriever       MCPRetriever
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                                 v
                       Neosis Normalization ACL
                                 │
             ┌───────────────────┼───────────────────┐
             v                   v                   v
       ResearchEvidence   ResearchUsage       ResearchEvent
             │                   │                   │
             └───────────────────┼───────────────────┘
                                 v
                             PostgreSQL
                                 │
             ┌───────────────────┼────────────────────┐
             v                   v                    v
          Reports           Memory candidates    Graph candidates
             │                   │                    │
             v                   v                    v
        API/UI            Promotion Service     Async Projection
                                                      │
                                                      v
                                                    Neo4j
```

---

# 52. Implementation Order

Do not implement everything at once.

## Phase A — Restore lifecycle correctness

1. Create ResearchRun in API.
2. Remove worker-generated run IDs.
3. Load owner from ResearchRun.
4. Fix undefined `owner_id`.
5. Remove `or True`.
6. Remove hidden ODR -> legacy fallback.
7. Make terminal lifecycle single-writer.
8. Add explicit execution result.

Exit gate:

- every research run has a persisted Run before execution;
- no research starts without a canonical Run;
- no terminal state can be overwritten;
- known failures are correctly classified.

---

## Phase B — Repair canonical evidence/provenance

1. Retriever interface.
2. RetrieverRegistry.
3. WebRetriever.
4. AcademicRetriever.
5. MCPRetriever.
6. GPT Researcher capability adapter.
7. evidence normalization.
8. source resolution.
9. provenance status.
10. report claim/citation mapping.
11. deterministic provenance audit.

Exit gate:

Every report citation resolves to evidence in the same run and workspace.

---

## Phase C — Complete upstream capability boundaries

1. Inspect/pin STORM.
2. Implement only approved STORM capability.
3. Implement GPT Researcher as structured capability.
4. Ensure neither becomes an autonomous supervisor.
5. Add capability policy flags.
6. Add capability-specific tests.

Exit gate:

ODR remains primary executor; STORM and GPT Researcher are bounded capabilities.

---

## Phase D — Durable execution and event model

1. Replace MemorySaver with AsyncPostgresSaver.
2. Add checkpoint setup/migrations.
3. Add durable event persistence.
4. Add event sequence numbers.
5. Add Redis live publication.
6. Add replay endpoint from PostgreSQL.
7. Add attempt model.
8. Make retries attempt-aware.

Exit gate:

A worker can restart and research can resume safely without process-local state.

---

## Phase E — Resource Governance

1. Add research admission controller.
2. Add per-user concurrency quota.
3. Add per-workspace concurrency quota.
4. Add global concurrency cap.
5. Add provider rate limiter.
6. Add research-specific budget policy.
7. Add queue status.
8. Separate research worker pool.
9. Add bounded internal provider concurrency.

Exit gate:

100/250/500/1000-user load cannot cause unbounded research fan-out.

---

## Phase F — Usage + Observability

1. Complete all usage counters.
2. Track summarization calls.
3. Track academic/MCP/GPT calls.
4. Track latency by operation.
5. Emit durable events.
6. Emit structured metrics.
7. Add dashboards/alerts.
8. Add runbook with actual failure procedures.

Exit gate:

Every research run is economically and operationally explainable.

---

## Phase G — Benchmark and Production Validation

1. Unit benchmark.
2. Integration benchmark.
3. Real-provider benchmark.
4. 10/50/100/250/500/1000-user load testing.
5. Failure injection.
6. Worker restart testing.
7. Redis restart testing.
8. PostgreSQL failover/connection pressure testing.
9. Open Notebook saturation testing.
10. Rollback testing.

Exit gate:

Only after all quality, reliability, isolation, cost, latency, and scalability gates pass should Chapter 3 be marked complete.

---

# 53. Chapter 2 Remediation Track

Run this in parallel but keep it architecturally separate from Research Mode.

## Ground/Open Notebook

Required work:

```text
1. Shared HTTP client
2. Connection pool sizing
3. Upstream concurrency limits
4. Per-workspace/user concurrency
5. Streaming connection limits
6. Circuit-breaker metrics
7. Timeout classification
8. Backpressure
9. Retry policy
10. Projection queue isolation
11. Open Notebook capacity benchmark
12. 1000-user load test
```

Do not move Open Notebook's internal state into the Neosis Research Fabric.

Do not replace Open Notebook with a custom Ground implementation.

---

# 54. Things the Fix Agent Must NOT Do

Do not:

- create a new custom deep-research supervisor;
- make STORM a competing supervisor;
- make GPT Researcher a second end-to-end engine;
- create a second canonical research database;
- write upstream results directly to Neo4j;
- bypass `ResearchService`;
- bypass `ResearchRepository`;
- bypass `ResearchLifecycleService`;
- put database sessions inside ODR upstream modules;
- make Redis the source of truth;
- use job IDs as research IDs;
- generate fallback run IDs;
- silently fall back from ODR to legacy;
- automatically promote every report into memory;
- automatically promote every research result into graph state;
- use unbounded `asyncio.gather`;
- use process-local semaphores as the only global concurrency control;
- treat mocked benchmark results as production latency evidence;
- delete the legacy engine during this remediation pass.

---

# 55. Testing Matrix

## Correctness

- Run creation.
- State transitions.
- Terminal-state idempotency.
- retry attempts.
- cancellation.
- partial completion.
- failure classification.

## Isolation

- cross-workspace evidence.
- cross-workspace reports.
- cross-workspace artifacts.
- cross-workspace memory promotion.
- cross-workspace graph promotion.
- malicious IDs.
- mismatched owner/run/workspace combinations.

## Provenance

- every citation resolves.
- broken citation rejected.
- cross-run citation rejected.
- cross-workspace citation rejected.
- unresolved external source explicitly tagged.

## Capability

- Web.
- Academic.
- MCP.
- GPT Researcher.
- STORM.
- provider failure.
- provider timeout.

## Scalability

- 10 concurrent runs.
- 50.
- 100.
- 250.
- 500.
- 1000 queued users.
- bounded active runs.
- provider saturation.
- DB pool saturation.
- worker restart.
- Redis restart.
- checkpoint recovery.

---

# 56. Acceptance Criteria

Chapter 3 remediation is complete only when all of the following are true.

### Lifecycle

- [ ] ResearchRun created before enqueue.
- [ ] run_id mandatory.
- [ ] owner_id canonical.
- [ ] attempt identity exists.
- [ ] no terminal-state overwrite.
- [ ] no hidden fallback.

### Engines

- [ ] ODR primary.
- [ ] legacy explicit only.
- [ ] STORM capability integrated or explicitly disabled by documented Phase 1 decision.
- [ ] GPT Researcher capability integrated through Neosis ACL.

### Retrieval

- [ ] RetrieverRegistry exists.
- [ ] WebRetriever exists.
- [ ] AcademicRetriever exists.
- [ ] MCPRetriever exists where enabled.
- [ ] provider policies exist.

### Evidence

- [ ] evidence persisted before synthesis where possible.
- [ ] fingerprints work.
- [ ] unresolved provenance is explicit.
- [ ] report citations map to evidence.
- [ ] deterministic provenance audit passes.

### Usage

- [ ] LLM usage.
- [ ] search usage.
- [ ] retrieval usage.
- [ ] academic usage.
- [ ] MCP usage.
- [ ] GPT Researcher usage.
- [ ] summarization usage.
- [ ] latency.
- [ ] cost.

### Durability

- [ ] AsyncPostgresSaver.
- [ ] durable ResearchEvent.
- [ ] event sequencing.
- [ ] retry attempt persistence.
- [ ] restart recovery.

### Scalability

- [ ] worker max concurrency.
- [ ] per-user quota.
- [ ] per-workspace quota.
- [ ] global research cap.
- [ ] provider rate limits.
- [ ] bounded internal fan-out.
- [ ] dedicated research workers.
- [ ] queue backpressure.
- [ ] load test through 1000-user scenario.

### Chapter 2

- [ ] shared Open Notebook HTTP pool.
- [ ] upstream concurrency limits.
- [ ] stream limits.
- [ ] projection isolation.
- [ ] dependency metrics.
- [ ] 1000-user saturation test.

### Operations

- [ ] dashboards.
- [ ] alerts.
- [ ] runbook.
- [ ] rollback tested.
- [ ] legacy retained for rollback window.

---

# 57. Recommended Ticket Structure for the Agent

The implementation agent should execute these as sequential tickets, not one giant refactor:

```text
R-01  Canonical ResearchRun creation
R-02  Worker lifecycle cleanup
R-03  Error classification / remove hidden fallback
R-04  Terminal state ownership
R-05  RetrieverRegistry
R-06  Web retriever normalization
R-07  Academic retriever
R-08  MCP capability boundary
R-09  GPT Researcher ACL
R-10  STORM capability ACL
R-11  Provenance model strengthening
R-12  Claim/citation mapping
R-13  Durable ResearchEvent persistence
R-14  AsyncPostgresSaver
R-15  Retry attempt model
R-16  Usage accounting completion
R-17  Research admission controller
R-18  Research quotas
R-19  Provider rate limiting
R-20  Research worker pool isolation
R-21  Evidence batching/storage strategy
R-22  Research observability
R-23  Chapter 2 Open Notebook capacity hardening
R-24  Real-provider benchmark
R-25  Load benchmark 10→1000
R-26  Failure injection
R-27  Rollback verification
R-28  Final architecture audit
```

Every ticket must include:

```text
scope
files to inspect
design constraints
implementation
tests
exit criteria
```

No ticket may introduce a new top-level architecture unless the current Chapter 3 architecture document is explicitly revised first.

---

# 58. Agent Workflow Requirement

Before implementation:

```text
read architecture
read implementation plan
read current app/
read tests
read this remediation document
```

Then:

```text
/grill-with-docs
/to-specs        # or installed /to-spec
/to-tickets
```

Implement one ticket group at a time.

After each major phase:

```text
run tests
run benchmark
run graphify
audit changed files
verify architecture invariants
```

Do not let implementation skills turn this remediation into a redesign exercise.

---

# 59. Final Engineering Assessment

The current Chapter 3 work should be described as:

> **A functional ODR integration prototype with a good canonical architecture, but not yet production-complete.**

The strongest parts are the Neosis-owned Research Fabric, adapter boundary, workspace-aware repository, lifecycle service, budget infrastructure, and evidence interception.

The most serious problems are not cosmetic:

1. ResearchRun creation is missing from the API lifecycle.
2. Worker identity handling is inconsistent.
3. Terminal state handling can overwrite partial/failure states.
4. Hidden fallback violates the explicit-engine architecture.
5. GPT Researcher bypasses the canonical product boundary.
6. STORM is absent.
7. Academic/MCP/retriever policy infrastructure is incomplete.
8. Provenance is weaker than the architecture requires.
9. Event durability is incomplete.
10. Usage accounting is incomplete.
11. MemorySaver makes the ODR runtime process-local and unsuitable as the production checkpoint layer.
12. Research concurrency is not globally governed.
13. The benchmark's mocked latency numbers are not a production SLA.
14. Chapter 2 has useful resilience primitives but no verified capacity model.
15. The system has no demonstrated 1,000-user research capacity envelope.

The correct response is **not** to throw away the architecture.

The correct response is to finish the architecture that was already chosen, restore canonical lifecycle ownership, add the missing capability boundaries, replace process-local execution state with durable checkpointing, and introduce explicit admission/backpressure/rate-limit controls before claiming Chapter 3 completion.

