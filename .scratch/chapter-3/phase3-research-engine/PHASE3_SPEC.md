## Problem Statement

NeosisLM currently has a prototype research mode that is tightly coupled to the custom `ResearchModeOrchestrator` execution loop. Phase 2 successfully built the canonical Neosis research fabric (durable State, Evidence, Tagging, and Provenance records), but the current execution loop does not use it. To scale to mature, multi-step deep research without reinventing the wheel, we need to bridge real production research execution (via mature upstream systems like Open Deep Research) directly to the canonical Phase 2 fabric, while retaining Neosis' absolute ownership over state, policy, resources, usage, and product outcomes.

## Solution

We will implement a `ResearchEngineFactory` / strategy resolver that routes execution to a mature upstream adapter (Open Deep Research) or the legacy orchestrator, all running securely in-process within the existing Arq worker (`app/workers/tasks.py`). 

The Open Deep Research (ODR) adapter will act as a thin bridge: translating Neosis requests into ODR configurations, and intercepting ODR's native tool calls to execute distinct Neosis-aware retrievers (`web_search`, `academic_search`, etc.). These interceptors will normalize evidence, apply workspace policies, track budgets, and write canonical `ResearchEvidence` to PostgreSQL *during* execution. Upstream events will be caught and yielded to the outer `ResearchService`, which persists them as canonical `ResearchEvent`s and streams them via Redis.

## User Stories

1. As an API client, I want to initiate a research run with an optional engine selection, so that I can seamlessly execute Open Deep Research or fall back to the legacy engine.
2. As a workspace owner, I want ODR to utilize distinct, specialized tools (web, academic, MCP), so that the research planner makes intelligent source decisions based on the objective.
3. As a researcher, I want my evidence to be normalized and persisted to PostgreSQL incrementally during execution, so that partial progress and provenance are never lost if the upstream engine crashes.
4. As a UI consumer, I want upstream execution events to be normalized into standard Neosis `ResearchEvent`s, so that I can render a unified streaming progress view regardless of the underlying engine.
5. As an admin, I want strict time, token, and cost budgets enforced at the Neosis layer, so that ODR fan-out cannot exhaust my resources.
6. As a user, I want the ability to cooperatively cancel an executing ODR job, so that runaway or mistaken research attempts can be safely stopped, finalizing state as `CANCELLED` and saving any gathered evidence.
7. As a researcher, I want partial research runs to yield whatever evidence was successfully gathered, so that a budget limit or transient error doesn't completely destroy my work.
8. As a system operator, I want retried runs to reuse the same canonical `run_id` and resume with the existing persisted evidence as context, so that recovery is engine-agnostic and efficient.
9. As a finance stakeholder, I want token and API usage accumulated during ODR execution to be periodically checkpointed and finalized into a canonical `ResearchUsage` record, so that operational costs are rigorously tracked.
10. As a workspace administrator, I want memory and graph promotion to be handled by the outer `ResearchService` (not the engine adapter), so that promotion remains a controlled, policy-driven product decision.

## Implementation Decisions

- **Execution Boundary**: `ResearchEngineFactory` and the selected engine (e.g., `OpenDeepResearchEngine`) run as in-process libraries inside the existing Arq worker (`app/workers/tasks.py`).
- **Engine Selection**: Centralized inside `ResearchService`. The API request may optionally specify an engine (falling back to workspace policy), which the Service validates and records in `ResearchRun.engine`.
- **Evidence Interception**: We will expose distinct tools (e.g., `web_search`, `academic_search`, `mcp_query`) to ODR's planner. When ODR invokes these, our Neosis wrapper executes the search, persists canonical `ResearchEvidence` to PostgreSQL, and returns the raw stringified results to ODR.
- **Event Handling**: The ODR adapter does not persist events itself. It yields or emits normalized `ResearchEvent` DTOs back to the outer worker loop, which uses `ResearchLifecycleService` to persist and publish them via Redis.
- **Cancellation**: Relies on cooperative `asyncio.CancelledError` thrown by Arq. The adapter catches this, flushes pending evidence, and allows the run to cleanly finalize as `CANCELLED` or `PARTIAL`.
- **Resource Backpressure**: Budgets (tokens, cost, task concurrency) are enforced globally via the Neosis retriever wrappers and LLM callbacks. Exceeding limits raises `ResearchBudgetExceeded`, cleanly interrupting the engine.
- **Partial State**: There is no new fallback synthesizer. If ODR is interrupted, the gathered canonical evidence is retained, and the run finalizes as `PARTIAL` (saving whatever native report was completed, if any).
- **Retries**: A retry keeps the canonical `run_id`, spins up a fresh ODR instance, and injects the previously persisted `ResearchEvidence` into ODR's context to avoid duplicate work.
- **Usage**: Usage is accumulated in-memory during execution, periodically checkpointed, and fully persisted via a final aggregate `ResearchUsage` record during run finalization.
- **Legacy Compatibility**: The existing `ResearchModeOrchestrator` will be wrapped in a `LegacyResearchEngine` adapter satisfying the unified `ResearchEngine` contract.
- **Knowledge Promotion**: The adapter merely saves `memory_candidate` and `graph_candidate` artifacts. Promotion is triggered strictly by the outer `ResearchService` based on policy when a terminal state is reached.

## Testing Decisions

- Test the `ResearchEngineFactory` logic to ensure correct engine dispatch based on run state.
- Test the distinct Neosis retriever tools to verify they successfully intercept queries, enforce budget limits (mocked), and produce `ResearchEvidence` records.
- Test ODR adapter event normalization by feeding raw ODR events and asserting they produce canonical `ResearchEvent` DTOs.
- Test cooperative cancellation by simulating an `asyncio.CancelledError` and verifying state safely finalizes.
- Conduct an integration test of the full `FastAPI -> ResearchService -> Worker -> ODR Adapter -> Retriever -> Postgres` chain.

## Out of Scope

- Removing the legacy baseline.
- Adding a new fallback/partial synthesizer.
- ODR performance benchmarking and quality evaluations (Phase 4).
- Creating new `OutputGraph` rendering strategies.

## Further Notes

- Strict adherence to Rule 11 (Legacy Compatibility) ensures we have a side-by-side comparative baseline for Phase 4 evaluations.
