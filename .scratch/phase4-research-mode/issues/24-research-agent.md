# 24: Autonomous Research Agent (STORM adaptation)

**What to build:** The core autonomous LLM loop. Given a broad research objective, the agent will autonomously plan a search strategy, execute web searches, synthesize the findings, and format the output as a Curated Graph with deep provenance links.

**Blocked by:** 22, 23

**Status:** ready-for-agent

- [ ] Implement `WebSearchTool` class using the `Tavily` API client (`tavily-python`), returning markdown/structured answers.
- [ ] Build `ResearchModeOrchestrator` using a LangGraph `StateGraph` that manages `ResearchState` and `PlanState`.
- [ ] Implement the planning node, which breaks the user's objective into smaller search tasks.
- [ ] Implement the execution loop, which calls the `WebSearchTool` and gathers evidence.
- [ ] Implement the synthesis node, which converts the gathered evidence into structured `OutputGraphNode` and `OutputGraphEdge` arrays (including `ProvenanceBundles`).
- [ ] Validate the graph structure natively matches the schemas created in Ticket 23.
