# UsageTracker

> 12 nodes · cohesion 0.23

## Key Concepts

- **UsageTracker** (19 connections) — `integrations/research_engine/budget.py`
- **ResearchBudgetExceeded** (5 connections) — `integrations/research_engine/budget.py`
- **.check_budget()** (4 connections) — `integrations/research_engine/budget.py`
- **research_engine/budget.py** (3 connections) — `integrations/research_engine/budget.py`
- **.add_search_call()** (3 connections) — `integrations/research_engine/budget.py`
- **.add_model_usage()** (2 connections) — `integrations/research_engine/budget.py`
- **.track_search_call()** (2 connections) — `integrations/research_engine/budget.py`
- **Exception** (1 connections)
- **Raised when an execution exceeds its allocated budget.** (1 connections) — `integrations/research_engine/budget.py`
- **.get_usage_metrics()** (1 connections) — `integrations/research_engine/budget.py`
- **.__init__()** (1 connections) — `integrations/research_engine/budget.py`
- **.track_error()** (1 connections) — `integrations/research_engine/budget.py`

## Relationships

- [OpenDeepResearchEngine](OpenDeepResearchEngine.md) (5 shared connections)
- [GPTResearcherRetriever](GPTResearcherRetriever.md) (2 shared connections)
- [MCPRetriever](MCPRetriever.md) (2 shared connections)
- [WebRetriever](WebRetriever.md) (2 shared connections)
- [ResearchNormalizationService](ResearchNormalizationService.md) (1 shared connections)
- [ResearchSourceResult](ResearchSourceResult.md) (1 shared connections)

## Source Files

- `integrations/research_engine/budget.py`

## Audit Trail

- EXTRACTED: 17 (61%)
- INFERRED: 11 (39%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*