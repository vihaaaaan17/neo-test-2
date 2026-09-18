**Status:** ready-for-agent

## Problem Statement

As the system scales and processes larger research objectives, the agents pull in excessive context from various memory systems (Source, Knowledge, Episodic, Working). This leads to prompt pollution, increased LLM costs, and token limit violations. Furthermore, engineers lack a structured way to evaluate the quality of the agent's retrieval and reasoning loops offline without being flooded by noisy operational traces from basic CRUD and background tasks.

## Solution

Phase 5 implements "Evaluation & Reliability." 

First, we will introduce a `MemoryRouterService` that acts as a strict boundary before any LLM prompt is assembled. It takes a token budget and a prioritized eviction policy to ensure the prompt never exceeds limits, preserving essential context (like Working Memory) while dropping less critical historical data if necessary. 

Second, we will implement selective LangSmith tracing. We will instrument the high-level reasoning loops (`GroundModeOrchestrator` and `ResearchModeOrchestrator`) to emit detailed traces for offline evaluation, while explicitly keeping background data pipelines (like Docling ingestion and Neo4j graph projection) out of LangSmith to maintain a high signal-to-noise ratio in our evaluation datasets.

## User Stories

1. As an ML Engineer, I want the system to emit LangSmith traces for `GroundModeOrchestrator` runs, so that I can evaluate groundedness and citation coverage offline.
2. As an ML Engineer, I want the system to emit LangSmith traces for `ResearchModeOrchestrator` runs, so that I can evaluate the autonomous agent's planning and evidence coverage.
3. As an ML Engineer, I want background jobs (e.g., parsing, CRUD operations, graph projection) to be excluded from LangSmith, so that my evaluation datasets are not polluted with noisy operational data.
4. As a system administrator, I want a unified `MemoryRouterService` that aggregates context from all 6 memory systems, so that there is a single chokepoint for prompt assembly.
5. As a system administrator, I want to pass a strict `token_budget` to the `MemoryRouterService`, so that the system never triggers LLM context window limits or blows up costs.
6. As a system administrator, I want the `MemoryRouterService` to strictly follow an eviction hierarchy (drop Episodic -> Knowledge -> Source -> Working), so that the agent retains its immediate train of thought (Working Memory) during high-context situations.
7. As a researcher, I want the system to drop entire memory items rather than truncating sentences, so that the provenance and citations of the retained context remain perfectly intact.

## Implementation Decisions

- **Selective Tracing**: We will conditionally configure LangSmith / LangChain tracing. It will be enabled in the LangGraph configurations of the orchestrators (`GroundModeOrchestrator` and `ResearchModeOrchestrator`). Background task queues (like `arq` workers doing graph projection) will only use standard OpenTelemetry/logging and will explicitly omit the `LANGCHAIN_TRACING_V2` environment variables or callbacks.
- **Unified Memory Router**: We will build a `MemoryRouterService` that consolidates the conceptual "Context Builder" and "Memory Router" from the initial architecture. It will return a typed `ContextBundle` Pydantic model.
- **Eviction Hierarchy**: When assembling the `ContextBundle`, the service will calculate the approximate token count of the items. If it exceeds the budget, it will pop items out entirely. The priority of retention (highest to lowest) is: Working Memory > Source Memory > Knowledge Memory > Episodic Memory.
- **No Truncation**: To preserve strict provenance links, texts will never be chunked or truncated at this stage. An item is either included in the `ContextBundle` in its entirety, or it is evicted entirely.

## Testing Decisions

- **Good Tests**: Tests should verify the external behavior of the router and the presence of traces without hitting live LLM APIs. 
- **Modules Tested**: `MemoryRouterService` and the orchestrators' tracing configurations.
- **Testing Seams**: 
  1. The primary seam for testing eviction is the `MemoryRouterService.build_context()` method. We will inject mock memory objects of known lengths and verify that the output `ContextBundle` strictly obeys the token budget and drops items in the correct hierarchical order.
  2. The seam for testing tracing is intercepting the LangChain callback manager during an orchestrator run to ensure trace IDs are generated, while verifying they are absent in a mocked background job execution.
- **Prior Art**: We will use the existing dependency injection patterns (e.g., `test_ground_mode_api.py`) to mock the memory repositories when testing the router.

## Out of Scope

- Building a full offline evaluation harness or automated regression CI pipeline (this phase just sets up the tracing data for it).
- Dynamically resizing token budgets based on the specific LLM model (we will use a static configuration for now).
- Vectorizing and semantically ranking Working Memory (Working Memory is treated as a chronological scratchpad).

## Further Notes

- The integration of the `MemoryRouterService` will require minor updates to the Phase 3 and Phase 4 orchestrators to route their context fetching through this new service instead of directly querying the repositories.
