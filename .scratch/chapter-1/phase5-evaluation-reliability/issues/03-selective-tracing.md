# 03: Selective LangSmith Tracing

**What to build:** The orchestrators are configured to emit LangSmith traces using LangChain callbacks, while the background `arq` workers (like parsing and graph projection) are explicitly sandboxed to prevent them from leaking noisy operational data into the evaluation datasets.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Add LangChain tracing callbacks/configuration to `GroundModeOrchestrator` execution
- [ ] Add LangChain tracing callbacks/configuration to `ResearchModeOrchestrator` execution
- [ ] Ensure background tasks (`app/workers/tasks.py`) unset `LANGCHAIN_TRACING_V2` or explicitly bypass tracing
