# 09: Single LLM Provider Resolution Path

**What to build:**
One `resolve_llm_provider()` replaces the duplicated provider/env logic in `config.py`, `app/api/deps/llm.py`,
`app/workers/settings.py::_real_llm_call` and the ODR engine. The engine stops mutating `os.environ`.

**Blocked by:** 08

**Status:** done (2026-10-07)

- [x] Add `resolve_llm_provider()` in `app/core/config.py` returning the active provider's API key, base URL and model
      (OpenAI-compatible or NVIDIA, following the existing `LLM_PROVIDER` / key fallback rules). It is the only function that
      reads provider keys/URLs/models.
- [x] `config.py`'s import-time block that exports `OPENAI_*`/`NVIDIA_*`/`TAVILY_API_KEY` to `os.environ` uses it
      (ODR's upstream model construction still reads these env vars, so the export stays — in one place).
- [x] `app/api/deps/llm.py` (`llm_call`, `embed_call`) and `app/workers/settings.py::_real_llm_call` call it instead of
      re-implementing the rules.
- [x] `OpenDeepResearchEngine.astream_events` removes its provider/env block and builds `model_id` from `resolve_llm_provider()`;
      it performs no `os.environ` writes.
- [x] Usage checkpointing in the engine is unchanged.
- [x] Unit tests: OpenAI-compatible provider, NVIDIA provider, NVIDIA fallback when only `NVIDIA_API_KEY` is set,
      missing-key error; engine run does not modify `os.environ`.
- [x] Suite shows no new failures versus the ticket-01 baseline.

## Notes (2026-10-07, implemented together with 10 and 11)

- `resolve_llm_provider(cfg=None, require_key=False) -> LLMProvider(name, api_key, base_url, model)` in `app/core/config.py`; reads `Settings`
  (not ad-hoc `os.environ`), applies the NVIDIA fallback and strips `/chat/completions`. The import-time env export now uses it and is the only env writer.
- `api/deps/llm.py` (`llm_call`, `embed_call`) and `workers/settings.py::_real_llm_call` use it with `require_key=True`; `_real_llm_call` keeps its
  `model`/`provider` parameters for caller compatibility but the configured provider decides (same effective behaviour as before).
- `OpenDeepResearchEngine` builds `model_id` and `apiKeys` from it and no longer writes `os.environ`. Tests: `tests/unit/test_llm_provider.py` (6).
