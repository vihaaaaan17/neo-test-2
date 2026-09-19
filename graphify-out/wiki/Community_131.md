# Community 131

> 23 nodes · cohesion 0.12

## Key Concepts

- **MCPClientManager** (16 connections) — `references/gpt-researcher/gpt_researcher/mcp/client.py`
- **client.py** (5 connections) — `references/gpt-researcher/gpt_researcher/mcp/client.py`
- **TestConvertConfigsHeaders** (5 connections) — `references/gpt-researcher/tests/test_mcp_client_config.py`
- **.convert_configs_to_langchain_format()** (4 connections) — `references/gpt-researcher/gpt_researcher/mcp/client.py`
- **.get_or_create_client()** (4 connections) — `references/gpt-researcher/gpt_researcher/mcp/client.py`
- **.get_all_tools()** (3 connections) — `references/gpt-researcher/gpt_researcher/mcp/client.py`
- **.__init__()** (3 connections) — `references/gpt-researcher/gpt_researcher/mcp/client.py`
- **test_mcp_client_config.py** (3 connections) — `references/gpt-researcher/tests/test_mcp_client_config.py`
- **.close_client()** (2 connections) — `references/gpt-researcher/gpt_researcher/mcp/client.py`
- **Any** (2 connections)
- **.test_headers_forwarded_for_streamable_http()** (2 connections) — `references/gpt-researcher/tests/test_mcp_client_config.py`
- **.test_headers_forwarded_for_websocket()** (2 connections) — `references/gpt-researcher/tests/test_mcp_client_config.py`
- **.test_no_headers_when_not_provided()** (2 connections) — `references/gpt-researcher/tests/test_mcp_client_config.py`
- **test_mcp_client_non_dict_config.py** (2 connections) — `references/gpt-researcher/tests/test_mcp_client_non_dict_config.py`
- **test_skips_non_dict_entries()** (2 connections) — `references/gpt-researcher/tests/test_mcp_client_non_dict_config.py`
- **MCP Client Management Module Handles MCP client creation, configuration…** (1 connections) — `references/gpt-researcher/gpt_researcher/mcp/client.py`
- **Get or create a MultiServerMCPClient with proper lifecycle management. Returns:…** (1 connections) — `references/gpt-researcher/gpt_researcher/mcp/client.py`
- **Properly close the MCP client and clean up resources.** (1 connections) — `references/gpt-researcher/gpt_researcher/mcp/client.py`
- **Get all available tools from MCP servers. Returns: List: All available MCP tools** (1 connections) — `references/gpt-researcher/gpt_researcher/mcp/client.py`
- **Manages MCP client lifecycle and configuration. Responsible for: - Converting…** (1 connections) — `references/gpt-researcher/gpt_researcher/mcp/client.py`
- **Initialize the MCP client manager. Args: mcp_configs: List of MCP server…** (1 connections) — `references/gpt-researcher/gpt_researcher/mcp/client.py`
- **Convert GPT Researcher MCP configs to langchain-mcp-adapters format. Returns:…** (1 connections) — `references/gpt-researcher/gpt_researcher/mcp/client.py`
- **MCPClientManager must skip non-dict server configs.** (1 connections) — `references/gpt-researcher/tests/test_mcp_client_non_dict_config.py`

## Relationships

- [Community 215](Community_215.md) (4 shared connections)
- [Community 179](Community_179.md) (1 shared connections)

## Source Files

- `references/gpt-researcher/gpt_researcher/mcp/client.py`
- `references/gpt-researcher/tests/test_mcp_client_config.py`
- `references/gpt-researcher/tests/test_mcp_client_non_dict_config.py`

## Audit Trail

- EXTRACTED: 33 (94%)
- INFERRED: 2 (6%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*