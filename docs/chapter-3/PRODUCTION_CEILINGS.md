# Phase 4: Production Ceilings & Evaluation Mechanics

This document details the rigorous evaluation framework, cost/latency ceilings, and empirical benchmarking strategies enforced for the Open Deep Research (ODR) Engine (Chapter 3). It explains how the legacy baseline was established, how the automated benchmark runner measures regressions, and the exact code paths responsible for tracking these metrics.

---

## 1. The Benchmarking Pipeline & Framework

To confidently migrate from the legacy `ResearchModeOrchestrator` to the new LangGraph-based `OpenDeepResearchEngine`, we rely on an automated, reproducible benchmark suite that executes against a frozen corpus.

### Code Components
- **The Corpus:** [`tests/fixtures/benchmark/corpus.jsonl`](file:///d:/koding/codes/NeosisLM/tests/fixtures/benchmark/corpus.jsonl)
  - Contains 20-30 representative and diverse prompts covering required research classes (e.g., broad exploration, focused fact-finding).
- **The Runner:** [`scripts/benchmark_runner.py`](file:///d:/koding/codes/NeosisLM/scripts/benchmark_runner.py)
  - Automates the execution of both engines (`--engine legacy` or `--engine open_deep_research`) against the frozen corpus.
  - Generates JSON metrics including execution duration (`duration_ms`), cost, and quality scores.
- **The Factory Adapter:** [`app/integrations/research_engine/factory.py`](file:///d:/koding/codes/NeosisLM/app/integrations/research_engine/factory.py)
  - Used by the benchmark runner to instantiate the selected engine while mocking the LLM API (`mock_llm_gateway`) and Search Tool (`MockSearchTool`). This ensures the benchmark runs deterministically and rapidly without incurring real API charges.

---

## 2. Legacy Baseline (Mocked Execution)

Before activating ODR, the legacy engine was run against the frozen corpus to establish a "ground truth" performance floor. The results are locked in [`legacy_baseline.json`](file:///d:/koding/codes/NeosisLM/tests/fixtures/benchmark/legacy_baseline.json).

- **Average Cost**: $0.04 per prompt
- **P95 Latency**: ~1.45 seconds (1445ms)
- **Quality Score**: 9.0 (out of 9)

*Note: Since execution is heavily mocked to isolate framework overhead, these numbers reflect graph execution latency and token counting loops rather than real-world API wait times.*

---

## 3. Production Ceilings

To ensure that the Phase 3 ODR implementation does not regress on cost or latency while significantly improving quality, the following hard limits are enforced for production cutover. If any of these ceilings are breached, the PR cannot be merged.

### 3.1 Max Cost per Query
- **Ceiling:** **$0.10**
- **Rationale:** Allows for multi-step reasoning and expanded context in ODR, but strictly caps out-of-control looping or excessive parallel searches.
- **Enforcement Code:** [`app/integrations/research_engine/budget.py`](file:///d:/koding/codes/NeosisLM/app/integrations/research_engine/budget.py)
  - The `UsageTracker` and `BudgetEnforcingCallbackHandler` intercept all LLM calls inside the LangGraph.
  - If the limits are breached (e.g., `model_calls`, `input_tokens`), it raises `ResearchBudgetExceeded`.
  - The `OpenDeepResearchEngine` adapter traps this exception and transitions the run to a `partial` state, ensuring a graceful halt instead of a hard crash.

### 3.2 P95 Latency Ceiling
- **Ceiling:** **3000ms (3.0s)** (in mocked environment)
- **Rationale:** Provides 2x overhead allowance for the LangGraph-based ODR architecture (which inherently has more nodes and state transitions than the legacy sequential orchestrator) while preventing unbounded graph cycles.
- **Enforcement Code:** [`app/workers/tasks.py`](file:///d:/koding/codes/NeosisLM/app/workers/tasks.py)
  - `run_research_agent_job()` wraps execution in a timer. The duration is logged via structured JSON (`duration_ms`), which Datadog/Splunk monitors asynchronously.

### 3.3 Minimum Quality Threshold
- **Ceiling:** **9.0**
- **Rationale:** Must match or exceed the legacy baseline's ability to cite sources and produce complete reports.
- **Enforcement Code:** [`scripts/benchmark_runner.py`](file:///d:/koding/codes/NeosisLM/scripts/benchmark_runner.py)
  - The `LLMJudge` class dynamically grades the final generated report. 
  - It uses deterministic checks (e.g., verifying `[1]` citation markers exist) combined with subjective LLM-as-a-judge scoring.
  - A score of 9 is composed of a deterministic 5 + subjective 4.

---

## 4. Optimization Strategies (Ticket 05)

If ODR exceeds these ceilings (as seen initially in `odr_unoptimized_baseline.json`), the following configuration limits in `engine.py` are clamped to constrain runtime behavior without altering the upstream graph:

- `max_concurrent_research_units`: Throttles the `supervisor` node from fanning out too many parallel `researcher` subgraphs.
- `max_researcher_iterations`: Limits the depth of the supervisor's reflection loops.
- `max_react_tool_calls`: Prevents the individual researcher agents from getting stuck in endless search-and-retry cycles.

By passing these strict values into the ODR `config`, we safely bridge the power of deep research with the operational stability of a production consumer API.
