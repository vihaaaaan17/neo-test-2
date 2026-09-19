# Community 144

> 21 nodes · cohesion 0.13

## Key Concepts

- **MCPToolSelector** (12 connections) — `references/gpt-researcher/gpt_researcher/mcp/tool_selector.py`
- **tool_selector.py** (7 connections) — `references/gpt-researcher/gpt_researcher/mcp/tool_selector.py`
- **test_mcp_tool_selector_json_repair.py** (7 connections) — `references/gpt-researcher/tests/test_mcp_tool_selector_json_repair.py`
- **.select_relevant_tools()** (5 connections) — `references/gpt-researcher/gpt_researcher/mcp/tool_selector.py`
- **._call_llm_for_tool_selection()** (4 connections) — `references/gpt-researcher/gpt_researcher/mcp/tool_selector.py`
- **test_select_recovers_fenced_json()** (4 connections) — `references/gpt-researcher/tests/test_mcp_tool_selector_json_repair.py`
- **test_select_skips_non_dict_tool_rows()** (4 connections) — `references/gpt-researcher/tests/test_mcp_tool_selector_json_repair.py`
- **_Tool** (4 connections) — `references/gpt-researcher/tests/test_mcp_tool_selector_json_repair.py`
- **._fallback_tool_selection()** (3 connections) — `references/gpt-researcher/gpt_researcher/mcp/tool_selector.py`
- **.generate_mcp_tool_selection_prompt()** (3 connections) — `references/gpt-researcher/gpt_researcher/prompts.py`
- **.__init__()** (2 connections) — `references/gpt-researcher/gpt_researcher/mcp/tool_selector.py`
- **asyncio** (2 connections)
- **MCP Tool Selection Module Handles intelligent tool selection using LLM analysis.** (1 connections) — `references/gpt-researcher/gpt_researcher/mcp/tool_selector.py`
- **Call the LLM using the existing create_chat_completion function for tool…** (1 connections) — `references/gpt-researcher/gpt_researcher/mcp/tool_selector.py`
- **Fallback tool selection using pattern matching if LLM selection fails. Args:…** (1 connections) — `references/gpt-researcher/gpt_researcher/mcp/tool_selector.py`
- **Handles intelligent selection of MCP tools using LLM analysis. Responsible for:…** (1 connections) — `references/gpt-researcher/gpt_researcher/mcp/tool_selector.py`
- **Initialize the tool selector. Args: cfg: Configuration object with LLM settings…** (1 connections) — `references/gpt-researcher/gpt_researcher/mcp/tool_selector.py`
- **Use LLM to select the most relevant tools for the research query. Args: query:…** (1 connections) — `references/gpt-researcher/gpt_researcher/mcp/tool_selector.py`
- **Generate prompt for LLM-based MCP tool selection. Args: query: The research…** (1 connections) — `references/gpt-researcher/gpt_researcher/prompts.py`
- **MCP tool selector should recover fenced LLM JSON via json_repair.** (1 connections) — `references/gpt-researcher/tests/test_mcp_tool_selector_json_repair.py`
- **.__init__()** (1 connections) — `references/gpt-researcher/tests/test_mcp_tool_selector_json_repair.py`

## Relationships

- [Community 215](Community_215.md) (4 shared connections)
- [Community 4](Community_4.md) (2 shared connections)
- [Community 41](Community_41.md) (2 shared connections)
- [Community 179](Community_179.md) (1 shared connections)
- [Community 168](Community_168.md) (1 shared connections)

## Source Files

- `references/gpt-researcher/gpt_researcher/mcp/tool_selector.py`
- `references/gpt-researcher/gpt_researcher/prompts.py`
- `references/gpt-researcher/tests/test_mcp_tool_selector_json_repair.py`

## Audit Trail

- EXTRACTED: 36 (95%)
- INFERRED: 2 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*