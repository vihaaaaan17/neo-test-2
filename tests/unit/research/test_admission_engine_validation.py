"""Admission rejects unsupported research engines before any quota or run creation."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.integrations.research_engine.engine import SUPPORTED_ENGINES
from app.services.research.admission import ResearchAdmissionController


def _controller():
    quota = MagicMock()
    quota.enforce_user_quota = AsyncMock(return_value="OK")
    quota.enforce_workspace_quota = AsyncMock(return_value="OK")
    quota.enforce_global_quota = AsyncMock(return_value="OK")
    limiter = MagicMock()
    limiter.enforce_rate_limit = AsyncMock(return_value=True)
    repo = MagicMock()
    repo.create_run = AsyncMock(return_value=MagicMock(name="run"))
    return ResearchAdmissionController(quota_service=quota, rate_limiter=limiter, repository=repo), quota, repo


def test_supported_engines_are_the_three_upstream_engines():
    assert SUPPORTED_ENGINES == ("open_deep_research", "storm", "gpt_researcher")


@pytest.mark.asyncio
@pytest.mark.parametrize("engine", SUPPORTED_ENGINES)
async def test_supported_engine_is_admitted(engine):
    controller, _, repo = _controller()
    await controller.admit_research_run(
        workspace_id=uuid.uuid4(), owner_id=uuid.uuid4(), objective="x", engine=engine
    )
    repo.create_run.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("engine", ["legacy", "test_engine", "", "ODR", "Storm"])
async def test_unsupported_engine_is_rejected_before_quota_and_run_creation(engine):
    controller, quota, repo = _controller()
    with pytest.raises(HTTPException) as exc:
        await controller.admit_research_run(
            workspace_id=uuid.uuid4(), owner_id=uuid.uuid4(), objective="x", engine=engine
        )
    assert exc.value.status_code == 422
    assert exc.value.detail == "unsupported_research_engine"
    quota.enforce_user_quota.assert_not_awaited()
    repo.create_run.assert_not_awaited()
