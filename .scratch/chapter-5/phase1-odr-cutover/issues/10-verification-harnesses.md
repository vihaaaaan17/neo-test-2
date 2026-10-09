# 10: Offline Deterministic Harness and Real-Provider ODR Smoke Gate

**What to build:**
Two verification tools: a deterministic offline harness (no test-only hooks in production code) and the opt-in
real-provider smoke test that gates Phase 1.

**Blocked by:** 08, 09

**Status:** done (2026-10-07)

- [x] Offline harness under `tests/` (e.g. `tests/harness/odr_offline.py` + fixture): patches ODR's model construction and
      `neosis_web_search` to return deterministic responses; drives `OpenDeepResearchEngine` over `tests/fixtures/benchmark/corpus.jsonl`
      entries; asserts the engine contract (progress events, one `final_report`, failures raise) and that evidence is recorded.
- [x] `tests/smoke/test_odr_real_provider.py`, marked `real_provider`, skipped unless explicitly enabled
      (e.g. `RUN_REAL_PROVIDER_SMOKE=1`); uses the configured provider (`resolve_llm_provider()`) and Tavily. Register the
      marker in `pytest.ini`.
- [x] The smoke test asserts: a ResearchRun is created with `engine == "open_deep_research"` and completes; events reach the
      canonical event stream; evidence rows carry provenance; a final report is persisted; a mid-run cancellation ends in a terminal
      state (no stuck `running` run); Ground answers on the same workspace do not cite research-derived sources; engine selection is
      deterministic (unsupported engine → 422); exactly one terminal run state and no duplicate terminal event on `research_events:{run_id}`.
      Report quality is not asserted.
- [x] Document how to run it (`RUN_REAL_PROVIDER_SMOKE=1 pytest tests/smoke -m real_provider`) in `docs/setup.md`.
- [x] Run it once against the live stack and attach the result to the PR; Phase 1 is not complete without a passing run.

## Notes (2026-10-07)

- Offline harness `tests/harness/odr_offline.py`: fakes ODR's `configurable_model` (structured output, supervisor/researcher tool calls,
  compression, final report) and the Tavily client inside the real `neosis_web_search`; runs the real vendored graph. 20 corpus items in ~2s
  (`tests/unit/integrations/research_engine/test_odr_offline_harness.py`). No production hooks.
- Smoke gate `tests/smoke/test_odr_real_provider.py` (`real_provider` marker registered in `pytest.ini`; skipped unless `RUN_REAL_PROVIDER_SMOKE=1`).
  The evidence check is tied to recorded search calls: a first live run made 0 searches (the free `auto` model answered from its own knowledge),
  so "no evidence" is only a failure when searches happened; the prompt asks for web sources.
- Live result 2026-10-07: **passed** (62s) - completed run with 1 search call, 8 evidence rows with provenance, 1 report, one `pending_review`
  memory candidate, single `completed` terminal event; cancelled run ended `cancelled` with no report and one `turn.cancelled` + `done`.
- `docs/setup.md` documents the suite, the harness and the smoke command.
