# 02: Upstream Vendoring & Dependencies

**What to build:** Secure the integration seam by pulling in upstream code. Instead of relying on brittle pip patching for Open Deep Research (ODR), vendor its source code into the Neosis codebase to allow precise LangGraph edge interception in Phase 2. Also add the necessary pip dependencies for STORM and GPT Researcher.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Add `gpt-researcher` and `knowledge-storm` to the project's dependency manager (`requirements.txt` or `pyproject.toml`).
- [ ] Create directory `app/integrations/research_engine/upstream/open_deep_research/`.
- [ ] Copy the core source code of `open_deep_research` from `references/` into the new vendored directory.
- [ ] Resolve any local import path issues within the vendored ODR code to ensure it runs correctly within the Neosis environment.
