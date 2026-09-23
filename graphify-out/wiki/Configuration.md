# Configuration

> 29 nodes · cohesion 0.15

## Key Concepts

- **Configuration** (16 connections) — `integrations/research_engine/upstream/open_deep_research/configuration.py`
- **.from_runnable_config()** (14 connections) — `integrations/research_engine/upstream/open_deep_research/configuration.py`
- **supervisor()** (11 connections) — `integrations/research_engine/upstream/open_deep_research/deep_researcher.py`
- **deep_researcher.py** (10 connections) — `integrations/research_engine/upstream/open_deep_research/deep_researcher.py`
- **clarify_with_user()** (10 connections) — `integrations/research_engine/upstream/open_deep_research/deep_researcher.py`
- **compress_research()** (10 connections) — `integrations/research_engine/upstream/open_deep_research/deep_researcher.py`
- **final_report_generation()** (10 connections) — `integrations/research_engine/upstream/open_deep_research/deep_researcher.py`
- **researcher()** (10 connections) — `integrations/research_engine/upstream/open_deep_research/deep_researcher.py`
- **write_research_brief()** (10 connections) — `integrations/research_engine/upstream/open_deep_research/deep_researcher.py`
- **get_api_key_for_model()** (10 connections) — `integrations/research_engine/upstream/open_deep_research/utils.py`
- **supervisor_tools()** (9 connections) — `integrations/research_engine/upstream/open_deep_research/deep_researcher.py`
- **RunnableConfig** (8 connections)
- **get_today_str()** (8 connections) — `integrations/research_engine/upstream/open_deep_research/utils.py`
- **Command** (6 connections)
- **Config** (2 connections) — `integrations/research_engine/upstream/open_deep_research/configuration.py`
- **RunnableConfig** (1 connections)
- **Create a Configuration instance from a RunnableConfig.** (1 connections) — `integrations/research_engine/upstream/open_deep_research/configuration.py`
- **Pydantic configuration.** (1 connections) — `integrations/research_engine/upstream/open_deep_research/configuration.py`
- **Main configuration class for the Deep Research agent.** (1 connections) — `integrations/research_engine/upstream/open_deep_research/configuration.py`
- **Main LangGraph implementation for the Deep Research agent.** (1 connections) — `integrations/research_engine/upstream/open_deep_research/deep_researcher.py`
- **Transform user messages into a structured research brief and initialize…** (1 connections) — `integrations/research_engine/upstream/open_deep_research/deep_researcher.py`
- **Lead research supervisor that plans research strategy and delegates to…** (1 connections) — `integrations/research_engine/upstream/open_deep_research/deep_researcher.py`
- **Execute tools called by the supervisor, including research delegation and…** (1 connections) — `integrations/research_engine/upstream/open_deep_research/deep_researcher.py`
- **Individual researcher that conducts focused research on specific topics. This…** (1 connections) — `integrations/research_engine/upstream/open_deep_research/deep_researcher.py`
- **Compress and synthesize research findings into a concise, structured summary.…** (1 connections) — `integrations/research_engine/upstream/open_deep_research/deep_researcher.py`
- *... and 4 more nodes in this community*

## Relationships

- [state.py](state.py.md) (11 shared connections)
- [utils.py](utils.py.md) (10 shared connections)
- [researcher_tools](researcher_tools.md) (6 shared connections)
- [get_all_tools](get_all_tools.md) (4 shared connections)
- [is_token_limit_exceeded](is_token_limit_exceeded.md) (3 shared connections)
- [neosis_web_search](neosis_web_search.md) (2 shared connections)
- [get_notes_from_tool_calls](get_notes_from_tool_calls.md) (2 shared connections)

## Source Files

- `integrations/research_engine/upstream/open_deep_research/configuration.py`
- `integrations/research_engine/upstream/open_deep_research/deep_researcher.py`
- `integrations/research_engine/upstream/open_deep_research/utils.py`

## Audit Trail

- EXTRACTED: 57 (58%)
- INFERRED: 41 (42%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*