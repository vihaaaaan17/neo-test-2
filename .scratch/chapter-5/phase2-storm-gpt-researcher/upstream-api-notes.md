# Upstream API notes (ticket 01, 2026-10-07)

## Versions
- `knowledge-storm` 1.1.1 (reference checkout `references/storm` @ fb951af, 2025-09-30). Installed ONLY in `venv-storm` (see below).
- `gpt-researcher` 0.15.1 (reference checkout @ 6f99857, 2026-08-23). Installed in the main `venv`.

## Critical finding: STORM cannot share the main environment
`knowledge-storm` pins `dspy_ai==2.4.9`, which requires `openai<2.0.0` (and `datasets<3`). The app needs `openai>=2.45` (`langchain-openai` 1.x, used by ODR).
A dry run showed installing it would downgrade openai 2.54 -> 1.109 and break ODR. Both packages were also listed in `requirements.txt` but neither was installed.
Decision: STORM runs in a separate virtualenv (`venv-storm`, `requirements-storm.txt`); the adapter starts `storm/runner.py` there as a subprocess.
Verified: `import knowledge_storm` works in `venv-storm`; `pip check` is clean there.

## GPT-Researcher install side effects (main venv)
Installed with `boto3/botocore/s3transfer/aiobotocore` held as constraints (otherwise pip upgrades botocore and breaks S3, as happened earlier).
Side effects: `numpy` 2.4.6 -> 2.2.6, `litellm` 1.101.0 -> 1.97.0, +84 packages (spacy, unstructured, mcp 2.3, langchain-community ...).
`wrapt` was pulled to 2.5, which breaks `aiobotocore` (needs `<2`); pinned back to 1.17.3. Remaining metadata conflict: `unstructured 0.27.16` declares `wrapt>=2.1.1`.
First import after install is slow (~60s of bytecode compilation); later ~15s.

## STORM public runtime API (from source)
- Entry point: `STORMWikiRunner(STORMWikiRunnerArguments(output_dir, max_conv_turn, max_perspective, search_top_k, retrieve_top_k, max_thread_num, ...), STORMWikiLMConfigs, rm).run(topic, do_research, do_generate_outline, do_generate_article, do_polish_article, callback_handler)`. Synchronous/blocking.
- LLM: five slots (`conv_simulator_lm`, `question_asker_lm`, `outline_gen_lm`, `article_gen_lm`, `article_polish_lm`), set with `LitellmModel(model="openai/<name>", api_key=..., api_base=..., max_tokens=...)` -> works with OpenAI-compatible endpoints.
- Retrieval: `TavilySearchRM(tavily_search_api_key, k, include_raw_content)` (also You/Bing/Serper/Brave/DuckDuckGo/... classes).
- Progress: `BaseCallbackHandler` hooks (`on_identify_perspective_*`, `on_information_gathering_*`, `on_dialogue_turn_end`, `on_information_organization_start`, `on_*_outline_*`).
- Output: files under `<output_dir>/<topic>/`: `storm_gen_article_polished.txt` (cites `[n]`), `url_to_info.json` (`url_to_unified_index` + per-URL title/description/snippets), `conversation_log.json`, `raw_search_results.json`. LM usage: `LitellmModel.get_usage_and_reset()`, `lm.history`.
- Cancellation: none upstream -> the adapter terminates the subprocess.
- Local ranking uses a sentence-transformers model downloaded from HuggingFace on first run. `Encoder` (needs `ENCODER_API_TYPE`) is Co-STORM only.
- Input: only a topic. No input for Neosis research context / prior evidence (not passed).

## GPT-Researcher public runtime API (from source)
- `GPTResearcher(query, report_type="research_report", report_source="web", config_path=..., log_handler=..., verbose=...)`; `await conduct_research()`; `await write_report()`; `get_research_sources()`, `get_source_urls()`, `get_costs()`. Async-native.
- Configuration: JSON `config_path` (keys `SMART_LLM`, `FAST_LLM`, `STRATEGIC_LLM`, `RETRIEVER`, `EMBEDDING`, ...; env vars override file values). The `openai` provider reads `OPENAI_API_KEY` / `OPENAI_BASE_URL` from the environment, which `app.core.config` already exports.
- Progress: `log_handler` object with async `on_tool_start`, `on_agent_action`, `on_research_step`.
- Cancellation: none upstream -> cancelling the consuming task cancels the awaiting upstream coroutines.
- Input: a query (no Neosis context input; not passed).

## Open questions for the user
1. STORM isolation (subprocess + `venv-storm`) is a deviation from "just import it"; acceptable? Alternative: drop STORM.
2. Embeddings: GPT-Researcher needs an embeddings endpoint (`EMBEDDING`); the freellmapi gateway's embeddings were rate-limited by Google earlier. Use a local embedding provider if that persists.
3. `wrapt` metadata conflict (`unstructured` vs `aiobotocore`) is left unresolved.
