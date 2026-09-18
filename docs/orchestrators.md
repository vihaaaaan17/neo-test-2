# Agents & Orchestrators

NeosisLM uses **LangGraph** to build highly reliable, cyclic, and stateful agent systems. Rather than simple linear chains, our agents operate in feedback loops capable of autonomous error correction.

## The Two Orchestrators

### 1. `ResearchModeOrchestrator`
This orchestrator executes "Open Deep Research". It acts autonomously to solve complex tasks by browsing the web.

**The State Machine**:
- **Planner Node**: Breaks the user's objective down into a `ResearchContext` plan containing sequential search tasks.
- **Executor Node**: Pulls the next task from the plan and uses `Tavily` (via `WebSearchTool`) to scrape the internet. Updates internal memory.
- **Synthesizer Node**: Evaluates the gathered evidence. If the evidence is insufficient, it sends the state *back* to the Executor for more searching. If sufficient, it maps the data into an `OutputGraph` (nodes and edges).
- **Reporter Node**: Converts the semantic graph into a human-readable markdown response.

### 2. `GroundModeOrchestrator`
This orchestrator implements strict "NotebookLM-style" internal Question-Answering. 

**Behavior**:
- It completely lacks access to the internet. 
- It relies entirely on the `HybridRetrievalService` (combining semantic vector search and keyword match) to find knowledge from the user's Workspace files.
- It strictly enforces grounding. If it cannot find evidence in the internal documents, it gracefully rejects the prompt rather than hallucinating.

## Shared Memory Fabric
Both orchestrators write to the exact same canonical database and memory routers. A fact discovered by the `ResearchModeOrchestrator` on the web is permanently stored, allowing the `GroundModeOrchestrator` to instantly reference it in future Q&A sessions.
