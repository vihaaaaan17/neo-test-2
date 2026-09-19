# 03: Research Engine Protocol & Factory

**What to build:** Build the traffic routing logic that implements the migration strategy. This ensures that the existing `run_research_agent_job` can dynamically switch between the legacy prototype and the new ODR-based engine without downtime or rewriting the API layer, controlled by the flags from Ticket 01.

**Blocked by:** 01: Core Models & Feature Flags, 02: Upstream Vendoring & Dependencies.

**Status:** ready-for-agent

- [ ] Define `ResearchEngineProtocol` in `app/integrations/research_engine/engine.py` (analogous to `GroundEngineProtocol`).
- [ ] Create `app/services/research/factory.py` with a `get_research_engine` factory function.
- [ ] The factory must evaluate the global `ENABLE_ADVANCED_RESEARCH` flag and the `Workspace.research_engine` flag to return either the `ResearchModeOrchestrator` or a dummy initialized `OpenDeepResearchEngine`.
- [ ] Update `app/workers/tasks.py` to invoke the factory instead of hardcoding `ResearchModeOrchestrator`.
