# 11: ADR, Glossary, and Upstream Revision Documentation

**What to build:**
Record the Phase 1 decisions in the project docs. Documentation only; no behaviour changes.

**Blocked by:** 10

**Status:** done (2026-10-07)

- [x] `docs/adr/0005-odr-only-research-runtime.md`: ODR is the only research runtime; legacy engine, `WebSearchTool` and the custom
      retriever framework are removed; supersedes only the "GPT Researcher as capability retriever" clause of ADR 0002;
      ADR 0002's STORM deferral remains in force until a Phase 2 ADR. Status: Accepted.
- [x] `docs/CONTEXT.md`: add glossary entries — Research Engine, Engine Adapter, Supported Engines, Final Report event,
      Terminal State Owner — consistent with `.scratch/chapter-5/spec.md`.
- [x] `docs/UPSTREAM_REVISION.md`: add an Open Deep Research section: repository URL, full commit SHA of
      `references/open_deep_research`, acquisition date, and the list of Neosis patches to `deep_researcher.py` and `utils.py`
      (import paths, `function_calling` structured output, optional MCP imports, `neosis_web_search`, API-key lookup, error handling change).
- [x] `docs/chapter-3/PRODUCTION_CEILINGS.md`: note that `legacy_baseline.json` is historical and the legacy engine no longer exists.
- [x] Run the final dead-code search from `.scratch/chapter-5/verification-checklist.md`; paste the (empty) result in the PR.

## Notes (2026-10-07)

- Added `docs/adr/0005-odr-only-research-runtime.md`, five glossary entries in `docs/CONTEXT.md`, an Open Deep Research section in
  `docs/UPSTREAM_REVISION.md` (SHA `1b7d2e80db9faa586165c60e09096dbbfd483a64`, patch list), and a historical note in `docs/chapter-3/PRODUCTION_CEILINGS.md`.
- Dead-code gate over `app tests scripts ui streamlit_app.py`: no hits.
