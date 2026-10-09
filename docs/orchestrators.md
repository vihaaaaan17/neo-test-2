# Agents & Orchestrators

NeosisLM uses **LangGraph** to build highly reliable, cyclic, and stateful agent systems. Rather than simple linear chains, our agents operate in feedback loops capable of autonomous error correction.

## Research and Ground Execution

### 1. Research Mode (Open Deep Research)
Research Mode runs the upstream **Open Deep Research** (ODR) LangGraph through the `OpenDeepResearchEngine` adapter
(`app/integrations/research_engine/open_deep_research/engine.py`). Neosis does not implement its own planner, executor or
synthesizer: ODR owns planning, task decomposition, the search loop (Tavily, via the evidence-capturing `neosis_web_search`
tool), reflection and report generation. The adapter only builds the ODR runtime config, injects the bounded Neosis research
context, and translates upstream execution signals into Neosis events. The worker owns persistence and run state.

### 2. Legacy `GroundModeOrchestrator` (deprecated)
This orchestrator implements strict "NotebookLM-style" internal Question-Answering. 

**Behavior**:
- It completely lacks access to the internet. 
- It relies entirely on the `HybridRetrievalService` (combining semantic vector search and keyword match) to find knowledge from the user's Workspace files.
- It strictly enforces grounding. If it cannot find evidence in the internal documents, it gracefully rejects the prompt rather than hallucinating.

## Shared Memory Fabric
Both modes write to the exact same canonical database and memory routers. A fact discovered by Research Mode on the web is permanently stored, allowing the `GroundModeOrchestrator` to instantly reference it in future Q&A sessions.
