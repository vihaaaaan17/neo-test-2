# 01: Central Engine Factory and Legacy Adapter

**What to build:** 
Unify the execution path by introducing a `ResearchEngine` interface and a `ResearchEngineFactory`. The factory resolves which engine to use (e.g., ODR vs Legacy) based on the `ResearchRun.engine` field. We also need a `LegacyResearchEngine` adapter that wraps the existing `ResearchModeOrchestrator` to implement this new interface. Finally, update the `app/workers/tasks.py` to use the factory and execute the engine, preserving the legacy behavior as the fallback.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] Create `app/integrations/research_engine/engine.py` with an abstract `ResearchEngine` class.
- [x] Create `app/integrations/research_engine/factory.py` to resolve engines.
- [x] Create `LegacyResearchEngine` adapter that wraps `ResearchModeOrchestrator` to fit the `ResearchEngine` interface.
- [x] Update `app/workers/tasks.py` (specifically `run_research_agent_job`) to fetch the engine via the factory instead of directly instantiating the `ResearchModeOrchestrator`.
