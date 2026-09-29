import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy import select, func

from app.repositories.research import ResearchRepository
from app.models.research import ResearchRun, ResearchEvent
from app.services.research.budget import UsageTracker

logger = logging.getLogger(__name__)


class ResearchMetricsService:
    """
    Service to emit structured metrics for research observability.
    Tracks wait time, time-to-first-event (TTFE), latency, tokens, tool call counts, cost, and failures.
    Enforces timezone.utc across all temporal operations.
    """

    def __init__(self, repository: ResearchRepository):
        self.repository = repository

    async def emit_metrics(
        self,
        run_id: UUID,
        workspace_id: UUID,
        status: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        usage_metrics: Optional[Dict[str, Any]] = None,
        failures: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Emits structured metrics with real runtime execution values.
        """
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        elif end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)

        duration_seconds = max((end_time - start_time).total_seconds(), 0.0)
        latency_ms = duration_seconds * 1000.0

        u_metrics = usage_metrics or {}
        wait_time_seconds = float(u_metrics.get("wait_time_seconds", 0.0))
        time_to_first_event_seconds = float(u_metrics.get("time_to_first_event_seconds", u_metrics.get("ttfe", 0.0)))
        tool_call_count = int(u_metrics.get("tool_call_count", u_metrics.get("tool_calls", 0)))
        cost = float(u_metrics.get("cost", 0.0))

        raw_tokens = u_metrics.get("tokens")
        if isinstance(raw_tokens, dict):
            tokens = {
                "prompt_tokens": int(raw_tokens.get("prompt_tokens", raw_tokens.get("prompt", 0))),
                "completion_tokens": int(raw_tokens.get("completion_tokens", raw_tokens.get("completion", 0))),
                "total_tokens": int(raw_tokens.get("total_tokens", raw_tokens.get("total", 0))),
            }
        else:
            total_toks = int(u_metrics.get("total_tokens", raw_tokens or 0))
            prompt_toks = int(u_metrics.get("prompt_tokens", 0))
            comp_toks = int(u_metrics.get("completion_tokens", total_toks - prompt_toks if total_toks >= prompt_toks else 0))
            tokens = {
                "prompt_tokens": prompt_toks,
                "completion_tokens": comp_toks,
                "total_tokens": total_toks,
            }

        metrics = {
            "run_id": str(run_id),
            "workspace_id": str(workspace_id),
            "status": status,
            "duration_seconds": duration_seconds,
            "latency_ms": latency_ms,
            "wait_time_seconds": wait_time_seconds,
            "time_to_first_event_seconds": time_to_first_event_seconds,
            "tokens": tokens,
            "tool_call_count": tool_call_count,
            "cost": cost,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "failures": failures or {}
        }

        # Log metrics
        logger.info(f"Research metrics for run {run_id}: {metrics}")

        # Store metrics in ResearchEvent
        await self.repository.create_event(
            workspace_id=workspace_id,
            run_id=run_id,
            event_type="research_metrics",
            payload=metrics
        )

        return metrics

    async def track_time_to_first_event(self, run_id: UUID, workspace_id: UUID, event_time: datetime) -> None:
        """
        Tracks the time-to-first-event (TTFE) for a research run.
        """
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)
        payload = {
            "run_id": str(run_id),
            "event_time": event_time.isoformat()
        }
        await self.repository.create_event(
            workspace_id=workspace_id,
            run_id=run_id,
            event_type="research_ttfe",
            payload=payload
        )

    async def track_cost(self, run_id: UUID, workspace_id: UUID, cost: float) -> None:
        """
        Tracks the cost of a research run.
        """
        payload = {
            "run_id": str(run_id),
            "cost": cost,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.repository.create_event(
            workspace_id=workspace_id,
            run_id=run_id,
            event_type="research_cost",
            payload=payload
        )

    async def track_failures(self, run_id: UUID, workspace_id: UUID, failure_type: str, error_message: str) -> None:
        """
        Tracks failures for a research run.
        """
        failure_metrics = {
            "failure_type": failure_type,
            "error_message": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        await self.repository.create_event(
            workspace_id=workspace_id,
            run_id=run_id,
            event_type="research_failure",
            payload=failure_metrics
        )

    async def get_observability_dashboard_data(self, workspace_id: UUID) -> Dict[str, Any]:
        """
        Retrieves real observability dashboard data for a workspace.
        """
        active_runs = 0
        completed_runs = 0
        failed_runs = 0
        total_cost = 0.0
        durations = []

        try:
            stmt = select(ResearchRun).where(ResearchRun.workspace_id == workspace_id)
            res = await self.repository.session.execute(stmt)
            runs = list(res.scalars().all())

            for r in runs:
                if r.status in ("pending", "running"):
                    active_runs += 1
                elif r.status in ("completed", "accepted"):
                    completed_runs += 1
                elif r.status in ("failed", "aborted_by_timeline_fence"):
                    failed_runs += 1

                if r.created_at and r.updated_at:
                    durations.append((r.updated_at - r.created_at).total_seconds())

            # Query cost from research_metrics events across workspace runs
            run_ids = [r.run_id for r in runs]
            if run_ids:
                ev_stmt = select(ResearchEvent).where(
                    ResearchEvent.run_id.in_(run_ids),
                    ResearchEvent.event_type == "research_metrics"
                )
                ev_res = await self.repository.session.execute(ev_stmt)
                for ev in ev_res.scalars().all():
                    payload = ev.payload or {}
                    total_cost += float(payload.get("cost", 0.0))
        except Exception as e:
            logger.debug("Failed querying aggregate dashboard data: %s", e)

        avg_duration = sum(durations) / len(durations) if durations else 0.0

        return {
            "workspace_id": str(workspace_id),
            "active_runs": active_runs,
            "completed_runs": completed_runs,
            "failed_runs": failed_runs,
            "total_runs": active_runs + completed_runs + failed_runs,
            "average_duration": round(avg_duration, 2),
            "total_cost": round(total_cost, 4)
        }