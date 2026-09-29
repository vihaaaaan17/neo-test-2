import pytest
import sys
from unittest.mock import patch, MagicMock

from langgraph.checkpoint.memory import MemorySaver
from app.core.config import settings
from app.services.working_memory import (
    validate_checkpointer,
    validate_checkpointer_configuration,
    get_checkpointer
)


def test_production_fails_when_saver_disabled():
    """In production, validate_checkpointer must raise RuntimeError if ASYNC_POSTGRES_SAVER_ENABLED is False."""
    with patch.object(settings, "ASYNC_POSTGRES_SAVER_ENABLED", False):
        with pytest.raises(RuntimeError, match="Production checkpointer requirement violated: AsyncPostgresSaver is unavailable"):
            validate_checkpointer(env="production")


def test_production_fails_when_neosis_env_production():
    """settings.NEOSIS_ENV == 'production' triggers production checkpointer guard."""
    with patch.object(settings, "NEOSIS_ENV", "production"):
        with patch.object(settings, "ASYNC_POSTGRES_SAVER_ENABLED", False):
            with pytest.raises(RuntimeError, match="Production checkpointer requirement violated: AsyncPostgresSaver is unavailable"):
                validate_checkpointer()


def test_production_fails_when_connection_fails():
    """In production with ASYNC_POSTGRES_SAVER_ENABLED=True, connection failure must raise RuntimeError."""
    mock_aio = MagicMock()
    mock_aio.AsyncPostgresSaver.from_conn_string.side_effect = Exception("DB down")

    with patch.object(settings, "ASYNC_POSTGRES_SAVER_ENABLED", True):
        with patch.dict(sys.modules, {
            "langgraph.checkpoint.postgres": MagicMock(aio=mock_aio),
            "langgraph.checkpoint.postgres.aio": mock_aio
        }):
            with pytest.raises(RuntimeError, match="Production checkpointer requirement violated: AsyncPostgresSaver is unavailable"):
                validate_checkpointer(env="production")


def test_production_succeeds_when_postgres_saver_available():
    """In production with valid AsyncPostgresSaver, validate_checkpointer returns the checkpointer."""
    mock_saver = MagicMock()
    mock_aio = MagicMock()
    mock_aio.AsyncPostgresSaver.from_conn_string.return_value = mock_saver

    with patch.object(settings, "ASYNC_POSTGRES_SAVER_ENABLED", True):
        with patch.dict(sys.modules, {
            "langgraph.checkpoint.postgres": MagicMock(aio=mock_aio),
            "langgraph.checkpoint.postgres.aio": mock_aio
        }):
            res = validate_checkpointer(env="production")
            assert res == mock_saver


def test_development_allows_memory_saver():
    """In development, validate_checkpointer permits fallback to MemorySaver without error."""
    with patch.object(settings, "ASYNC_POSTGRES_SAVER_ENABLED", False):
        res = validate_checkpointer(env="development")
        assert isinstance(res, MemorySaver)


def test_test_environment_allows_memory_saver():
    """In test environment, validate_checkpointer permits MemorySaver without error."""
    with patch.object(settings, "ASYNC_POSTGRES_SAVER_ENABLED", False):
        res = validate_checkpointer(env="test")
        assert isinstance(res, MemorySaver)


def test_validate_checkpointer_configuration_alias():
    """validate_checkpointer_configuration is an alias for validate_checkpointer."""
    assert validate_checkpointer_configuration is validate_checkpointer


def test_get_checkpointer_respects_environment():
    """get_checkpointer utilizes validate_checkpointer in production and returns MemorySaver in dev."""
    with patch.object(settings, "ENVIRONMENT", "development"):
        with patch.object(settings, "NEOSIS_ENV", None):
            with patch.object(settings, "ASYNC_POSTGRES_SAVER_ENABLED", False):
                cp = get_checkpointer()
                assert isinstance(cp, MemorySaver)
