# Open Deep Research (ODR) Engine: Architecture, Onboarding, & Operations

This document is the authoritative technical reference and developer onboarding guide for the **Open Deep Research (ODR) Engine Integration** (Chapter 3). It is designed to take a new engineer from zero to fully understanding how the LangGraph-based research engine is wired into NeosisLM, how to safely build on top of it, and how to operate it in production.

---

## 1. Architectural Philosophy and Design Tenets

Integrating an external LangGraph-driven research engine requires careful orchestration to prevent budget overruns, hanging background jobs, and state corruption. We adhere to these tenets:

1. **Neosis Owns the Product Boundary:** Neosis is the canonical source of truth for Workspaces, Runs, Evidence, and Lifecycles. The ODR LangGraph implementation (`deep_researcher.py`) is treated as an isolated upstream dependency. It does not know about Postgres or Neosis UI.
2. **Anti-Corruption Layer (ACL):** The LangGraph engine emits arbitrary internal states (`clarify_with_user`, `research_supervisor`, `write_research_brief`). The adapter (`engine.py`) intercepts these states and normalizes them into standard Neosis `ResearchEvent` schemas (`planning`, `executing`, `synthesizing`).
3. **Strict Budgeting:** ODR uses recursive AI loops. We inject a `UsageTracker` and `BudgetEnforcingCallbackHandler` directly into the LangGraph callbacks to track every token. If the graph exceeds its budget, an explicit `ResearchBudgetExceeded` exception halts execution cooperatively.
4. **Idempotent Background Lifecycles:** The graph is executed inside an ARQ worker (`tasks.py`). If the worker crashes, the `ResearchLifecycleService` ensures state transitions do not hang the frontend UI.

---

## 2. Developer Onboarding: Building on the Engine

If you are a new developer tasked with adding a new feature (e.g., adding a new search tool, altering the supervisor's logic, or fixing a bug in the graph), read this section first.

### 2.1 The Data Flow (End-to-End)
When a user types a research objective in the UI:
1. **API Layer (`ResearchController`)**: Accepts the objective and enqueues an ARQ job.
2. **Background Worker (`tasks.py > run_research_agent_job`)**:
   - Spawns in the background.
   - Looks up the workspace's `research_engine` flag.
   - Instantiates `OpenDeepResearchEngine` via the Factory.
   - Begins streaming events via `engine.astream_events()`.
3. **The Engine Adapter (`engine.py`)**:
   - Creates a `UsageTracker`.
   - Packages the initial state (the user's objective) and injects prior context if this is a retry.
   - Invokes the compiled LangGraph `astream()`.
4. **LangGraph Execution (`deep_researcher.py`)**:
   - The graph loops between `supervisor` and `researcher` nodes.
   - It performs searches and aggregates `notes`.
   - Finally, it generates a `final_report`.
5. **Event Normalization & Promotion**:
   - The adapter intercepts these graph transitions, emitting standard JSON over Redis pub/sub to the UI.
   - Upon completion, `run_research_agent_job` promotes the findings to the persistent Postgres knowledge graph and episodic memory.

### 2.2 How to Extend the LangGraph Upstream
The file `app/integrations/research_engine/upstream/open_deep_research/deep_researcher.py` contains the raw graph logic. 

**Adding a New Tool:**
If you want the researcher to use a new tool (e.g., querying an internal database):
1. Define the tool in `app/integrations/research_engine/upstream/open_deep_research/utils.py`.
2. Ensure the tool is appended to the list returned by `get_all_tools(config)`.
3. The `researcher` node automatically binds all tools returned by this function to the LLM. 
*Rule:* Do not hardcode Neosis dependencies (like `SessionLocal`) into the tool. Pass required data via the `RunnableConfig`.

**Altering the Graph Topology:**
The graph uses standard LangGraph `StateGraph`. If you add a new node (e.g., an `editor` node after `final_report_generation`):
1. Add the node to `deep_researcher_builder`.
2. Update the edges (e.g., `research_supervisor` -> `editor` -> `final_report_generation`).
3. **CRITICAL:** Update `engine.py`! The adapter uses `if node_name == "..."` to emit SSE events. If you introduce a new node without updating the adapter, the UI will go silent during that step.

### 2.3 Running & Debugging Locally
When building, use the automated benchmark runner to iterate rapidly without touching the UI.
```bash
# Run the benchmark against the ODR engine
PYTHONPATH="." .\venv\Scripts\python.exe scripts/benchmark_runner.py --engine open_deep_research
```
- This mocks the expensive web searches.
- If you need to trace the LangGraph execution, ensure `LANGCHAIN_API_KEY` is set in your `.env`. The tracing context `tracing_v2_enabled(project_name="NeosisLM-ResearchMode")` is automatically wrapped around the execution in `tasks.py` and `engine.py`.

---

## 3. Component Map: Detailed Code Index

### A. The Orchestration Layer
- **File:** [`app/workers/tasks.py`](file:///d:/koding/codes/NeosisLM/app/workers/tasks.py)
- **Function:** `run_research_agent_job(workspace_id, objective, run_id)`
- **Role:** The ARQ background worker. It initializes the execution, handles cooperative cancellation, and manages the `ResearchLifecycleService` to transition the run from `researching` -> `completed` / `failed`. It orchestrates the final memory promotion logic once the graph exits.

### B. The Factory and Feature Flags
- **File:** [`app/integrations/research_engine/factory.py`](file:///d:/koding/codes/NeosisLM/app/integrations/research_engine/factory.py)
- **Function:** `ResearchEngineFactory.get_engine()`
- **Role:** Routes execution to either the `LegacyResearchEngine` or the `OpenDeepResearchEngine`. The global fallback is controlled by the `ACTIVE_RESEARCH_ENGINE` flag in `app/core/config.py`.

### C. The Anti-Corruption Layer (Adapter)
- **File:** [`app/integrations/research_engine/open_deep_research/engine.py`](file:///d:/koding/codes/NeosisLM/app/integrations/research_engine/open_deep_research/engine.py)
- **Class/Function:** `OpenDeepResearchEngine.astream_events()`
- **Role:** The boundary wall. It accepts the canonical Neosis `objective`, configures the LangGraph execution with strict ceilings (`max_concurrent_research_units`, `max_researcher_iterations`), and executes the graph. It maps internal LangGraph node updates to Neosis events and writes periodic token usage to Postgres via `create_usage()`.

### D. The ODR LangGraph Implementation
- **File:** [`app/integrations/research_engine/upstream/open_deep_research/deep_researcher.py`](file:///d:/koding/codes/NeosisLM/app/integrations/research_engine/upstream/open_deep_research/deep_researcher.py)
- **Role:** The core graph builder (`deep_researcher_builder`). Contains the actual logic nodes:
  - `clarify_with_user`: Determines if the prompt is too vague.
  - `research_supervisor`: Plans the sub-queries.
  - `researcher` (subgraph): Executes searches and compresses them.
  - `final_report_generation`: Synthesizes the final output.

### E. Telemetry and Budgeting
- **File:** [`app/integrations/research_engine/budget.py`](file:///d:/koding/codes/NeosisLM/app/integrations/research_engine/budget.py)
- **Class:** `UsageTracker` & `BudgetEnforcingCallbackHandler`
- **Role:** Hooks into `on_llm_end` during LangGraph execution. Tracks tokens and search calls.

---

## 4. Operational Guardrails & Observability

Use the structured JSON logs emitted by `tasks.py` and `engine.py` to monitor system health in production.

### 4.1 Latency Monitoring (Splunk / Datadog)
```sql
event="research_run_completed" OR event="research_run_failed" 
| stats p95(duration_ms) as p95_latency, avg(duration_ms) as avg_latency by engine
| where p95_latency > 3000
```
*Threshold:* P95 latency must remain below 3.0s.

### 4.2 Cost Monitoring
```sql
event="research_usage_final"
| eval estimated_cost = (model_calls * 0.01) + (search_calls * 0.005)
| stats avg(estimated_cost) as avg_cost_per_run
| where avg_cost_per_run > 0.10
```
*Threshold:* Average cost should remain below $0.10 per run.

### 4.3 Failure Rates
```sql
event="research_run_failed" OR event="research_run_completed"
| stats count(eval(status="failed")) as errors, count as total
| eval error_rate = (errors / total) * 100
| where error_rate > 5
```
*Threshold:* Error rate should remain under 5%.

---

## 5. Incident Procedures & Rollback

### Incident: High Latency or Cost Spike
1. **Diagnosis:** Check `research_usage_final` logs to see if `model_calls` or `search_calls` are spiking.
2. **Mitigation:** In `app/integrations/research_engine/open_deep_research/engine.py`, tighten the configurations:
   - Reduce `max_concurrent_research_units`
   - Reduce `max_researcher_iterations`
   - Reduce `max_react_tool_calls`
3. **Rollback:** If mitigation fails, proceed to Rollback Protocol.

### Incident: Graph Checkpointing Failures / Worker OOM
1. **Diagnosis:** Look for `MemorySaver` size explosion or worker crash logs.
2. **Mitigation:** Ensure the graph limits in `engine.py` are strictly enforced to prevent unbounded context growth. 
3. **Rollback:** Proceed to Rollback Protocol immediately to prevent API starvation.

### Rollback Protocol (Global)
To globally route traffic back to the legacy `ResearchModeOrchestrator`:
1. Change `ACTIVE_RESEARCH_ENGINE` in `app/core/config.py` back to `"legacy"`.
2. Redeploy the API workers. 
3. *Note:* In-flight ODR runs may fail during worker restart; the idempotency guard will allow users to safely retry.

### Rollback Protocol (Per-Workspace)
To bypass the global setting for a specific problematic workspace (useful for VIP customers):
```sql
UPDATE workspaces 
SET research_engine = 'legacy' 
WHERE workspace_id = '<WORKSPACE_UUID>';
```

---

## 6. Deprecation Notice
The legacy [`ResearchModeOrchestrator`](file:///d:/koding/codes/NeosisLM/app/orchestration/research_mode.py) and [`LegacyResearchEngine`](file:///d:/koding/codes/NeosisLM/app/integrations/research_engine/legacy.py) are marked with `@deprecated`. They are retained solely as a safety fallback and will be removed in Chapter 5. Do not add new features to them.
