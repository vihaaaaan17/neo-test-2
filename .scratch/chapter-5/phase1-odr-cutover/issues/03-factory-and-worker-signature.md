# 03: Factory and Worker Signature Cleanup

**What to build:**
Reduce the factory and ODR constructor to what ODR actually needs, remove the legacy branch and env override from engine
resolution, and stop the worker from building a legacy search tool.

**Blocked by:** 02

**Status:** done (2026-10-07)

- [x] `ResearchEngineFactory.get_engine(engine_name, redis_client=None)`:
  - remove the `legacy`, `storm` and `gpt_researcher` branches and the `LegacyResearchEngine` import;
  - remove the `ACTIVE_RESEARCH_ENGINE` env/settings fallback; the factory resolves only the supplied persisted engine name;
  - raise `ResearchEngineSetupError` for any name not in `SUPPORTED_ENGINES` (backstop; admission is the primary check).
- [x] `OpenDeepResearchEngine.__init__(self, redis_client=None)`: remove `llm_gateway` and `search_tool`.
- [x] `app/workers/tasks.py::run_research_agent_job`: remove `WebSearchTool` import/construction and the research-job
      `llm_gateway` closure used only for the factory call; call `get_engine(engine_name=engine_flag, redis_client=redis)`.
      Leave `ctx["llm_call"]` and other jobs' gateways alone.
- [x] `ACTIVE_RESEARCH_ENGINE` stays in `app/core/config.py` as the default used at admission/workspace creation only.
- [x] Delete or rewrite tests that exercise the removed behaviour at the factory level
      (`tests/integration/benchmark/test_rollback.py`, `tests/integration/benchmark/test_rollback_verification.py`,
      the legacy case in `tests/unit/integrations/research_engine/test_odr_engine_integration.py`) so the suite stays green;
      the remaining legacy files are deleted in ticket 04.
- [x] Add factory unit tests: ODR resolves; unknown/`legacy`/`storm` raise `ResearchEngineSetupError`; env var has no effect.
- [x] Confirm `legacy.py` / `research_mode.py` / `web_search.py` are now unreferenced by production code (they are deleted next).

## Notes (2026-10-07, implemented together with 04 and 05)

- `get_engine(engine_name, redis_client=None)` resolves only `SUPPORTED_ENGINES`; env/settings never override it. `OpenDeepResearchEngine(redis_client=None)`.
- The worker's research-job `llm_gateway` closure and `WebSearchTool` were removed (the other job's gateway is unrelated and untouched).
- Rollback tests were deleted rather than rewritten (the rollback kill-switch no longer exists); factory behaviour is covered by
  `tests/unit/integrations/research_engine/test_odr_engine_integration.py` (supported, 5 unsupported names, setting/env ignored).
- Constructor call sites in `test_checkpointer_and_reconciliation_scoping.py` and `test_odr_adapter_candidate_emission.py` updated.
