# 03: GPT-Researcher Adapter

**What to build:**
`GPTResearcherEngine` that instantiates the upstream `GPTResearcher` runtime through its supported API and maps its output to the
Neosis engine contract. Replaces the (deleted in Phase 1) retriever and tool bridges.

**Blocked by:** 01

**Status:** done (2026-10-07)

- [x] `app/integrations/research_engine/gpt_researcher/engine.py` implementing `ResearchEngine`.
- [x] Pass the canonical objective and allowed inputs; let GPT-Researcher run its own planning, research, crawl and report workflow.
- [x] Collect upstream sources and the report; normalize sources into Neosis evidence persistence; yield one `final_report`.
- [x] Configure via GPT-Researcher's supported configuration mechanism; avoid environment mutation and monkey-patching
      (a narrow provider-compatibility boundary only if proven necessary, documented in the PR).
- [x] Do not build a second planner around it.
- [x] Contract tests in `tests/unit/integrations/research_engine/test_gpt_researcher_engine_integration.py`.

## Notes (2026-10-07)

- Implemented: `gpt_researcher/engine.py` (`GPTResearcherEngine`): models via GPT-Researcher's JSON `config_path` (key/base URL come from the env `app.core.config` already exports; the adapter writes no environment),
  `log_handler` -> progress events, sources -> Neosis evidence, cost -> usage, failures raised. `gpt-researcher` 0.15.1 installed in the main venv (see `upstream-api-notes.md` for side effects).
- Verified: 6 contract tests with a fake `GPTResearcher` (progress, one `final_report`, config/no env mutation, failures raised, cancellation stops the upstream task, source normalisation).
- Verified live against the real GPT-Researcher + configured provider + Tavily: one `final_report` (4,126 chars, ~378s on the free model), 12 evidence rows all with provenance URLs, 1 usage row.
- Bugs found and fixed: (1) `asyncio.wait_for` in the progress loop swallowed task cancellation on Python 3.11 (the adapter kept running after cancel) -> replaced with `asyncio.wait`;
  (2) the live run showed GPT-Researcher calls `on_agent_action(action, **kwargs)` with the name both positional and keyword -> handler signatures accept both (the test fake now mirrors that call shape);
  (3) a duplicate URL overwrote the first source instead of being skipped.
- Limits: no Neosis research context / prior evidence input; embeddings go through the configured OpenAI-compatible endpoint (`EMBEDDING_MODEL`), which may be rate-limited on the free gateway.
