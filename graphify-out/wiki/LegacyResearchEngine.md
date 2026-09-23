# LegacyResearchEngine

> 33 nodes · cohesion 0.08

## Key Concepts

- **LegacyResearchEngine** (10 connections) — `integrations/research_engine/legacy.py`
- **ResearchEngine** (8 connections) — `integrations/research_engine/engine.py`
- **ResearchEngineFactory** (7 connections) — `integrations/research_engine/factory.py`
- **.get_engine()** (7 connections) — `integrations/research_engine/factory.py`
- **ResearchEngineSetupError** (5 connections) — `integrations/research_engine/exceptions.py`
- **ResearchExecutionError** (5 connections) — `integrations/research_engine/exceptions.py`
- **.astream_events()** (4 connections) — `integrations/research_engine/engine.py`
- **.astream_events()** (4 connections) — `integrations/research_engine/legacy.py`
- **research_engine/engine.py** (3 connections) — `integrations/research_engine/engine.py`
- **exceptions.py** (3 connections) — `integrations/research_engine/exceptions.py`
- **TokenLimitExceededError** (3 connections) — `integrations/research_engine/exceptions.py`
- **.__init__()** (3 connections) — `integrations/research_engine/legacy.py`
- **UUID** (2 connections)
- **.cancel()** (2 connections) — `integrations/research_engine/engine.py`
- **legacy.py** (2 connections) — `integrations/research_engine/legacy.py`
- **.cancel()** (2 connections) — `integrations/research_engine/legacy.py`
- **Any** (2 connections)
- **UUID** (2 connections)
- **Any** (1 connections)
- **Stream execution events from the research engine. Args: run_id: The canonical…** (1 connections) — `integrations/research_engine/engine.py`
- **Trigger cooperative cancellation of the running execution.** (1 connections) — `integrations/research_engine/engine.py`
- **Abstract interface for all research engines in Neosis.** (1 connections) — `integrations/research_engine/engine.py`
- **Exception** (1 connections)
- **Raised when token limits are exceeded.** (1 connections) — `integrations/research_engine/exceptions.py`
- **Base class for research execution errors.** (1 connections) — `integrations/research_engine/exceptions.py`
- *... and 8 more nodes in this community*

## Relationships

- [OpenDeepResearchEngine](OpenDeepResearchEngine.md) (2 shared connections)
- [run_research_agent_job](run_research_agent_job.md) (2 shared connections)
- [ResearchModeOrchestrator](ResearchModeOrchestrator.md) (2 shared connections)
- [BaseRetriever](BaseRetriever.md) (1 shared connections)

## Source Files

- `integrations/research_engine/engine.py`
- `integrations/research_engine/exceptions.py`
- `integrations/research_engine/factory.py`
- `integrations/research_engine/legacy.py`

## Audit Trail

- EXTRACTED: 39 (81%)
- INFERRED: 9 (19%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*