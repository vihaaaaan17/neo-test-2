# ResearchModeOrchestrator

> 22 nodes · cohesion 0.15

## Key Concepts

- **ResearchModeOrchestrator** (16 connections) — `orchestration/research_mode.py`
- **ResearchContext** (8 connections) — `orchestration/research_mode.py`
- **ResearchState** (8 connections) — `orchestration/research_mode.py`
- **WebSearchTool** (6 connections) — `services/web_search.py`
- **.__init__()** (5 connections) — `orchestration/research_mode.py`
- **research_mode.py** (4 connections) — `orchestration/research_mode.py`
- **.run()** (4 connections) — `orchestration/research_mode.py`
- **UUID** (3 connections)
- **.astream_events()** (3 connections) — `orchestration/research_mode.py`
- **.executor_node()** (3 connections) — `orchestration/research_mode.py`
- **.executor_router()** (3 connections) — `orchestration/research_mode.py`
- **.planner_node()** (3 connections) — `orchestration/research_mode.py`
- **._build_graph()** (2 connections) — `orchestration/research_mode.py`
- **.reporter_node()** (2 connections) — `orchestration/research_mode.py`
- **.search()** (2 connections) — `services/web_search.py`
- **Any** (1 connections)
- **BaseModel** (1 connections)
- **deprecated** (1 connections)
- **TypedDict** (1 connections)
- **web_search.py** (1 connections) — `services/web_search.py`
- **Executes a search query and returns the results formatted as markdown.** (1 connections) — `services/web_search.py`
- **.__init__()** (1 connections) — `services/web_search.py`

## Relationships

- [run_research_agent_job](run_research_agent_job.md) (4 shared connections)
- [GroundModeOrchestrator](GroundModeOrchestrator.md) (3 shared connections)
- [LegacyResearchEngine](LegacyResearchEngine.md) (2 shared connections)

## Source Files

- `orchestration/research_mode.py`
- `services/web_search.py`

## Audit Trail

- EXTRACTED: 37 (84%)
- INFERRED: 7 (16%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*