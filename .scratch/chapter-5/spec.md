# Chapter 5 — Research Engine Upstream Cutover (2-Phase Spec)

Source plan: `RESEARCH_ENGINE_UPSTREAM_CUTOVER_2_PHASE_PLAN.md` (repo root).
Decisions below were settled in a grilling session (Q1–Q27) and are binding. Do not reopen them without a concrete contradiction.

## Problem Statement

NeosisLM was meant to be a thin compatibility layer over upstream research engines. In practice the repo contains
invented research machinery next to the real Open Deep Research (ODR) integration:

- a custom `ResearchModeOrchestrator` + `LegacyResearchEngine` (planner/executor/synthesizer loop, own prompts);
- a custom retriever framework (`services/research/retrievers/*`) and a `GPTResearcherTool`/`GPTResearcherRetriever` bridge
  that are not reachable from the default ODR path;
- a legacy `WebSearchTool` that is injected into every engine but used only by the legacy one;
- `STORM` and `GPT-Researcher` advertised as supported but not actually integrated.

The ODR adapter (`open_deep_research/engine.py`) also does product work that belongs to the worker/service layer
(report persistence, candidate creation, DB lookups, env mutation), and the worker and engine both emit terminal states,
which can produce duplicate terminal events and leave cancelled runs without a finalization pass.

## Solution

Two phases.

- **Phase 1 — ODR cutover + deletion.** ODR is the only supported engine. All invented research machinery is deleted.
  The ODR adapter is reduced to the engine boundary; the worker becomes the single owner of terminal state and persistence.
- **Phase 2 — STORM + GPT-Researcher as real upstream engines.** Thin adapters over the actual `knowledge_storm` and
  `gpt_researcher` runtimes behind the same contract.

Target architecture:

`API/ChatService -> ResearchRun -> Worker -> ResearchEngineFactory -> {ODR | STORM | GPT-Researcher adapter} -> Upstream runtime`

Neosis owns: workspace, auth, ResearchRun, admission/quota, policy, context injection, evidence/provenance persistence,
events, cancellation signalling, budgets/usage accounting, promotion gates, graph projection, API/worker lifecycle.
The upstream engine owns: planning, decomposition, search/research loop, reflection, synthesis, report generation.

## Settled decisions (Q1–Q27)

| # | Decision |
|---|---|
| Q1 | `ACTIVE_RESEARCH_ENGINE` is only the default for new workspaces/requests without an engine. The factory resolves the persisted `ResearchRun.engine` and nothing else. The env-override/rollback behaviour is removed. |
| Q2 | One `SUPPORTED_ENGINES` constant shared by admission and the factory. Phase 1: `("open_deep_research",)`. `storm` / `gpt_researcher` are rejected like unknown names until Phase 2. |
| Q3 | Migration changes only `workspaces.research_engine = 'legacy'` → `'open_deep_research'` and the server/model default. Historical `research_runs.engine` values are untouched. No check constraint yet. Production must be inspected (T0 preflight) — do not assume production matches dev. |
| Q4 | `ResearchEngineFactory.get_engine(engine_name, redis_client=None)`; `OpenDeepResearchEngine(redis_client=None)`. `llm_gateway` / `search_tool` plumbing removed. |
| Q5 | Full test sweep: mechanically replace `"legacy"` fixture values; delete tests that validate deleted code; rewrite `tests/test_research_agent.py` only if it still gives ODR coverage, otherwise delete. |
| Q6 | Benchmark runner: default `open_deep_research`, `--engine` limited to supported engines, real-provider only. `legacy_baseline.json` kept as immutable historical data and marked obsolete. |
| Q7 | Real-provider smoke test is the gate (see verification checklist), including exactly one terminal state and no duplicate terminal event. |
| Q8 | Final report + `memory_candidate` persistence moves out of the engine into an engine-agnostic `ResearchService` method called by the worker. |
| Q9 | All `final_graph` / `graph_candidate` creation is removed from the ODR path (engine and worker). Promotion/projection infrastructure stays. "Research graph generation" is recorded as a Chapter 5 product gap, not solved with a Neosis-invented step. |
| Q10 | The worker resolves prior evidence and `research_context`. `_format_research_context` moves to `app/services/research/context.py` as `format_research_context`. The adapter only receives data and decides how upstream consumes it. |
| Q11 | One `resolve_llm_provider()` is the single provider-resolution path (used by `config.py`, `api/deps/llm.py`, the worker, and adapters). Engine-level env mutation is removed. Usage checkpointing is unchanged. |
| Q12 | Ticket order: preflight → allow-list/migration → factory/worker signature → delete legacy → delete retrievers → thin the adapter → verification/docs. The adapter work happens after the deletions. |
| Q13 | Deterministic offline harness lives under `tests/` (patches ODR model construction and `neosis_web_search`). No test-only hooks in production code. |
| Q14 | The worker is the only writer of terminal run state and the only publisher of terminal events. Engines emit progress events plus one `final_report` event; failures are exceptions. Engine terminal/fence events are removed. |
| Q15 | `completed` requires a `final_report` event. No report → `failed` with reason `engine_finished_without_report`. `partial` (budget exceeded) stays terminal with no salvage report. |
| Q16 | The worker runs the engine stream in a child task it owns. On Redis cancel it cancels that task, catches `CancelledError`, and finalizes through the normal path. The API still writes `cancelled` for user cancels; the worker tolerates an already-terminal state (`InvalidTransitionError`). `engine.cancel()` remains on the interface (no-op for ODR). |
| Q17 | One explicit `{"status": "final_report", "report": "<markdown>"}` event, consumed by the worker, never bridged to chat. `ui/app.py` is checked for reliance on the old `summary` field. |
| Q18 | Coarse ODR progress events are kept in Phase 1. `subgraphs=True` granularity is a later UX ticket. |
| Q19 | `tests/smoke/test_odr_real_provider.py`, marked `real_provider`, skipped unless explicitly enabled. |
| Q20 | New ADR 0005 supersedes only ADR 0002's "GPT Researcher as retriever" clause. ADR 0002's STORM deferral stays until a Phase 2 ADR. |
| Q21 | Add glossary entries to `docs/CONTEXT.md`: Research Engine, Engine Adapter, Supported Engines, Final Report event, Terminal State Owner. |
| Q22 | `ui/app.py` drops the `legacy` option; engine shown as fixed `open_deep_research` (hardcoded, no new endpoint). |
| Q23 | Unsupported engine → `HTTPException(422, detail="unsupported_research_engine")` in `ResearchAdmissionController.admit_research_run`; the factory raises `ResearchEngineSetupError` as backstop. |
| Q24 | Migration chains from current head `f7a8b9c0d1e2`; downgrade restores only the server default and documents that the data change is irreversible; `scripts/validate_migrations.py` is part of the gate. |
| Q25 | `STORM_ENABLED` and the `gpt-researcher` / `knowledge-storm` requirements are left untouched in Phase 1. |
| Q26 | Add an ODR section to `docs/UPSTREAM_REVISION.md` (repo URL, full commit SHA from `references/open_deep_research`, list of Neosis patches). Documentation only. |
| Q27 | The full test suite is run once at the start of Phase 1 (T0) and recorded as the baseline. "Suite passes" = no new failures versus that baseline. Tests of deleted code are deleted, not left failing. Pre-existing failures are documented, not fixed in Phase 1. |

Additional rule: **no Phase 1 code is written to make Phase 2 easier.** Phase 2 adapters conform to the same
final-output contract independently.

## Ticket index

Phase 1 (`phase1-odr-cutover/issues/`): 01 preflight+baseline, 02 allow-list+migration, 03 factory/worker signature,
04 delete legacy stack, 05 delete retriever stack, 06 extract context+evidence loading, 07 `final_report` contract +
service finalization + graph-candidate removal, 08 terminal-state ownership + cancellation, 09 provider consolidation,
10 verification harnesses (offline + real-provider smoke), 11 docs/ADR/glossary.

(Ticket 06–09 together are the plan's "thin the ODR adapter" step, split so each ticket is one reviewable change.)

Phase 2 (`phase2-storm-gpt-researcher/issues/`): 01 inspect upstream APIs, 02 STORM adapter, 03 GPT-Researcher adapter,
04 factory/config/allow-list, 05 contract tests + smoke + dead-code gate + ADR.

## Out of scope

- Redesigning Chapter 4, the memory model, the Ground pipeline, or the promotion system.
- Research graph generation (follow-up product gap).
- Finer-grained ODR progress events (`subgraphs=True`).
- Database check constraint on engine names (after Phase 2).
- Open Notebook / Ground behaviour.
