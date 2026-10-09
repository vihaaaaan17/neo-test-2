# 02: STORM Adapter

**What to build:**
`StormResearchEngine` that calls the real `knowledge_storm` runtime and maps its output to the Neosis engine contract.

**Blocked by:** 01

**Status:** done (2026-10-07)

- [x] `app/integrations/research_engine/storm/engine.py` implementing `ResearchEngine`.
- [x] Map Neosis objective/context to STORM inputs; supply provider/credentials via `resolve_llm_provider()` and STORM's own configuration.
- [x] Invoke the upstream runtime (running blocking calls off the event loop if the API is sync); translate progress into Neosis progress events;
      yield one `final_report`; raise on failure; implement `cancel()` only if upstream supports it.
- [x] Route sources/citations into Neosis evidence persistence so provenance is retained; do not write reports/candidates in the adapter.
- [x] Do not reimplement question decomposition, perspective generation, multi-pass research, citation gathering, drafting or synthesis.
- [x] Contract tests in `tests/unit/integrations/research_engine/test_storm_engine_integration.py`.

## Notes (2026-10-07)

- Implemented: `storm/engine.py` (`StormResearchEngine`), `storm/runner.py` (runs in the isolated `venv-storm`, calls the real `STORMWikiRunner`; stdout line protocol), shared
  `integrations/research_engine/evidence.py`, `STORM_PYTHON` setting, `requirements-storm.txt`. STORM cannot share the main environment (dspy_ai 2.4.9 -> openai<2.0.0), hence the subprocess.
- Verified: 9 contract tests with a stand-in runner (progress, one `final_report`, objective/provider/credentials reach the runner, failure and no-result raise, cancellation terminates the process,
  missing environment message, UTF-8 mode, source formatting, topic sanitising).
- Verified live against the real STORM runtime + configured provider + Tavily (small settings: 1 turn, 1-2 perspectives): one `final_report` (10,680 chars, ~93s), 11 evidence rows all with provenance URLs, 1 usage row.
- Live run found two real upstream-on-Windows problems, fixed in the adapter without touching STORM: (1) STORM uses the topic text as a directory name, so `?` crashed it -> the runner strips invalid file-name characters;
  (2) STORM writes files in cp1252 and reads them as UTF-8 -> the subprocess runs in Python UTF-8 mode (`PYTHONUTF8=1`).
- Limits: STORM accepts only a topic (no Neosis research context / prior evidence); no budget enforcement mid-run (usage is recorded afterwards); first run downloads a sentence-transformers model.
