from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from app.workers.settings import WorkerSettings

router = APIRouter()

@router.get("/worker-pool-status", response_model=Dict[str, Any])
def get_worker_pool_status() -> Dict[str, Any]:
    """
    Get the current status of worker pools and queues.
    """
    worker_settings = WorkerSettings()

    queue_status = {}
    for queue_name, queue_config in worker_settings.QUEUES.items():
        queue_status[queue_name] = {
            "max_jobs": queue_config.get("max_jobs", 0),
            "functions": [func.__name__ for func in queue_config.get("functions", [])],
            "queue_name": queue_config.get("queue_name", queue_name)
        }

    return {
        "status": "active",
        "queues": queue_status,
        "message": "Worker pools are isolated and segregated"
    }