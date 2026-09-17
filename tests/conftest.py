"""
Shared pytest fixtures and markers.

Integration tests that touch a real Postgres instance are marked with
`@pytest.mark.integration`. They are automatically skipped when no Postgres
is reachable (e.g. local dev without Docker running, CI without a DB service).

To run integration tests explicitly:
    pytest -m integration
"""
import asyncio
import socket
import pytest
from urllib.parse import urlparse


def _postgres_is_reachable() -> bool:
    """Quick TCP probe to check if Postgres port is open."""
    from app.core.config import settings
    try:
        parsed = urlparse(settings.DATABASE_URL.replace("postgresql+asyncpg", "http"))
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


# --------------------------------------------------------------------------- #
# Auto-skip marker: @pytest.mark.integration
# --------------------------------------------------------------------------- #
def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require a live Postgres connection "
        "(auto-skipped when Postgres is not reachable)"
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests if Postgres is not reachable."""
    if _postgres_is_reachable():
        return  # DB is up — run everything
    skip_no_db = pytest.mark.skip(reason="Postgres not reachable (start docker-compose)")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_no_db)
