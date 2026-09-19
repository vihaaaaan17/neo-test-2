import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from app.services.research.factory import get_research_engine
from app.integrations.research_engine.engine import OpenDeepResearchEngine

@pytest.mark.asyncio
async def test_odr_engine_factory_integration():
    """
    Smoke test to verify that the factory successfully resolves the new ODR engine
    and that `astream_events` works without breaking at instantiation.
    """
    mock_llm_gateway = AsyncMock()
    mock_search_tool = MagicMock()
    mock_redis = MagicMock()
    
    with patch("app.services.research.factory.settings.ENABLE_ADVANCED_RESEARCH", True):
        engine = get_research_engine(
            workspace_flag="new",
            llm_gateway=mock_llm_gateway,
            search_tool=mock_search_tool,
            redis_client=mock_redis
        )
    
    assert isinstance(engine, OpenDeepResearchEngine)
    assert engine.llm_gateway == mock_llm_gateway
    assert engine.search_tool == mock_search_tool
    assert engine.redis_client == mock_redis
    
    workspace_id = uuid4()
    objective = "Test objective"
    
    # Just verify that the generator yields at least the first starting event
    generator = engine.astream_events(workspace_id, objective)
    
    first_event = await generator.__anext__()
    assert first_event["status"] == "starting"
    assert "Initializing Open Deep Research" in first_event["message"]
