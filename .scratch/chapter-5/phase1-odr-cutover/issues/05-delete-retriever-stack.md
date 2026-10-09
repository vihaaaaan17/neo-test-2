# 05: Delete the Custom Retriever Framework and GPT-Researcher Bridge

**What to build:**
Remove the custom retriever package and the GPT-Researcher retriever/tool bridge. ODR keeps its own upstream tool assembly;
`neosis_web_search` stays as the evidence-interception bridge. Do not move these classes elsewhere or replace them with
another registry.

**Blocked by:** 03 (04 is independent; either order works)

**Status:** done (2026-10-07)

- [x] Delete `app/services/research/retrievers/` (`base.py`, `registry.py`, `web.py`, `academic.py`, `mcp.py`,
      `gpt_researcher.py`, `__init__.py`).
- [x] Delete `app/integrations/research_engine/tools/gpt_researcher_tool.py`.
- [x] Remove the commented-out `GPTResearcherTool` block from `get_all_tools` in
      `app/integrations/research_engine/upstream/open_deep_research/utils.py` (do not reintroduce it as a tool).
- [x] Delete `tests/unit/services/research/test_retrievers.py` and `tests/unit/integrations/research_engine/test_gpt_researcher_tool.py`.
- [x] Check `app/services/research/budget.py` and `app/services/research/metrics.py` still import cleanly
      (`UsageTracker` is shared with `integrations/research_engine/budget.py`; keep it).
- [x] Add or keep a unit test proving `neosis_web_search` still records evidence and usage (this replaces the deleted
      retriever coverage for supported behaviour).
- [x] Search for `RetrieverRegistry`, `WebRetriever`, `AcademicRetriever`, `MCPRetriever`, `GPTResearcherRetriever`,
      `GPTResearcherTool`, `services.research.retrievers` across `app tests scripts ui`; the result must be empty.
- [x] Leave `gpt-researcher` / `knowledge-storm` in `requirements.txt` and `STORM_ENABLED` in config untouched.
- [x] Suite shows no new failures versus the ticket-01 baseline.

## Notes (2026-10-07, implemented together with 03 and 04)

- Deleted the whole `app/services/research/retrievers/` package, `tools/gpt_researcher_tool.py`, the commented `GPTResearcherTool` block in `utils.py`,
  and the two test files for them. `UsageTracker` (shared) and `neosis_web_search` are untouched.
- Dead-code search over `app tests scripts ui streamlit_app.py` for the plan's symbol list returns no hits.
