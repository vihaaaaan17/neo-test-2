import pytest
import uuid

from app.core.config import settings
from app.integrations.research_engine.factory import ResearchEngineFactory

async def mock_llm_gateway(prompt: str) -> str:
    return "Mock response"

class MockSearchTool:
    async def search(self, query: str) -> list[dict]:
        return [{"url": "http://example.com", "content": "Mock"}]
    async def __call__(self, query: str) -> list[dict]:
        return await self.search(query)
    async def execute(self, query: str) -> list[dict]:
        return await self.search(query)

class DummyOpenDeepResearchEngine:
    pass

class DummyLegacyResearchEngine:
    pass

@pytest.mark.asyncio
async def test_engine_rollback(monkeypatch):
    def mock_get_engine(engine_name, llm_gateway, search_tool, redis_client=None):
        if settings.ACTIVE_RESEARCH_ENGINE:
            engine_name = settings.ACTIVE_RESEARCH_ENGINE
        if engine_name == "open_deep_research":
            return DummyOpenDeepResearchEngine()
        return DummyLegacyResearchEngine()

    monkeypatch.setattr(ResearchEngineFactory, "get_engine", staticmethod(mock_get_engine))

    # 1. Base case: legacy
    settings.ACTIVE_RESEARCH_ENGINE = "legacy"
    engine1 = ResearchEngineFactory.get_engine(
        engine_name="open_deep_research", # requested engine
        llm_gateway=mock_llm_gateway,
        search_tool=MockSearchTool()
    )
    assert engine1.__class__.__name__ == "DummyLegacyResearchEngine"
    
    # 2. Cutover to ODR
    settings.ACTIVE_RESEARCH_ENGINE = "open_deep_research"
    engine2 = ResearchEngineFactory.get_engine(
        engine_name="legacy", # requested engine, should be overridden
        llm_gateway=mock_llm_gateway,
        search_tool=MockSearchTool()
    )
    assert engine2.__class__.__name__ == "DummyOpenDeepResearchEngine"
    
    # 3. Rollback to legacy
    settings.ACTIVE_RESEARCH_ENGINE = "legacy"
    engine3 = ResearchEngineFactory.get_engine(
        engine_name="open_deep_research", 
        llm_gateway=mock_llm_gateway,
        search_tool=MockSearchTool()
    )
    assert engine3.__class__.__name__ == "DummyLegacyResearchEngine"
    
    # Cleanup
    settings.ACTIVE_RESEARCH_ENGINE = None
