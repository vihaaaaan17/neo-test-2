import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.research.retrievers import (
    RetrieverRegistry,
    ResearchRetrievalPolicy,
    ResearchSourceResult,
    BaseRetriever,
    WebRetriever,
    AcademicRetriever,
    MCPRetriever,
    GPTResearcherRetriever
)

class MockRetriever(BaseRetriever):
    name = "mock"

    async def retrieve(self, query: str, max_results: int = 5, **kwargs):
        return [
            ResearchSourceResult(
                url=f"https://example.com/search?q={query}",
                title="Mock Result",
                content=f"Mock content for {query}",
                query=query,
                retriever=self.name
            )
        ]

@pytest.mark.asyncio
async def test_retriever_registry_basic():
    registry = RetrieverRegistry()
    mock_retriever = MockRetriever()
    registry.register("mock", mock_retriever)

    assert "mock" in registry.list_retrievers()
    assert registry.get("mock") == mock_retriever

    results = await registry.retrieve("test query", retriever_name="mock")
    assert len(results) == 1
    assert results[0].content == "Mock content for test query"
    assert results[0].retriever == "mock"

@pytest.mark.asyncio
async def test_retriever_registry_policy_max_calls():
    policy = ResearchRetrievalPolicy(max_calls=1)
    registry = RetrieverRegistry(policy=policy)
    registry.register("mock", MockRetriever())

    # First call succeeds
    res1 = await registry.retrieve("query 1", retriever_name="mock")
    assert len(res1) == 1

    # Second call exceeds max_calls=1
    res2 = await registry.retrieve("query 2", retriever_name="mock")
    assert len(res2) == 0

@pytest.mark.asyncio
async def test_retriever_registry_policy_disallowed():
    policy = ResearchRetrievalPolicy(allow_web=False)
    registry = RetrieverRegistry(policy=policy)
    registry.register("tavily", MockRetriever())

    results = await registry.retrieve("query", retriever_name="tavily")
    assert len(results) == 0

@pytest.mark.asyncio
async def test_academic_retriever_parsing():
    retriever = AcademicRetriever()
    sample_atom = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <id>http://arxiv.org/abs/2101.00001</id>
            <title>Test arXiv Paper</title>
            <summary>This is a test summary of an arXiv paper.</summary>
        </entry>
    </feed>
    """
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = sample_atom
        mock_get.return_value = mock_response

        results = await retriever.retrieve("quantum computing", max_results=1)
        assert len(results) == 1
        assert results[0].title == "Test arXiv Paper"
        assert "test summary" in results[0].content
        assert results[0].retriever == "arxiv"

@pytest.mark.asyncio
async def test_mcp_retriever_acl():
    policy = ResearchRetrievalPolicy(allow_mcp=True, allowed_mcp_servers=["allowed-server"])
    retriever = MCPRetriever(policy=policy, mcp_client_manager=AsyncMock())
    retriever.mcp_client_manager.call_tool = AsyncMock(return_value={
        "content": "MCP tool output",
        "title": "Tool Result",
        "url": "mcp://allowed-server/tool"
    })

    # Disallowed server
    results_disallowed = await retriever.retrieve("query", server_name="forbidden-server", tool_name="some-tool")
    assert len(results_disallowed) == 0

    # Allowed server
    results_allowed = await retriever.retrieve("query", server_name="allowed-server", tool_name="some-tool")
    assert len(results_allowed) == 1
    assert results_allowed[0].content == "MCP tool output"
    assert results_allowed[0].retriever == "mcp"

@pytest.mark.asyncio
async def test_gpt_researcher_retriever():
    mock_gateway = AsyncMock(return_value="LLM Response")
    with patch("app.services.research.retrievers.gpt_researcher.GPTResearcher") as MockGPTResearcher:
        instance = MockGPTResearcher.return_value
        instance.conduct_research = AsyncMock()
        instance.get_results.return_value = [
            {"link": "https://example.com/gpt", "title": "GPT Result", "content": "GPT Content", "score": 0.95}
        ]

        retriever = GPTResearcherRetriever(llm_gateway=mock_gateway)
        results = await retriever.retrieve("AI trends", max_results=1)

        assert len(results) == 1
        assert results[0].title == "GPT Result"
        assert results[0].content == "GPT Content"
        assert results[0].retriever == "gpt_researcher"
