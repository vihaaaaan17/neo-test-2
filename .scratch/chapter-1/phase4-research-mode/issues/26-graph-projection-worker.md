# 26: Asynchronous Output KG Projection

**What to build:** The final persistence step of the research run. Takes the synthesized Curated Graph from the agent's memory and permanently saves it into Neo4j so the user can load it later.

**Blocked by:** 24, 25

**Status:** ready-for-agent

- [ ] Create an `arq` background task `project_output_graph_job` in `app/workers/tasks.py`.
- [ ] Hook this job to automatically enqueue when the `ResearchModeOrchestrator` finishes its run successfully.
- [ ] The job must read the `OutputGraphNode` and `OutputGraphEdge` arrays from the final LangGraph state.
- [ ] Execute `GraphRepository` to physically write the deep provenance graph into the Neo4j instance.
- [ ] Implement basic idempotency (if the job retries, it should safely merge/overwrite the graph nodes instead of duplicating them).
