# BaseRetriever

> 17 nodes · cohesion 0.16

## Key Concepts

- **BaseRetriever** (10 connections) — `services/research/retrievers/base.py`
- **RetrieverRegistry** (10 connections) — `services/research/retrievers/registry.py`
- **ResearchRetrievalPolicy** (5 connections) — `services/research/retrievers/base.py`
- **.retrieve()** (5 connections) — `services/research/retrievers/registry.py`
- **ABC** (4 connections)
- **base.py** (4 connections) — `services/research/retrievers/base.py`
- **.get()** (4 connections) — `services/research/retrievers/registry.py`
- **.register()** (3 connections) — `services/research/retrievers/registry.py`
- **.__init__()** (2 connections) — `services/research/retrievers/registry.py`
- **.list_retrievers()** (2 connections) — `services/research/retrievers/registry.py`
- **registry.py** (1 connections) — `services/research/retrievers/registry.py`
- **Any** (1 connections)
- **Register a retriever instance under a name.** (1 connections) — `services/research/retrievers/registry.py`
- **Get a registered retriever by name.** (1 connections) — `services/research/retrievers/registry.py`
- **List all registered retriever names.** (1 connections) — `services/research/retrievers/registry.py`
- **Execute retrieval using the specified retriever or policy defaults, enforcing…** (1 connections) — `services/research/retrievers/registry.py`
- **Central registry for managing and invoking retrievers (web, academic, mcp,…** (1 connections) — `services/research/retrievers/registry.py`

## Relationships

- [ResearchSourceResult](ResearchSourceResult.md) (5 shared connections)
- [MCPRetriever](MCPRetriever.md) (3 shared connections)
- [LegacyResearchEngine](LegacyResearchEngine.md) (1 shared connections)
- [run_research_agent_job](run_research_agent_job.md) (1 shared connections)
- [GPTResearcherRetriever](GPTResearcherRetriever.md) (1 shared connections)
- [WebRetriever](WebRetriever.md) (1 shared connections)

## Source Files

- `services/research/retrievers/base.py`
- `services/research/retrievers/registry.py`

## Audit Trail

- EXTRACTED: 30 (88%)
- INFERRED: 4 (12%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*