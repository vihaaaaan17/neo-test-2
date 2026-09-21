# 02: ODR Adapter Skeleton and Event Normalization

**What to build:** 
Create the `OpenDeepResearchEngine` adapter that implements the `ResearchEngine` interface. It should translate a canonical `ResearchRun` to an ODR configuration/request. It must also capture ODR's internal events (e.g. from LangGraph stream) and normalize them into `ResearchEvent` schemas to be yielded back to the outer loop for persistence and Redis broadcasting.

**Blocked by:** 01: Central Engine Factory and Legacy Adapter

**Status:** ready-for-agent

- [x] Create `app/integrations/research_engine/open_deep_research/engine.py`.
- [x] Implement adapter logic to initialize the ODR graph state from the `ResearchRun`.
- [x] Implement an async event generator that consumes ODR's stream and yields `ResearchEvent` DTOs.
- [x] Register `open_deep_research` inside `ResearchEngineFactory`.
