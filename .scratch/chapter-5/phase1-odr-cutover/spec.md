# Phase 1 — ODR Cutover + Removal of Legacy/Dead Research Stack

Parent: `.scratch/chapter-5/spec.md` (decisions Q1–Q27 apply verbatim).

## Objective

Make `open_deep_research` the only active engine, delete all invented research mechanics, and leave the ODR integration
as the single clean compatibility boundary with the worker as sole owner of terminal state and persistence.

## Current state (facts verified in the repo)

- `Workspace.research_engine` defaults to `"legacy"` (model and migration `5172a2f9d3aa`); alembic head is `f7a8b9c0d1e2`.
- Dev DB: 1,125 workspaces on `legacy`; `research_runs.engine` holds free-form values (`legacy`, `test`, `test_engine`, `odr`, `open_deep_research`).
  Admission accepts any string; the factory fails late inside the worker.
- `ResearchEngineFactory.get_engine(engine_name, llm_gateway, search_tool, redis_client)`; the env var `ACTIVE_RESEARCH_ENGINE`
  is used as a fallback and by rollback tests as a kill-switch for `legacy`.
- `OpenDeepResearchEngine` stores `llm_gateway` / `search_tool` and never uses them.
- `tasks.py::run_research_agent_job` builds `WebSearchTool()` for every run.
- `OpenDeepResearchEngine.astream_events` (≈330 lines) does DB reads (prior evidence, research_context), env mutation,
  usage checkpointing, a timeline-fence check, `create_report`, `memory_candidate` and `graph_candidate` creation, and
  yields its own `failed/partial/cancelled` statuses. ODR never produces `final_graph`; that is legacy-only.
- The worker derives `final_status` as `"completed"` unless an engine event says otherwise (no report required),
  republishes engine terminal events, and does not catch `CancelledError`. `engine.cancel()` cancels the worker's own task.
- `services/research/retrievers/*` (+ `gpt_researcher_tool.py`) is imported by nothing on the ODR path.
- `legacy` as a string appears in 12 test files plus `scripts/benchmark_runner.py`, `ui/app.py`, `app/models/workspace.py`.

## Implementation decisions

See the parent decision table. Key mechanics:

- `SUPPORTED_ENGINES = ("open_deep_research",)` is defined next to the `ResearchEngine` interface
  (`app/integrations/research_engine/engine.py`) and imported by admission and the factory.
- Engine → worker contract: engines yield progress dicts (`status` in `starting|planning|executing|researching|synthesizing`)
  and exactly one `{"status": "final_report", "report": str}`. Failures are raised: `ResearchBudgetExceeded` → `partial`,
  `asyncio.CancelledError` → `cancelled`, any other exception → `failed`.
- Worker finalization order: fence check → map terminal status → if completed, `ResearchService` persists report +
  `memory_candidate` → candidate normalization (existing) → lifecycle transition → turn finalization → single terminal event.
- `resolve_llm_provider()` returns the resolved key/base URL/model for the active provider (OpenAI-compatible or NVIDIA),
  and is the only place that reads provider env/settings.

## Testing decisions

- Unit tests: admission validation, factory resolution, `format_research_context`, `ResearchService` finalization,
  worker terminal-state mapping and cancellation (with a stub engine), `resolve_llm_provider`.
- Offline deterministic harness (ticket 10) under `tests/`, patching ODR model construction and `neosis_web_search`.
- Real-provider smoke (ticket 10): `tests/smoke/test_odr_real_provider.py`, `real_provider` marker, opt-in.
- Baseline (ticket 01): full suite once before any change; the phase is done when there are no new failures against it.

## Acceptance criteria

- New workspaces default to `open_deep_research`; existing `legacy` workspaces are migrated.
- Unsupported engine names are rejected at admission with 422 `unsupported_research_engine`.
- `ResearchModeOrchestrator`, `LegacyResearchEngine`, `WebSearchTool`, the retriever package, `GPTResearcherRetriever`
  and `GPTResearcherTool` no longer exist; the dead-code search in the verification checklist returns no application hits.
- ODR still executes through the vendored upstream graph; no new research algorithm exists in Neosis.
- Terminal state/events are owned by the worker: exactly one terminal run state and no duplicate terminal event.
- A cancelled run ends terminal (not stuck) with finalization performed.
- Full suite: no new failures versus the ticket-01 baseline.
- Real-provider ODR smoke test passes (checklist items 1–8).

## Out of scope

Everything listed in the parent spec, plus any STORM / GPT-Researcher adapter work.
