import pytest
from unittest.mock import AsyncMock
from uuid import uuid4
from app.orchestration.ground_mode import GroundModeOrchestrator
from app.services.hybrid_retrieval import RetrievedChunk

@pytest.mark.asyncio
async def test_ground_mode_orchestrator_success_first_try():
    hybrid_retriever = AsyncMock()
    hybrid_retriever.retrieve.return_value = [
        RetrievedChunk(block_id=uuid4(), text="The capital of France is Paris.", source_id=uuid4(), score=1.0)
    ]
    
    async def mock_llm_gateway(prompt: str) -> str:
        if "hallucination detection judge" in prompt:
            return "YES"
        return "Paris"
        
    async def mock_embed_gateway(text: str) -> list[float]:
        return [0.1, 0.2, 0.3]
        
    orchestrator = GroundModeOrchestrator(
        hybrid_retriever=hybrid_retriever,
        llm_gateway=mock_llm_gateway,
        embed_gateway=mock_embed_gateway
    )
    
    workspace_id = uuid4()
    result = await orchestrator.run(workspace_id=workspace_id, query="What is the capital of France?")
    
    assert result["answer"] == "Paris"
    assert result["is_grounded"] is True
    assert result["retries"] == 1  # 0 on retrieve, increments to 1 on check_hallucination_node
    
    hybrid_retriever.retrieve.assert_called_once_with(
        workspace_id=workspace_id,
        query_text="What is the capital of France?",
        query_embedding=[0.1, 0.2, 0.3]
    )

@pytest.mark.asyncio
async def test_ground_mode_orchestrator_retry_on_hallucination():
    hybrid_retriever = AsyncMock()
    hybrid_retriever.retrieve.return_value = [
        RetrievedChunk(block_id=uuid4(), text="Water boils at 100 degrees Celsius.", source_id=uuid4(), score=1.0)
    ]
    
    call_count = 0
    async def mock_llm_gateway(prompt: str) -> str:
        nonlocal call_count
        if "hallucination detection judge" in prompt:
            call_count += 1
            if call_count == 1:
                return "NO"  # Fail the first time
            return "YES"     # Pass the second time
        
        # On retry, the prompt should contain the critical instruction
        if "CRITICAL INSTRUCTION" in prompt:
            return "Water boils at 100 degrees Celsius."
        return "Water boils at 100 degrees Celsius, and ice melts at 0." # Hallucination on first try
        
    async def mock_embed_gateway(text: str) -> list[float]:
        return [0.1]
        
    orchestrator = GroundModeOrchestrator(
        hybrid_retriever=hybrid_retriever,
        llm_gateway=mock_llm_gateway,
        embed_gateway=mock_embed_gateway
    )
    
    workspace_id = uuid4()
    result = await orchestrator.run(workspace_id=workspace_id, query="When does water boil?")
    
    assert result["answer"] == "Water boils at 100 degrees Celsius."
    assert result["is_grounded"] is True
    assert result["retries"] == 2  # Increments once per check, checked twice
