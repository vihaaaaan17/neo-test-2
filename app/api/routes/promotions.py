from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from arq.connections import Redis

from app.core.database import get_db
from app.api.deps.auth import get_current_user
from app.api.deps.arq import get_arq_redis
from app.repositories.workspace import WorkspaceRepository
from app.repositories.research import ResearchRepository
from app.services.research.promotion import (
    PromotionService,
    CandidateNotFoundError,
    InvalidLifecycleTransitionError,
    PromotionError,
)
from app.services.research.derivation import CrossWorkspaceBoundaryError
from app.schemas.promotion import (
    PromotionCandidateResponse,
    PromotionReviewRequest,
    PromotionReviewResponse,
)

router = APIRouter()


async def _verify_workspace(workspace_id: UUID, user_id: UUID, session: AsyncSession):
    ws_repo = WorkspaceRepository(session)
    ws = await ws_repo.get_workspace(workspace_id, user_id)
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or access denied"
        )
    return ws


def _get_promotion_service(
    session: AsyncSession = Depends(get_db),
    arq_pool: Optional[Redis] = Depends(get_arq_redis),
) -> PromotionService:
    research_repo = ResearchRepository(session)
    return PromotionService(
        session=session,
        research_repo=research_repo,
        arq_pool=arq_pool,
    )


@router.get(
    "/workspaces/{workspace_id}/promotions",
    response_model=List[PromotionCandidateResponse],
    summary="List promotion candidates for a workspace"
)
async def list_promotions(
    workspace_id: UUID,
    status_filter: Optional[str] = Query(None, alias="status"),
    run_id: Optional[UUID] = Query(None),
    current_user: UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: PromotionService = Depends(_get_promotion_service),
):
    await _verify_workspace(workspace_id, current_user, session)
    candidates = await service.list_candidates(
        workspace_id=workspace_id,
        status=status_filter,
        run_id=run_id,
    )
    return candidates


@router.get(
    "/workspaces/{workspace_id}/promotions/{artifact_id}",
    response_model=PromotionCandidateResponse,
    summary="Get promotion candidate details"
)
async def get_promotion(
    workspace_id: UUID,
    artifact_id: UUID,
    current_user: UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: PromotionService = Depends(_get_promotion_service),
):
    await _verify_workspace(workspace_id, current_user, session)
    try:
        return await service.get_candidate(workspace_id, artifact_id)
    except CandidateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {artifact_id} not found in workspace"
        )


@router.post(
    "/workspaces/{workspace_id}/promotions/{artifact_id}/accept",
    response_model=PromotionReviewResponse,
    summary="Accept a promotion candidate"
)
async def accept_promotion(
    workspace_id: UUID,
    artifact_id: UUID,
    current_user: UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: PromotionService = Depends(_get_promotion_service),
):
    await _verify_workspace(workspace_id, current_user, session)
    try:
        candidate, target_id = await service.accept_candidate(
            workspace_id=workspace_id,
            artifact_id=artifact_id,
            user_id=current_user,
        )
        return PromotionReviewResponse(
            artifact_id=candidate.artifact_id,
            promotion_status=candidate.promotion_status,
            promoted_target_type=candidate.promoted_target_type,
            promoted_target_id=candidate.promoted_target_id,
            reviewed_at=candidate.reviewed_at,
            reviewed_by=candidate.reviewed_by,
            review_reason=candidate.review_reason,
        )
    except CandidateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {artifact_id} not found"
        )
    except InvalidLifecycleTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except CrossWorkspaceBoundaryError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cross-workspace lineage validation failed: {str(exc)}"
        )
    except PromotionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


@router.post(
    "/workspaces/{workspace_id}/promotions/{artifact_id}/reject",
    response_model=PromotionReviewResponse,
    summary="Reject a promotion candidate"
)
async def reject_promotion(
    workspace_id: UUID,
    artifact_id: UUID,
    payload: Optional[PromotionReviewRequest] = None,
    current_user: UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: PromotionService = Depends(_get_promotion_service),
):
    await _verify_workspace(workspace_id, current_user, session)
    reason = payload.review_reason if payload else None
    try:
        candidate = await service.reject_candidate(
            workspace_id=workspace_id,
            artifact_id=artifact_id,
            user_id=current_user,
            reason=reason,
        )
        return PromotionReviewResponse(
            artifact_id=candidate.artifact_id,
            promotion_status=candidate.promotion_status,
            promoted_target_type=candidate.promoted_target_type,
            promoted_target_id=candidate.promoted_target_id,
            reviewed_at=candidate.reviewed_at,
            reviewed_by=candidate.reviewed_by,
            review_reason=candidate.review_reason,
        )
    except CandidateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {artifact_id} not found"
        )
    except InvalidLifecycleTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except PromotionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
