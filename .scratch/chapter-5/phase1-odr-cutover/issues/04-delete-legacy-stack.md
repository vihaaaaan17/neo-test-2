# 04: Delete the Legacy Research Stack

**What to build:**
Remove the invented legacy research engine, its orchestrator and its search service, and sweep every test, script, UI
control and doc that referenced them.

**Blocked by:** 03

**Status:** done (2026-10-07)

- [x] Delete `app/integrations/research_engine/legacy.py`, `app/orchestration/research_mode.py`, `app/services/web_search.py`.
- [x] Tests that validate deleted code: delete `tests/unit/test_orchestrator_deprecation.py`; decide on `tests/test_research_agent.py`
      (keep only cases that still give useful ODR coverage, otherwise delete it) and record the decision in the PR description.
- [x] Mechanically replace `"legacy"` ORM fixture values with `"open_deep_research"` in:
      `tests/integration/chat/test_events.py`, `tests/integration/chat/test_turns.py`,
      `tests/integration/test_concurrency_and_failures.py`, `tests/integration/benchmark/test_failure_injection.py`,
      `tests/integration/benchmark/test_reliability.py`, `tests/test_async_sse.py`, `tests/test_workspaces.py`.
- [x] `scripts/benchmark_runner.py`: default `--engine` becomes `open_deep_research`, choices limited to `SUPPORTED_ENGINES`,
      remove mock `search_tool` plumbing and legacy execution, default `--output` becomes
      `tests/fixtures/benchmark/odr_baseline.json`; real-provider only.
- [x] Keep `tests/fixtures/benchmark/legacy_baseline.json` unchanged as immutable history; add
      `tests/fixtures/benchmark/README.md` stating it is obsolete (legacy engine removed in Chapter 5 Phase 1).
- [x] `ui/app.py`: remove the `legacy` option; show the engine as a fixed, read-only `open_deep_research` label (no new endpoint).
- [x] Update `docs/orchestrators.md`, `docs/architecture.md` and `README.md` where they describe the legacy orchestrator or
      `WebSearchTool`; leave `.scratch/` and historical chapter reports untouched.
- [x] Search for `ResearchModeOrchestrator`, `LegacyResearchEngine`, `WebSearchTool`, `planner_node`, `executor_node`,
      `synthesizer_node`, `reporter_node`, `research_engine="legacy"` across `app tests scripts ui`; the result must be empty.
- [x] Suite shows no new failures versus the ticket-01 baseline.

## Notes (2026-10-07, implemented together with 03 and 05)

- Deleted: `legacy.py`, `orchestration/research_mode.py`, `services/web_search.py`, `test_orchestrator_deprecation.py`, `tests/test_research_agent.py`
  (it only tested the deleted orchestrator; ODR coverage lives in `tests/unit/research` and `tests/unit/integrations`).
- `scripts/benchmark_runner.py` rewritten: ODR only (`--engine` from `SUPPORTED_ENGINES`), real provider, output default `odr_baseline.json`, mock tiers removed.
  `tests/fixtures/benchmark/README.md` marks `legacy_baseline.json` obsolete. Offline deterministic harness remains ticket 10.
- UI: engine shown as a fixed read-only field. Docs: `orchestrators.md`, `architecture.md`, `README.md`, `docs/README.md` updated.
- Fixture strings swept in `test_async_sse`, `test_workspaces`, `test_concurrency_and_failures`, `test_failure_injection`, `test_reliability`.
- Also fixed: `scripts/validate_migrations.py` live round-trip (alembic's `env.py` calls `asyncio.run`, which cannot nest in the script's running loop;
  the commands now run in a worker thread). Verified: upgrade, downgrade -1, upgrade on the dev DB.
