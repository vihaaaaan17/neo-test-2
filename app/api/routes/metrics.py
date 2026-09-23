from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import Dict, Any
from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.services.research.metrics import ResearchMetricsService
from app.repositories.research import ResearchRepository
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("/workspaces/{workspace_id}/metrics", response_model=Dict[str, Any])
async def get_workspace_metrics(
    workspace_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Get observability metrics for a workspace.
    """
    repository = ResearchRepository(session)
    metrics_service = ResearchMetricsService(repository)

    metrics_data = await metrics_service.get_observability_dashboard_data(workspace_id)

    return {
        "workspace_id": str(workspace_id),
        "metrics": metrics_data,
        "status": "success"
    }