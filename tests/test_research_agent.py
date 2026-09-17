import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from app.orchestration.research_mode import ResearchModeOrchestrator
from app.services.web_search import WebSearchTool

@pytest.mark.asyncio
async def test_research_orchestrator():
    workspace_id = uuid4()
    objective = "Find latest solid state battery news"
    
    # Mock LLM
    async def mock_llm_gateway(prompt: str) -> str:
        if "expert research planner" in prompt:
            return '["search query 1", "search query 2"]'
        if "research synthesis agent" in prompt:
            return '''
            {
                "nodes": [
                    {
                        "id": "node1",
                        "label": "Concept",
                        "properties": {"name": "Solid State"}
                    }
                ],
                "edges": []
            }
            '''
        return ""
        
    # Mock WebSearchTool
    mock_search = MagicMock(spec=WebSearchTool)
    mock_search.search = AsyncMock(side_effect=[
        "Result 1 content",
        "Result 2 content"
    ])
    
    orchestrator = ResearchModeOrchestrator(
        llm_gateway=mock_llm_gateway,
        search_tool=mock_search
    )
    
    result_state = await orchestrator.run(workspace_id, objective)
    
    # Verify Planning
    assert len(result_state["plan"]) == 2
    assert result_state["plan"][0] == "search query 1"
    
    # Verify Execution
    assert mock_search.search.call_count == 2
    assert len(result_state["gathered_evidence"]) == 2
    assert "Result 1 content" in result_state["gathered_evidence"][0]
    
    # Verify Synthesis
    assert result_state["final_graph"] is not None
    assert len(result_state["final_graph"]["nodes"]) == 1
    assert result_state["final_graph"]["nodes"][0]["id"] == "node1"
