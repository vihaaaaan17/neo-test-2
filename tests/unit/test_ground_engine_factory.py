import pytest
import sys
from unittest.mock import patch, MagicMock

# Mock pgvector before any app imports to avoid ModuleNotFoundError
sys.modules['pgvector'] = MagicMock()
sys.modules['pgvector.sqlalchemy'] = MagicMock()

from app.services.ground.factory import get_ground_engine
from app.integrations.open_notebook.ground_engine import OpenNotebookGroundEngine
from app.orchestration.ground_mode import GroundModeOrchestrator

pytestmark = pytest.mark.asyncio

@patch("app.services.ground.factory.settings")
async def test_ground_engine_factory_enabled(mock_settings):
    """Verify that when OPEN_NOTEBOOK_ENABLED=True, the legacy engine is not instantiated."""
    mock_settings.OPEN_NOTEBOOK_ENABLED = True
    
    hybrid_retriever = MagicMock()
    llm_gateway = MagicMock()
    embed_gateway = MagicMock()
    
    with patch("app.orchestration.ground_mode.GroundModeOrchestrator.__init__") as mock_legacy_init:
        engine = await get_ground_engine(
            hybrid_retriever=hybrid_retriever,
            llm_gateway=llm_gateway,
            embed_gateway=embed_gateway
        )
        
        assert isinstance(engine, OpenNotebookGroundEngine)
        mock_legacy_init.assert_not_called()

@patch("app.services.ground.factory.settings")
async def test_ground_engine_factory_disabled(mock_settings):
    """Verify that when OPEN_NOTEBOOK_ENABLED=False, the legacy engine is instantiated correctly."""
    mock_settings.OPEN_NOTEBOOK_ENABLED = False
    
    hybrid_retriever = MagicMock()
    llm_gateway = MagicMock()
    embed_gateway = MagicMock()
    
    # We don't mock __init__ because we want to verify it works without failing, 
    # and we can patch out any complex nested dependencies or test it normally
    # But since it emits warnings and telemetry, we might want to catch that.
    with patch("logging.Logger.warning") as mock_warning:
        with patch("opentelemetry.metrics.get_meter") as mock_meter:
            mock_counter = MagicMock()
            mock_meter.return_value.create_counter.return_value = mock_counter
            
            engine = await get_ground_engine(
                hybrid_retriever=hybrid_retriever,
                llm_gateway=llm_gateway,
                embed_gateway=embed_gateway
            )
            
            assert isinstance(engine, GroundModeOrchestrator)
            mock_warning.assert_called_with(
                "GroundModeOrchestrator is deprecated and will be removed in Phase 5. "
                "Please use OpenNotebookGroundEngine instead. "
                "Ensure OPEN_NOTEBOOK_ENABLED is True in your configuration."
            )
            mock_counter.add.assert_called_once_with(1)
