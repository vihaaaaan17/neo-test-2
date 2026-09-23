# OpenDeepResearchEngine

> 17 nodes · cohesion 0.14

## Key Concepts

- **OpenDeepResearchEngine** (10 connections) — `integrations/research_engine/open_deep_research/engine.py`
- **BudgetEnforcingCallbackHandler** (7 connections) — `integrations/research_engine/budget.py`
- **.astream_events()** (7 connections) — `integrations/research_engine/open_deep_research/engine.py`
- **.on_llm_end()** (3 connections) — `integrations/research_engine/budget.py`
- **.__init__()** (2 connections) — `integrations/research_engine/budget.py`
- **open_deep_research/engine.py** (2 connections) — `integrations/research_engine/open_deep_research/engine.py`
- **.cancel()** (2 connections) — `integrations/research_engine/open_deep_research/engine.py`
- **.__init__()** (2 connections) — `integrations/research_engine/open_deep_research/engine.py`
- **Any** (2 connections)
- **UUID** (2 connections)
- **AsyncCallbackHandler** (1 connections)
- **Intercepts LLM results to track usage and enforce budgets.** (1 connections) — `integrations/research_engine/budget.py`
- **Track token usage after an LLM call completes.** (1 connections) — `integrations/research_engine/budget.py`
- **Adapter that integrates the Open Deep Research graph into Neosis as a…** (1 connections) — `integrations/research_engine/open_deep_research/engine.py`
- **Trigger cooperative cancellation of the running execution.** (1 connections) — `integrations/research_engine/open_deep_research/engine.py`
- **Execute the ODR graph and normalize its events.** (1 connections) — `integrations/research_engine/open_deep_research/engine.py`
- **LLMResult** (1 connections)

## Relationships

- [UsageTracker](UsageTracker.md) (5 shared connections)
- [LegacyResearchEngine](LegacyResearchEngine.md) (2 shared connections)
- [ResearchRepository](ResearchRepository.md) (1 shared connections)

## Source Files

- `integrations/research_engine/budget.py`
- `integrations/research_engine/open_deep_research/engine.py`

## Audit Trail

- EXTRACTED: 20 (74%)
- INFERRED: 7 (26%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*