# neosis_web_search

> 16 nodes · cohesion 0.13

## Key Concepts

- **neosis_web_search()** (8 connections) — `integrations/research_engine/tools/neosis_search_tools.py`
- **configuration.py** (5 connections) — `integrations/research_engine/upstream/open_deep_research/configuration.py`
- **SearchAPI** (5 connections) — `integrations/research_engine/upstream/open_deep_research/configuration.py`
- **get_search_tool()** (5 connections) — `integrations/research_engine/upstream/open_deep_research/utils.py`
- **MCPConfig** (3 connections) — `integrations/research_engine/upstream/open_deep_research/configuration.py`
- **BaseModel** (2 connections)
- **Enum** (2 connections)
- **neosis_search_tools.py** (1 connections) — `integrations/research_engine/tools/neosis_search_tools.py`
- **InjectedToolArg** (1 connections)
- **RunnableConfig** (1 connections)
- **tool** (1 connections)
- **Fetch search results, immediately persist them to Neosis DB, and return…** (1 connections) — `integrations/research_engine/tools/neosis_search_tools.py`
- **Configuration management for the Open Deep Research system.** (1 connections) — `integrations/research_engine/upstream/open_deep_research/configuration.py`
- **Enumeration of available search API providers.** (1 connections) — `integrations/research_engine/upstream/open_deep_research/configuration.py`
- **Configuration for Model Context Protocol (MCP) servers.** (1 connections) — `integrations/research_engine/upstream/open_deep_research/configuration.py`
- **Configure and return search tools based on the specified API provider. Args:…** (1 connections) — `integrations/research_engine/upstream/open_deep_research/utils.py`

## Relationships

- [Configuration](Configuration.md) (2 shared connections)
- [get_all_tools](get_all_tools.md) (2 shared connections)
- [ResearchRepository](ResearchRepository.md) (1 shared connections)
- [ResearchNormalizationService](ResearchNormalizationService.md) (1 shared connections)
- [utils.py](utils.py.md) (1 shared connections)

## Source Files

- `integrations/research_engine/tools/neosis_search_tools.py`
- `integrations/research_engine/upstream/open_deep_research/configuration.py`
- `integrations/research_engine/upstream/open_deep_research/utils.py`

## Audit Trail

- EXTRACTED: 19 (83%)
- INFERRED: 4 (17%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*