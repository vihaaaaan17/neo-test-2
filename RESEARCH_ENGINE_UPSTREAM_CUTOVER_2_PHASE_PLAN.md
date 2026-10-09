# NeosisLM Research Engine — 2-Phase Upstream Cutover & Cleanup Plan

Repository audited: `vihaaaaan17/neo-test-2` (`main`)

Goal: finish the research-engine architecture without rebuilding the research system. Neosis owns product/runtime concerns; upstream engines own research algorithms.

## Target end state

- ODR core: **DONE / retained**
- ODR compatibility/product layer: **retained, but made thinner**
- STORM: **real upstream engine, thin Neosis adapter**
- GPT-Researcher: **real upstream engine, thin Neosis adapter**
- Custom retriever framework: **REMOVED**
- Legacy research engine/orchestrator: **REMOVED**
- Legacy search service used only by that engine: **REMOVED**
- `ResearchEngineFactory`: resolves only supported upstream engines
- No custom planner / executor / synthesizer / researcher loop remains in Neosis
- No upstream engine is reimplemented inside `app/`

## Non-negotiable boundary

Neosis owns: workspace, auth, ResearchRun, admission/quota, policy, context injection, evidence/provenance persistence, events, cancellation signalling, budgets/usage accounting, promotion gates, graph projection, API/worker lifecycle.

The upstream engine owns: planning, task decomposition, search/research loop, reflection, source exploration, synthesis, and report generation.

A Neosis adapter may translate inputs/outputs/events and attach Neosis metadata. It must not recreate the upstream research algorithm.

---

# PHASE 1 — ODR Cutover + Remove Dead/Legacy Research Stack

## Objective

Make ODR the only active engine, remove all obsolete custom research mechanics, and leave the current ODR integration as the single clean compatibility boundary.

## 1. Make ODR the database/default engine

### Change

**File:** `app/models/workspace.py`

**Symbol:** `Workspace.research_engine`

Change the model default from `"legacy"` to `"open_deep_research"`.

**Migration:** `alembic/versions/5172a2f9d3aa_add_research_engine_models_and_flags.py`

Do not edit an old migration in place once deployed. Add a new migration that:

1. updates existing `workspaces.research_engine = 'legacy'` rows to `'open_deep_research'`;
2. changes the server default to `'open_deep_research'`;
3. optionally adds a database check constraint for the supported engine names after Phase 2 is complete.

### Verify

**File:** `app/api/routes/workspaces.py`

**Function:** `create_workspace`

Confirm workspace creation no longer produces legacy-backed workspaces.

---

## 2. Remove legacy from engine resolution

### Change

**File:** `app/integrations/research_engine/factory.py`

**Function:** `ResearchEngineFactory.get_engine`

Phase 1 target:

- keep `open_deep_research`;
- keep `storm` and `gpt_researcher` branches disabled until Phase 2 if desired;
- remove the `legacy` branch and the import of `LegacyResearchEngine`;
- fail clearly on unsupported engine names.

Also remove the misleading fallback logic that makes a caller-supplied engine compete with configuration. The canonical precedence should be explicit:

`ResearchRun.engine` / selected engine -> validated factory resolution.

Configuration may define the default, but must not silently change an already persisted engine selection.

---

## 3. Stop injecting a Neosis search implementation into ODR

### Change

**File:** `app/workers/tasks.py`

**Function:** `run_research_agent_job`

Remove the legacy construction:

`WebSearchTool()`

and stop passing that object into `ResearchEngineFactory.get_engine(...)` for ODR.

ODR should continue to build its own search tool through its upstream tool assembly, with Neosis-specific evidence interception only where already required.

### Follow-through

**File:** `app/integrations/research_engine/factory.py`

**Function:** `ResearchEngineFactory.get_engine`

Remove the `search_tool` parameter if no active engine requires it after Phase 1. If the common interface is kept for Phase 2 compatibility, it must be optional and ignored by engines that own their upstream tooling.

---

## 4. Keep `neosis_web_search` only as the ODR/Neosis integration bridge

### Keep

**File:** `app/integrations/research_engine/tools/neosis_search_tools.py`

**Relevant callable:** `neosis_web_search` / its tool wrapper implementation.

This is allowed because it is not a new retrieval algorithm. It is the boundary where upstream ODR search results enter Neosis evidence/provenance handling.

### Remove the duplicate search implementation

**File:** `app/services/web_search.py`

Delete the legacy `WebSearchTool` implementation once repository search confirms no active callers remain after Phase 1.

The expected remaining caller from the current tree is `app/workers/tasks.py`; remove that dependency first.

---

## 5. Remove the custom retriever framework

The following files are obsolete once ODR owns retrieval/tool selection:

- `app/services/research/retrievers/base.py`
- `app/services/research/retrievers/registry.py`
- `app/services/research/retrievers/web.py`
- `app/services/research/retrievers/academic.py`
- `app/services/research/retrievers/mcp.py`
- `app/services/research/retrievers/gpt_researcher.py`
- `app/services/research/retrievers/__init__.py`

### Important

Do **not** move these classes into a new location. Do not replace them with another custom registry. ODR already has upstream tool selection and the repo already has Neosis-specific search/provenance plumbing.

### Tests to remove/replace

**File:** `tests/unit/services/research/test_retrievers.py`

Delete the tests for the obsolete registry/retriever classes. Replace only the behavior that is still part of the supported architecture, mainly ODR search-tool/provenance integration tests.

---

## 6. Remove the legacy research engine completely

Delete:

- `app/integrations/research_engine/legacy.py`
- `app/orchestration/research_mode.py`

The second file contains the custom research algorithm that must disappear:

- `ResearchModeOrchestrator._build_graph`
- `ResearchModeOrchestrator.planner_node`
- `ResearchModeOrchestrator.executor_node`
- `ResearchModeOrchestrator.executor_router`
- `ResearchModeOrchestrator.synthesizer_node`
- `ResearchModeOrchestrator.reporter_node`
- `ResearchModeOrchestrator.astream_events`
- `ResearchModeOrchestrator.run`

These functions are precisely the duplicated planning/execution/synthesis stack that the upstream-engine architecture is intended to eliminate.

### Tests/scripts to update

Remove or rewrite legacy-specific code in:

- `tests/test_research_agent.py`
- `tests/unit/test_orchestrator_deprecation.py`
- `tests/integration/benchmark/test_rollback.py` where legacy is used as an engine fixture
- `tests/integration/benchmark/test_rollback_verification.py` where legacy is hard-coded
- `scripts/benchmark_runner.py`

In `scripts/benchmark_runner.py` specifically:

- change `--engine` choices to supported engines;
- change the default from `legacy` to `open_deep_research`;
- remove mock `search_tool` plumbing if the factory no longer accepts it;
- rename `legacy_baseline.json` output references if still relevant.

---

## 7. Thin the ODR adapter without touching ODR's algorithm

**File:** `app/integrations/research_engine/open_deep_research/engine.py`

**Function:** `OpenDeepResearchEngine.astream_events`

Keep the following responsibilities only:

1. accept canonical Neosis inputs;
2. construct the ODR runtime config;
3. inject bounded `research_context`;
4. invoke the upstream compiled graph;
5. translate upstream execution signals into Neosis-compatible events;
6. surface structured upstream output to the worker/service layer.

Avoid adding any new planner/search/synthesis logic here.

### Product logic cleanup

The current function contains substantial persistence/orchestration work around usage, reports, candidates and timeline fencing. Do not redesign the data model in Phase 1. Instead, isolate these sections behind clearly named Neosis service calls where practical, leaving `astream_events` as the engine boundary.

Prefer extraction to existing product services rather than inventing new engine-specific abstractions.

---

## 8. Preserve ODR upstream internals as upstream code

**Files:**

- `app/integrations/research_engine/upstream/open_deep_research/deep_researcher.py`
- `app/integrations/research_engine/upstream/open_deep_research/utils.py`

Do not rewrite the ODR graph.

`deep_researcher.py` remains the research algorithm.

In `utils.py`, keep upstream search/tool assembly. The existing `get_search_tool` / `get_all_tools` boundary may continue to select Tavily, MCP, `ResearchComplete`, and `think_tool` as dictated by upstream ODR configuration.

Do not reintroduce `GPTResearcherTool` into `get_all_tools` as a replacement for the retriever system. GPT-Researcher becomes a separate engine in Phase 2.

---

## Phase 1 acceptance criteria

- New workspaces default to `open_deep_research`.
- Existing legacy workspaces are migrated to ODR.
- `ResearchEngineFactory` cannot instantiate `LegacyResearchEngine`.
- `ResearchModeOrchestrator` is gone.
- `WebSearchTool` legacy path is gone.
- Custom retriever package is gone.
- `GPTResearcherRetriever` is gone.
- `GPTResearcherTool` is gone as a tool-level integration.
- ODR still executes through the vendored upstream graph.
- No new research algorithm exists in Neosis.
- Full unit/integration suite passes.
- ODR real-provider smoke test passes end-to-end.

---

# PHASE 2 — Add STORM + GPT-Researcher as True Upstream Engines

## Objective

Expose STORM and GPT-Researcher as top-level engine implementations using only their upstream runtimes. Neosis adds adapters, not alternative research systems.

## 1. Introduce a single engine adapter pattern

Keep:

**File:** `app/integrations/research_engine/engine.py`

**Interface:** `ResearchEngine`

Required adapter surface remains:

- `astream_events(...)`
- `cancel()`

The adapter contract is intentionally small.

---

## 2. Add STORM adapter

### New file

`app/integrations/research_engine/storm/engine.py`

### Required class

`StormResearchEngine`

### Implementation rule

The adapter must call the actual `knowledge_storm` runtime. It must not reproduce STORM's:

- question decomposition;
- perspective generation;
- multi-pass research;
- citation gathering;
- article drafting;
- synthesis logic.

The adapter only:

1. maps Neosis objective/context into STORM inputs;
2. supplies configured upstream providers/credentials;
3. invokes STORM;
4. maps STORM outputs/events into the Neosis contract;
5. returns structured report/citation/output metadata;
6. maps cancellation where the upstream runtime supports it.

### Do not guess the third-party API

Before implementation, inspect the installed `knowledge-storm` package/version and use its actual public runtime API. Do not write compatibility code against an assumed STORM API.

---

## 3. Add GPT-Researcher adapter

### New file

`app/integrations/research_engine/gpt_researcher/engine.py`

### Required class

`GPTResearcherEngine`

This replaces both of the old layers:

- `app/services/research/retrievers/gpt_researcher.py`
- `app/integrations/research_engine/tools/gpt_researcher_tool.py`

### Implementation rule

GPT-Researcher is a **full engine**, not a search tool inside ODR.

The adapter must:

1. instantiate the upstream `GPTResearcher` runtime using its supported API;
2. pass the canonical research objective and allowed inputs;
3. let GPT-Researcher perform its own planning/research/crawl/report workflow;
4. collect the upstream sources/report;
5. normalize those into Neosis report/evidence structures;
6. expose them through the same `ResearchEngine` interface.

Do not build a second planner around GPT-Researcher.

Do not patch its internal LLM implementation unless required for a narrow provider compatibility boundary. Prefer the upstream configuration mechanism over environment mutation or monkey-patching.

---

## 4. Update factory to support exactly three upstream engines

**File:** `app/integrations/research_engine/factory.py`

**Function:** `ResearchEngineFactory.get_engine`

Supported values:

- `open_deep_research`
- `storm`
- `gpt_researcher`

Unknown values fail deterministically.

Each branch should only instantiate the matching thin adapter.

No branch may instantiate a custom orchestrator, retriever registry, or alternate research loop.

---

## 5. Configuration becomes explicit

**File:** `app/core/config.py`

Keep:

`ACTIVE_RESEARCH_ENGINE = "open_deep_research"`

Add only the minimum enablement/provider settings required by the actual upstream packages.

Remove the old meaning of `STORM_ENABLED` as a formal deferral flag. Once STORM works, the setting should describe availability/configuration, not architecture status.

Do not create a large engine-specific configuration framework unless an upstream package genuinely requires it.

---

## 6. Worker stays engine-agnostic

**File:** `app/workers/tasks.py`

**Function:** `run_research_agent_job`

The worker should:

1. load `ResearchRun`;
2. resolve its engine through `ResearchEngineFactory`;
3. execute `engine.astream_events(...)`;
4. persist/bridge canonical Neosis events;
5. finalize ResearchRun state.

It should not contain engine-specific planner/search/synthesis branches.

Engine-specific differences belong inside the adapter.

---

## 7. Tests: replace implementation tests with contract tests

Add/retain engine contract tests that prove every adapter:

- accepts the same Neosis input contract;
- produces normalized research events;
- returns a final report/result;
- preserves workspace/run identity;
- handles failure;
- handles cancellation where supported;
- does not bypass Neosis evidence/provenance boundaries.

Recommended files:

- `tests/unit/integrations/research_engine/test_odr_engine_integration.py`
- `tests/unit/integrations/research_engine/test_storm_engine_integration.py`
- `tests/unit/integrations/research_engine/test_gpt_researcher_engine_integration.py`

Retire tests whose purpose is to validate deleted implementations rather than supported behavior.

---

## 8. Final repository search / dead-code gate

Before declaring Phase 2 complete, search the whole repository for:

- `ResearchModeOrchestrator`
- `LegacyResearchEngine`
- `RetrieverRegistry`
- `WebRetriever`
- `AcademicRetriever`
- `MCPRetriever`
- `GPTResearcherRetriever`
- `GPTResearcherTool`
- `WebSearchTool`
- `research_engine="legacy"`
- `planner_node`
- `executor_node`
- `synthesizer_node`
- `reporter_node`

Expected result: no active application references. Historical `.scratch/` or graph-export documentation may remain, but it must not be imported/executed by production code.

---

# Final Definition of Done

## Architecture

`API/ChatService -> ResearchRun -> Worker -> ResearchEngineFactory -> {ODR | STORM | GPT-Researcher adapter} -> Upstream runtime`

Neosis product/runtime logic surrounds the engine. The engine algorithm itself never lives in Neosis.

## Engine status

| Engine | Status after this plan |
|---|---|
| ODR | Active, primary, upstream algorithm retained |
| STORM | Active, upstream runtime behind thin adapter |
| GPT-Researcher | Active, upstream runtime behind thin adapter |
| Legacy engine | Deleted |
| Custom retriever framework | Deleted |
| GPT-Researcher tool/retriever bridge | Deleted; replaced by top-level engine adapter |

## Verification gate

Do not mark this complete from import tests alone. For each engine that is enabled in the environment, run one real-provider smoke test and verify:

1. ResearchRun is created and completes.
2. Events reach the canonical event stream.
3. Sources/evidence retain provenance.
4. Final report is persisted.
5. No research-derived material becomes Ground evidence.
6. Engine selection is deterministic.
7. Failure/cancellation does not leave a running/stuck ResearchRun.

## Critical rule

Do not use this cleanup as a reason to redesign Chapter 4, the memory model, the Ground pipeline, or the promotion system. This plan is specifically for making the research-engine boundary correct and removing duplicated research implementations.
