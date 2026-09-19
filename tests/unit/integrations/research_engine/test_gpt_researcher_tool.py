import pytest
from app.integrations.research_engine.tools.gpt_researcher_tool import GPTResearcherTool

@pytest.mark.asyncio
async def test_gpt_researcher_tool_initialization():
    tool = GPTResearcherTool()
    assert tool.name == "gpt_researcher_deep_crawl"
    assert "crawls the web" in tool.description

    # Since GPTResearcher requires LLM API keys to actually run, we just test 
    # the initialization and ensure the schema requires a query
    schema = tool.args_schema
    assert "query" in schema.model_fields
