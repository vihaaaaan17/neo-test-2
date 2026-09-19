# 05: ODR Graph Wiring

**What to build:** The final integration step for Phase 1. Assemble the vendored ODR graph, inject the GPT Researcher tool into its execution node, and connect the fully constructed graph to the `OpenDeepResearchEngine` wrapper. This ensures the new engine can actually process a request end-to-end.

**Blocked by:** 03: Research Engine Protocol & Factory, 04: GPT-Researcher Tool Adapter.

**Status:** ready-for-agent

- [ ] Update the vendored ODR graph instantiation in `app/integrations/research_engine/engine.py` to include the GPT-Researcher tool in its standard toolset.
- [ ] Implement the `run` (or stream) method in `OpenDeepResearchEngine` so that it translates Neosis job parameters into ODR LangGraph inputs.
- [ ] Map ODR execution checkpoints to Redis, leaving canonical Postgres untouched.
- [ ] Run an integration smoke test to verify the factory can route a request to the new engine and the vendored graph executes successfully.
