# Chapter 5 — Final Acceptance and Verification Checklist

Use this for the Phase 1 gate (ODR only) and again per enabled engine in Phase 2. Do not mark a phase complete from import
tests alone.

## A. Architecture

- [ ] `API/ChatService -> ResearchRun -> Worker -> ResearchEngineFactory -> adapter -> upstream runtime` is the only research path.
- [ ] No planner / executor / synthesizer / researcher loop exists in `app/`; no upstream engine is reimplemented in `app/`.
- [ ] The worker is the single owner of terminal run state and terminal events.
- [ ] Engines yield progress + exactly one `final_report`; failures are exceptions.

## B. Phase 1 deliverables

- [ ] New workspaces default to `open_deep_research`; no `legacy` workspaces remain after migration (preflight re-run).
- [ ] Unsupported engines are rejected at admission with 422 `unsupported_research_engine`; the factory raises `ResearchEngineSetupError` as backstop.
- [ ] `ResearchEngineFactory.get_engine(engine_name, redis_client=None)`; `OpenDeepResearchEngine(redis_client=None)`; no `search_tool` / `llm_gateway` plumbing.
- [ ] `ACTIVE_RESEARCH_ENGINE` has no effect on factory resolution of a persisted `ResearchRun.engine`.
- [ ] `ResearchModeOrchestrator`, `LegacyResearchEngine`, `WebSearchTool`, retriever package, `GPTResearcherRetriever`, `GPTResearcherTool` are deleted.
- [ ] `final_graph` / `graph_candidate` creation removed from the ODR path; promotion/projection code unchanged.
- [ ] `format_research_context` lives in `app/services/research/context.py`; the adapter does no context DB reads.
- [ ] One `resolve_llm_provider()`; the engine writes nothing to `os.environ`.
- [ ] `docs/adr/0005`, `docs/CONTEXT.md` glossary, `docs/UPSTREAM_REVISION.md` ODR section, obsolete note for `legacy_baseline.json`.

## C. Dead-code gate (expected: no application hits)

Search `app tests scripts ui` (historical `.scratch/` and graph exports excluded) for:

`ResearchModeOrchestrator`, `LegacyResearchEngine`, `RetrieverRegistry`, `WebRetriever`, `AcademicRetriever`, `MCPRetriever`,
`GPTResearcherRetriever`, `GPTResearcherTool`, `WebSearchTool`, `research_engine="legacy"`, `planner_node`, `executor_node`,
`synthesizer_node`, `reporter_node`, `services.research.retrievers`, `orchestration.research_mode`, `services.web_search`.

## D. Tests

- [ ] Baseline recorded in `.scratch/chapter-5/phase1-odr-cutover/baseline.md` before any change.
- [ ] Full suite: no new failures versus the baseline; tests of deleted code are deleted, not failing; pre-existing failures documented.
- [ ] `scripts/validate_migrations.py` and `tests/unit/test_migrations.py` pass.
- [ ] Offline deterministic harness passes (no test-only hooks in production code).

## E. Real-provider smoke gate (per enabled engine)

Run: `RUN_REAL_PROVIDER_SMOKE=1 pytest tests/smoke -m real_provider`

1. [ ] A ResearchRun is created with the expected `engine` and completes.
2. [ ] Events reach the canonical event stream (`research_events` and chat events).
3. [ ] Sources/evidence retain provenance.
4. [ ] The final report is persisted.
5. [ ] No research-derived material becomes Ground evidence.
6. [ ] Engine selection is deterministic (unsupported engine → 422).
7. [ ] Failure and cancellation do not leave a running/stuck ResearchRun; cancellation finalizes through the worker.
8. [ ] Exactly one terminal run state and no duplicate terminal event.

Report quality is not a gate.

## F. Known follow-ups (recorded, not in scope)

- Research graph generation (Output KG from research runs) — product gap after ODR cutover.
- Finer-grained ODR progress events (`subgraphs=True`).
- DB check constraint on engine names (after Phase 2).
- Phase 2: STORM and GPT-Researcher adapters, ADR superseding 0002's STORM deferral, load-test status.
