import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.services.research.metrics import ResearchMetricsService
from app.models.research import ResearchRun, ResearchEvent


@pytest.mark.asyncio
async def test_emit_metrics_utc_and_structured_tokens():
    mock_repo = MagicMock()
    mock_repo.create_event = AsyncMock()

    service = ResearchMetricsService(repository=mock_repo)

    workspace_id = uuid.uuid4()
    run_id = uuid.uuid4()

    # Naive start time (should get timezone.utc attached)
    start_time = datetime(2026, 9, 29, 12, 0, 0)
    end_time = datetime(2026, 9, 29, 12, 0, 5)

    usage_metrics = {
        "wait_time_seconds": 1.25,
        "time_to_first_event_seconds": 0.45,
        "tool_call_count": 8,
        "cost": 0.042,
        "tokens": {
            "prompt_tokens": 1200,
            "completion_tokens": 350,
            "total_tokens": 1550,
        },
    }

    metrics = await service.emit_metrics(
        run_id=run_id,
        workspace_id=workspace_id,
        status="completed",
        start_time=start_time,
        end_time=end_time,
        usage_metrics=usage_metrics,
        failures=None,
    )

    assert metrics["run_id"] == str(run_id)
    assert metrics["workspace_id"] == str(workspace_id)
    assert metrics["status"] == "completed"
    assert metrics["duration_seconds"] == 5.0
    assert metrics["latency_ms"] == 5000.0
    assert metrics["wait_time_seconds"] == 1.25
    assert metrics["time_to_first_event_seconds"] == 0.45
    assert metrics["tool_call_count"] == 8
    assert metrics["cost"] == 0.042
    assert metrics["tokens"]["prompt_tokens"] == 1200
    assert metrics["tokens"]["completion_tokens"] == 350
    assert metrics["tokens"]["total_tokens"] == 1550
    assert "+00:00" in metrics["start_time"] or "Z" in metrics["start_time"]
    assert "+00:00" in metrics["end_time"] or "Z" in metrics["end_time"]

    # Verify event persisted to repo
    mock_repo.create_event.assert_awaited_once_with(
        workspace_id=workspace_id,
        run_id=run_id,
        event_type="research_metrics",
        payload=metrics,
    )


@pytest.mark.asyncio
async def test_emit_metrics_scalar_tokens_fallback():
    mock_repo = MagicMock()
    mock_repo.create_event = AsyncMock()

    service = ResearchMetricsService(repository=mock_repo)

    workspace_id = uuid.uuid4()
    run_id = uuid.uuid4()
    start_time = datetime.now(timezone.utc) - timedelta(seconds=2)

    usage_metrics = {
        "tokens": 500,
        "tool_calls": 3,
        "ttfe": 0.3,
        "cost": 0.015,
    }

    metrics = await service.emit_metrics(
        run_id=run_id,
        workspace_id=workspace_id,
        status="done",
        start_time=start_time,
        usage_metrics=usage_metrics,
    )

    assert metrics["tokens"]["total_tokens"] == 500
    assert metrics["tokens"]["completion_tokens"] == 500
    assert metrics["tool_call_count"] == 3
    assert metrics["time_to_first_event_seconds"] == 0.3
    assert metrics["cost"] == 0.015


@pytest.mark.asyncio
async def test_track_helpers_and_utc_normalization():
    mock_repo = MagicMock()
    mock_repo.create_event = AsyncMock()

    service = ResearchMetricsService(repository=mock_repo)

    workspace_id = uuid.uuid4()
    run_id = uuid.uuid4()

    # TTFE with naive time
    naive_event_time = datetime(2026, 9, 29, 10, 0, 0)
    await service.track_time_to_first_event(run_id, workspace_id, naive_event_time)
    mock_repo.create_event.assert_awaited_with(
        workspace_id=workspace_id,
        run_id=run_id,
        event_type="research_ttfe",
        payload={
            "run_id": str(run_id),
            "event_time": naive_event_time.replace(tzinfo=timezone.utc).isoformat(),
        },
    )

    # Cost
    await service.track_cost(run_id, workspace_id, 0.085)
    call_args = mock_repo.create_event.await_args[1]
    assert call_args["event_type"] == "research_cost"
    assert call_args["payload"]["cost"] == 0.085

    # Failure
    await service.track_failures(run_id, workspace_id, "timeout", "Tool timed out after 30s")
    call_args2 = mock_repo.create_event.await_args[1]
    assert call_args2["event_type"] == "research_failure"
    assert call_args2["payload"]["failure_type"] == "timeout"
    assert call_args2["payload"]["error_message"] == "Tool timed out after 30s"


@pytest.mark.asyncio
async def test_get_observability_dashboard_data_aggregation():
    workspace_id = uuid.uuid4()

    # Setup mock runs
    t0 = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=10)
    t2 = t0 + timedelta(seconds=20)

    run_active = ResearchRun(
        run_id=uuid.uuid4(),
        workspace_id=workspace_id,
        owner_id=uuid.uuid4(),
        objective="Run 1",
        status="running",
        engine="open_deep_research",
        created_at=t0,
        updated_at=t1,
    )
    run_completed = ResearchRun(
        run_id=uuid.uuid4(),
        workspace_id=workspace_id,
        owner_id=uuid.uuid4(),
        objective="Run 2",
        status="completed",
        engine="open_deep_research",
        created_at=t0,
        updated_at=t2,
    )
    run_failed = ResearchRun(
        run_id=uuid.uuid4(),
        workspace_id=workspace_id,
        owner_id=uuid.uuid4(),
        objective="Run 3",
        status="aborted_by_timeline_fence",
        engine="open_deep_research",
        created_at=t0,
        updated_at=t1,
    )

    # Setup mock events for cost
    ev1 = ResearchEvent(
        event_id=uuid.uuid4(),
        run_id=run_completed.run_id,
        sequence=1,
        event_type="research_metrics",
        payload={"cost": 0.05},
    )
    ev2 = ResearchEvent(
        event_id=uuid.uuid4(),
        run_id=run_failed.run_id,
        sequence=1,
        event_type="research_metrics",
        payload={"cost": 0.025},
    )

    mock_session = AsyncMock()
    # Mocking two execute queries: first for runs, second for events
    run_res = MagicMock()
    run_res.scalars.return_value.all.return_value = [run_active, run_completed, run_failed]

    ev_res = MagicMock()
    ev_res.scalars.return_value.all.return_value = [ev1, ev2]

    mock_session.execute = AsyncMock(side_effect=[run_res, ev_res])

    mock_repo = MagicMock()
    mock_repo.session = mock_session

    service = ResearchMetricsService(repository=mock_repo)
    data = await service.get_observability_dashboard_data(workspace_id)

    assert data["workspace_id"] == str(workspace_id)
    assert data["active_runs"] == 1
    assert data["completed_runs"] == 1
    assert data["failed_runs"] == 1
    assert data["total_runs"] == 3
    # durations: 10, 20, 10 -> avg = 40 / 3 = 13.33
    assert data["average_duration"] == 13.33
    # cost: 0.05 + 0.025 = 0.075
    assert data["total_cost"] == 0.075
