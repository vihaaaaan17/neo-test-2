# Upstream Revision

This file documents the pinned version of the Open Notebook implementation used as the Ground Engine runtime for NeosisLM. 

## Source Information
- **Repository URL:** https://github.com/lfnovo/open-notebook (inferred from references/open-notebook)
- **Git Reference:** `v1.14.0` (Git Tag)
- **Git SHA:** `30c7e2a63e43b7f270fc2c638f0b6246934a53f4`

## Docker Runtime
- **Docker Image Tag:** `lfnovo/open_notebook:1.14.0`
- **Docker Image Digest:** `lfnovo/open_notebook@sha256:e53f90d6153fcf4a64604d9a0c12cb0428a32cfb8dbcbb72e81ab12c013ee330`
- **Acquisition Date:** 2026-09-18

## Integration Notes
- Phase 1 integration uses HTTP API boundary (`:5055`) to the isolated Docker container.
- *Note:* The user spec originally stated the image tag was `v1.14.0`, but Docker Hub only publishes `1.14.0`. We have adopted `1.14.0` to match the actual published image for the `v1.14.0` git tag release.

---

# Open Deep Research (Research Engine)

The pinned version of Open Deep Research used as the only Research Engine runtime (see ADR 0005).

## Source Information
- **Repository URL:** https://github.com/langchain-ai/open_deep_research
- **Git SHA:** `1b7d2e80db9faa586165c60e09096dbbfd483a64` (checkout in `references/open_deep_research`, commit dated 2026-08-10)
- **Vendored at:** `app/integrations/research_engine/upstream/open_deep_research/` (copied from the reference's `src/open_deep_research/`)
- **Acquisition Date:** 2026-09 (Chapter 3); revision recorded 2026-10-07

## Unmodified files
`prompts.py`, `state.py` and `configuration.py` are byte-identical to the reference.

## Neosis patches (keep minimal; re-apply on upgrade)
- `deep_researcher.py`
  - imports rewritten to the vendored package path;
  - `with_structured_output(..., method="function_calling")` for `ClarifyWithUser` and `ResearchQuestion` so OpenAI-compatible gateways work;
  - removed an upstream `or True` that ended the research phase on any supervisor error (now only on token-limit errors).
- `utils.py`
  - imports rewritten to the vendored package path;
  - `langchain_mcp_adapters` / `mcp` imports made optional;
  - `with_structured_output(Summary, method="function_calling")` for webpage summarization;
  - Tavily search tool replaced by the evidence-capturing `neosis_web_search` (`app/integrations/research_engine/tools/neosis_search_tools.py`);
  - API-key lookup falls back to the configured OpenAI/NVIDIA/Tavily keys instead of requiring `GET_API_KEYS_FROM_CONFIG`.

---

# STORM (Research Engine)

Selectable engine (see ADR 0006). Runs unmodified in its own virtual environment; Neosis only calls its public runtime API.

## Source Information
- **Repository URL:** https://github.com/stanford-oval/storm
- **Package:** `knowledge-storm==1.1.1` (installed only in `venv-storm`, see `requirements-storm.txt`)
- **Git SHA:** `fb951af7744dab086e34962e9bc6fe878e145f83` (checkout in `references/storm`, commit dated 2025-09-30)
- **Adapter:** `app/integrations/research_engine/storm/` (`engine.py` adapter, `runner.py` executed inside `venv-storm`)

## Neosis patches
None. Windows quirks are handled outside upstream: the subprocess runs with `PYTHONUTF8=1`, and the runner strips file-name-invalid
characters from the topic before handing it to STORM.

---

# GPT-Researcher (Research Engine)

Selectable engine (see ADR 0006). Used in-process through its public `GPTResearcher` API; not vendored.

## Source Information
- **Repository URL:** https://github.com/assafelovic/gpt-researcher
- **Package:** `gpt-researcher==0.15.1` (main `venv`, see `requirements.txt`)
- **Git SHA:** `6f998577d547b1e54ec662dac63583aa11e3b84b` (checkout in `references/gpt-researcher`, commit dated 2026-08-23)
- **Adapter:** `app/integrations/research_engine/gpt_researcher/engine.py`

## Neosis patches
None. Models are set through GPT-Researcher's JSON config file; the API key and base URL come from `OPENAI_API_KEY` /
`OPENAI_BASE_URL`, exported once by `app.core.config`.
