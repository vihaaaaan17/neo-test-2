import pytest
from unittest.mock import patch, MagicMock
from app.core.config import settings
from app.services.working_memory import (
    validate_checkpointer_configuration,
    get_checkpointer,
    MemorySaver
)


def test_production_fails_fast_when_durable_saver_disabled():
    """
    In production, ASYNC_POSTGRES_SAVER_ENABLED must be True.
    If disabled, validate_checkpointer_configuration must raise RuntimeError immediately.
    """
    with patch.object(settings, "ENVIRONMENT", "production"), \
         patch.object(settings, "ASYNC_POSTGRES_SAVER_ENABLED", False):
        with pytest.raises(RuntimeError, match="Production environment misconfiguration: ASYNC_POSTGRES_SAVER_ENABLED must be True"):
            validate_checkpointer_configuration()


def test_production_fails_fast_when_connection_fails():
    """
    In production, if AsyncPostgresSaver fails to connect,
    validate_checkpointer_configuration must fail fast and refuse in-memory fallback.
    """
    with patch.object(settings, "ENVIRONMENT", "production"), \
         patch.object(settings, "ASYNC_POSTGRES_SAVER_ENABLED", True):
        with pytest.raises(RuntimeError, match="Production durable checkpointer failed to initialize"):
            validate_checkpointer_configuration()


def test_development_allows_memory_saver():
    """
    In development or test, MemorySaver is permitted without raising RuntimeError.
    """
    with patch.object(settings, "ENVIRONMENT", "development"), \
         patch.object(settings, "ASYNC_POSTGRES_SAVER_ENABLED", False):
        validate_checkpointer_configuration()
        checkpointer = get_checkpointer()
        assert isinstance(checkpointer, MemorySaver)


def test_test_environment_allows_memory_saver():
    with patch.object(settings, "ENVIRONMENT", "test"), \
         patch.object(settings, "ASYNC_POSTGRES_SAVER_ENABLED", False):
        validate_checkpointer_configuration()
        checkpointer = get_checkpointer()
        assert isinstance(checkpointer, MemorySaver)
