# 02: Integrate Router into Orchestrators

**What to build:** Both the `GroundModeOrchestrator` and `ResearchModeOrchestrator` are updated to route their fetched memory through the `MemoryRouterService` before assembling their LLM context, ensuring the LLM token window is never violated during deep research runs.

**Blocked by:** 01: Memory Router Service Foundation

**Status:** ready-for-agent

- [ ] Instantiate `MemoryRouterService` in `GroundModeOrchestrator`
- [ ] Update `GroundModeOrchestrator` prompt assembly to use `ContextBundle` from the router
- [ ] Instantiate `MemoryRouterService` in `ResearchModeOrchestrator`
- [ ] Update `ResearchModeOrchestrator` synthesizer node to use `ContextBundle` from the router
