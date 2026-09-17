import pytest
from uuid import uuid4
from unittest.mock import AsyncMock
from app.services.episodic import EpisodicMemoryService
from app.repositories.episodic import EpisodicRepository
from app.models.episodic import EpisodicMemory

@pytest.mark.asyncio
async def test_episodic_memory_compression():
    repo = AsyncMock(spec=EpisodicRepository)
    
    mock_summary = "Agent investigated X, found Y, and concluded Z."
    async def mock_llm_gateway(prompt: str) -> str:
        assert "Scratchpad:" in prompt
        assert "Hypotheses:" in prompt
        return mock_summary

    service = EpisodicMemoryService(repository=repo, llm_gateway=mock_llm_gateway)
    
    owner_id = uuid4()
    workspace_id = uuid4()
    run_id = uuid4()
    
    working_state = {
        "scratchpad": ["Tried searching for Y", "Failed to find Y", "Found Z instead"],
        "active_hypotheses": ["Maybe Z is the real Y"],
        "pinned_evidence": []
    }
    
    expected_memory = EpisodicMemory(episode_id=uuid4(), summary=mock_summary)
    repo.create_episode.return_value = expected_memory
    
    result = await service.compress_working_memory(
        owner_id=owner_id,
        workspace_id=workspace_id,
        working_state=working_state,
        run_id=run_id
    )
    
    assert result == expected_memory
    repo.create_episode.assert_called_once()
    args, kwargs = repo.create_episode.call_args
    
    assert kwargs["owner_id"] == owner_id
    assert kwargs["workspace_id"] == workspace_id
    assert kwargs["data"].summary == mock_summary
    assert kwargs["data"].event_type == "working_memory_compression"
    assert kwargs["data"].run_id == run_id
