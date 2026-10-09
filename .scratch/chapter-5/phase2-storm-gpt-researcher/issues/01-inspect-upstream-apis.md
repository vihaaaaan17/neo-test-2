# 01: Inspect the Installed STORM and GPT-Researcher APIs

**What to build:**
A short, factual note on the public runtime APIs of the installed `knowledge-storm` and `gpt-researcher` packages, so the adapters
are written against the real API. No application code.

**Blocked by:** Phase 1 complete

**Status:** done (2026-10-07)

- [x] Record installed versions (and `references/storm`, `references/gpt-researcher` commits) in
      `.scratch/chapter-5/phase2-storm-gpt-researcher/upstream-api-notes.md`.
- [x] For each package: the entry point to run a full research/report job, required configuration (LLM, retriever/search, keys),
      what it returns (report, sources/citations), what progress/events or callbacks it exposes, async vs sync, and whether it
      supports cancellation.
- [x] Note how each package selects its LLM and search provider and whether freellmapi/OpenAI-compatible endpoints work through
      its supported configuration (no monkey-patching).
- [x] List open questions that need a user decision (e.g. which retriever STORM should use) before tickets 02 and 03 start.

## Notes (2026-10-07)
Done. Findings are in `../upstream-api-notes.md`. Headline: STORM cannot be installed into the main environment (dspy_ai 2.4.9 -> openai<2.0.0), so it runs in an isolated `venv-storm`; both packages were in requirements.txt but not installed.
