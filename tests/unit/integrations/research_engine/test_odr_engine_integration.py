import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from app.core.config import settings
from app.integrations.research_engine.engine import SUPPORTED_ENGINES
from app.integrations.research_engine.exceptions import ResearchEngineSetupError
from app.integrations.research_engine.factory import ResearchEngineFactory
from app.integrations.research_engine.open_deep_research.engine import OpenDeepResearchEngine


@pytest.mark.asyncio
async def test_odr_engine_factory_integration():
    """The factory resolves the ODR engine and astream_events starts without breaking at instantiation."""
    engine = ResearchEngineFactory.get_engine(engine_name="open_deep_research", redis_client=MagicMock())

    assert isinstance(engine, OpenDeepResearchEngine)

    generator = engine.astream_events(uuid4(), uuid4(), "Test objective")
    first_event = await generator.__anext__()

    assert first_event["status"] == "starting"
    assert "Initializing Open Deep Research execution" in first_event["message"]


@pytest.mark.parametrize("engine_name", ["legacy", "test_engine", "", "ODR"])
def test_factory_rejects_unsupported_engines(engine_name):
    with pytest.raises(ResearchEngineSetupError):
        ResearchEngineFactory.get_engine(engine_name=engine_name)


def test_factory_ignores_active_research_engine_setting_and_env(monkeypatch):
    """A persisted engine is never silently overridden by configuration (no rollback/kill-switch)."""
    monkeypatch.setattr(settings, "ACTIVE_RESEARCH_ENGINE", "legacy")
    monkeypatch.setenv("ACTIVE_RESEARCH_ENGINE", "legacy")

    engine = ResearchEngineFactory.get_engine(engine_name="open_deep_research")

    assert isinstance(engine, OpenDeepResearchEngine)
    assert SUPPORTED_ENGINES == ("open_deep_research", "storm", "gpt_researcher")


def test_factory_resolves_each_supported_engine_to_its_thin_adapter():
    from app.integrations.research_engine.gpt_researcher.engine import GPTResearcherEngine
    from app.integrations.research_engine.storm.engine import StormResearchEngine

    expected = {
        "open_deep_research": OpenDeepResearchEngine,
        "storm": StormResearchEngine,
        "gpt_researcher": GPTResearcherEngine,
    }
    assert set(expected) == set(SUPPORTED_ENGINES)
    for name, cls in expected.items():
        assert type(ResearchEngineFactory.get_engine(engine_name=name, redis_client=MagicMock())) is cls
