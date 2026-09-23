"""
Load Benchmark Infrastructure (k6/Locust-style).

Validates admission control and queue backpressure by simulating
concurrent research requests at increasing load levels (10 -> 1000 users).

Usage:
    python scripts/load_benchmark.py --users 100 --duration 60
    python scripts/load_benchmark.py --users 500 --duration 120
"""

import asyncio
import json
import time
import argparse
import os
import sys
from pathlib import Path
from typing import Optional

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("load_benchmark")

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.integrations.research_engine.factory import ResearchEngineFactory
from app.services.research.admission import ResearchAdmissionController
from app.services.research.quota import ResearchQuotaService
from app.services.research.rate_limiter import ProviderRateLimiter
from app.repositories.research import ResearchRepository
from app.core.database import async_session_maker
from app.core.config import settings
from app.workers.settings import WorkerSettings


class LoadBenchmark:
    """
    Simulates concurrent research requests to validate admission control
    and queue backpressure.
    """

    def __init__(self, num_users: int, duration_seconds: int, workspace_id: str = None):
        self.num_users = num_users
        self.duration_seconds = duration_seconds
        self.workspace_id = workspace_id or str(__import__("uuid").uuid4())
        self.results = []
        self.start_time = None
        self.end_time = None
        self.admission_controller = None
        self.quota_service = None
        self.rate_limiter = None
        self.worker_settings = WorkerSettings()

    async def setup(self):
        """Initialize shared resources."""
        async with async_session_maker() as session:
            redis_client = None
            repository = ResearchRepository(session, redis_client)
            self.quota_service = ResearchQuotaService(repository)
            self.rate_limiter = ProviderRateLimiter(redis_client)
            self.admission_controller = ResearchAdmissionController(
                self.quota_service, self.rate_limiter, repository
            )

    async def simulate_user(self, user_id: int) -> dict:
        """Simulate a single user making a research request."""
        owner_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"user_{user_id}")
        workspace_uuid = uuid.UUID(str(self.workspace_id))
        objective = f"Benchmark test from user {user_id}"

        start = time.time()
        status = "unknown"
        error = None

        try:
            async with async_session_maker() as session:
                repository = ResearchRepository(session)
                quota_service = ResearchQuotaService(repository)
                rate_limiter = ProviderRateLimiter(None)
                admission_controller = ResearchAdmissionController(quota_service, rate_limiter, repository)

                # Check admission
                admitted = await admission_controller.admit_research_run(
                    workspace_id=workspace_uuid,
                    owner_id=owner_id,
                    objective=objective,
                    engine="open_deep_research",
                )
                status = "admitted"
        except Exception as e:
            status = "rejected"
            error = str(e)

        duration_ms = int((time.time() - start) * 1000)
        return {
            "user_id": user_id,
            "status": status,
            "duration_ms": duration_ms,
            "error": error,
        }

    async def run(self) -> list[dict]:
        """Run the load benchmark."""
        logger.info(f"Starting load benchmark: {self.num_users} users, {self.duration_seconds}s duration")

        await self.setup()
        self.start_time = time.time()

        # Create user tasks
        tasks = [self.simulate_user(i) for i in range(self.num_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        self.end_time = time.time()
        self.results = [r for r in results if isinstance(r, dict)]

        # Aggregate metrics
        admitted = sum(1 for r in self.results if r["status"] == "admitted")
        rejected = sum(1 for r in self.results if r["status"] == "rejected")
        total = len(self.results)
        duration = self.end_time - self.start_time

        metrics = {
            "total_users": total,
            "admitted": admitted,
            "rejected": rejected,
            "admission_rate": admitted / total if total > 0 else 0,
            "rejection_rate": rejected / total if total > 0 else 0,
            "duration_seconds": duration,
            "throughput_users_per_second": total / duration if duration > 0 else 0,
            "avg_duration_ms": sum(r["duration_ms"] for r in self.results) / total if total > 0 else 0,
            "p50_duration_ms": self._percentile(50),
            "p95_duration_ms": self._percentile(95),
            "p99_duration_ms": self._percentile(99),
        }

        logger.info(f"Load benchmark complete: {metrics}")
        return metrics

    def _percentile(self, p: int) -> float:
        """Calculate percentile duration."""
        durations = sorted(r["duration_ms"] for r in self.results)
        if not durations:
            return 0.0
        k = (len(durations) - 1) * (p / 100.0)
        f = int(k)
        c = f + 1 if f + 1 < len(durations) else f
        return durations[f] + (durations[c] - durations[f]) * (k - f)


async def main():
    parser = argparse.ArgumentParser(description="Run Load Benchmark")
    parser.add_argument("--users", type=int, default=100, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds")
    parser.add_argument("--output", type=str, default="tests/fixtures/benchmark/load_baseline.json", help="Output file")
    args = parser.parse_args()

    benchmark = LoadBenchmark(num_users=args.users, duration_seconds=args.duration)
    metrics = await benchmark.run()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info(f"Load benchmark results written to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())