import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from app.integrations.research_engine.factory import ResearchEngineFactory
from app.integrations.research_engine.legacy import LegacyResearchEngine
from app.integrations.research_engine.open_deep_research.engine import OpenDeepResearchEngine

@pytest.mark.asyncio
async def test_legacy_engine_factory_integration():
    """
    Verify that the factory successfully resolves the Legacy engine
    and that `astream_events` works without breaking at instantiation.
    """
    mock_llm_gateway = AsyncMock()
    mock_search_tool = MagicMock()
    mock_redis = MagicMock()
    
    engine = ResearchEngineFactory.get_engine(
        engine_name="legacy",
        llm_gateway=mock_llm_gateway,
        search_tool=mock_search_tool,
        redis_client=mock_redis
    )
    
    assert isinstance(engine, LegacyResearchEngine)
    assert engine.orchestrator is not None

@pytest.mark.asyncio
async def test_odr_engine_factory_integration():
    """
    Verify that the factory successfully resolves the ODR engine.
    """
    mock_llm_gateway = AsyncMock()
    mock_search_tool = MagicMock()
    mock_redis = MagicMock()
    
    engine = ResearchEngineFactory.get_engine(
        engine_name="open_deep_research",
        llm_gateway=mock_llm_gateway,
        search_tool=mock_search_tool,
        redis_client=mock_redis
    )
    
    assert isinstance(engine, OpenDeepResearchEngine)
    assert engine.llm_gateway == mock_llm_gateway
    
    workspace_id = uuid4()
    objective = "Test objective"
    run_id = uuid4()
    
    generator = engine.astream_events(run_id, workspace_id, objective)
    first_event = await generator.__anext__()
    
    assert first_event["status"] == "starting"
    assert "Initializing Open Deep Research execution" in first_event["message"]
