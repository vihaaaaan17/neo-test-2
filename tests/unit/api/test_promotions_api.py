import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import HTTPException

from app.api.routes.promotions import (
    list_promotions,
    get_promotion,
    accept_promotion,
    reject_promotion,
)
from app.models.research import ResearchArtifact
from app.models.workspace import Workspace
from app.schemas.promotion import PromotionReviewRequest


@pytest.mark.asyncio
async def test_list_promotions_route():
    workspace_id = uuid4()
    user_id = uuid4()
    mock_ws = Workspace(workspace_id=workspace_id, owner_id=user_id)

    mock_candidates = [
        ResearchArtifact(
            artifact_id=uuid4(),
            run_id=uuid4(),
            type="memory_candidate",
            payload={"text": "Candidate 1"},
            promotion_status="pending_review",
            created_at=datetime.now(timezone.utc)
        )
    ]

    mock_service = MagicMock()
    mock_service.list_candidates = AsyncMock(return_value=mock_candidates)
    mock_session = AsyncMock()

    with patch("app.api.routes.promotions.WorkspaceRepository") as mock_ws_repo_cls:
        mock_ws_repo = mock_ws_repo_cls.return_value
        mock_ws_repo.get_workspace = AsyncMock(return_value=mock_ws)

        res = await list_promotions(
            workspace_id=workspace_id,
            status_filter="pending_review",
            run_id=None,
            current_user=user_id,
            session=mock_session,
            service=mock_service
        )

        assert len(res) == 1
        assert res[0].promotion_status == "pending_review"
        assert res[0].type == "memory_candidate"


@pytest.mark.asyncio
async def test_get_promotion_route():
    workspace_id = uuid4()
    user_id = uuid4()
    artifact_id = uuid4()
    mock_ws = Workspace(workspace_id=workspace_id, owner_id=user_id)

    mock_candidate = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=uuid4(),
        type="graph_candidate",
        payload={"nodes": []},
        promotion_status="pending_review",
        created_at=datetime.now(timezone.utc)
    )

    mock_service = MagicMock()
    mock_service.get_candidate = AsyncMock(return_value=mock_candidate)
    mock_session = AsyncMock()

    with patch("app.api.routes.promotions.WorkspaceRepository") as mock_ws_repo_cls:
        mock_ws_repo = mock_ws_repo_cls.return_value
        mock_ws_repo.get_workspace = AsyncMock(return_value=mock_ws)

        res = await get_promotion(
            workspace_id=workspace_id,
            artifact_id=artifact_id,
            current_user=user_id,
            session=mock_session,
            service=mock_service
        )

        assert res.artifact_id == artifact_id
        assert res.type == "graph_candidate"


@pytest.mark.asyncio
async def test_accept_promotion_route():
    workspace_id = uuid4()
    user_id = uuid4()
    artifact_id = uuid4()
    target_id = uuid4()
    now = datetime.now(timezone.utc)
    mock_ws = Workspace(workspace_id=workspace_id, owner_id=user_id)

    mock_candidate = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=uuid4(),
        type="memory_candidate",
        payload={"text": "Accepted item"},
        promotion_status="accepted",
        promoted_target_type="knowledge_memory",
        promoted_target_id=target_id,
        reviewed_by=user_id,
        reviewed_at=now,
        created_at=now
    )

    mock_service = MagicMock()
    mock_service.accept_candidate = AsyncMock(return_value=(mock_candidate, target_id))
    mock_session = AsyncMock()

    with patch("app.api.routes.promotions.WorkspaceRepository") as mock_ws_repo_cls:
        mock_ws_repo = mock_ws_repo_cls.return_value
        mock_ws_repo.get_workspace = AsyncMock(return_value=mock_ws)

        res = await accept_promotion(
            workspace_id=workspace_id,
            artifact_id=artifact_id,
            current_user=user_id,
            session=mock_session,
            service=mock_service
        )

        assert res.artifact_id == artifact_id
        assert res.promotion_status == "accepted"
        assert res.promoted_target_type == "knowledge_memory"
        assert res.promoted_target_id == target_id


@pytest.mark.asyncio
async def test_reject_promotion_route():
    workspace_id = uuid4()
    user_id = uuid4()
    artifact_id = uuid4()
    now = datetime.now(timezone.utc)
    mock_ws = Workspace(workspace_id=workspace_id, owner_id=user_id)

    mock_candidate = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=uuid4(),
        type="claim_candidate",
        payload={"claim": "Unproven assertion"},
        promotion_status="rejected",
        reviewed_by=user_id,
        reviewed_at=now,
        review_reason="Rejected after verification audit",
        created_at=now
    )

    mock_service = MagicMock()
    mock_service.reject_candidate = AsyncMock(return_value=mock_candidate)
    mock_session = AsyncMock()

    with patch("app.api.routes.promotions.WorkspaceRepository") as mock_ws_repo_cls:
        mock_ws_repo = mock_ws_repo_cls.return_value
        mock_ws_repo.get_workspace = AsyncMock(return_value=mock_ws)

        payload = PromotionReviewRequest(
            decision="reject",
            review_reason="Rejected after verification audit"
        )

        res = await reject_promotion(
            workspace_id=workspace_id,
            artifact_id=artifact_id,
            payload=payload,
            current_user=user_id,
            session=mock_session,
            service=mock_service
        )

        assert res.artifact_id == artifact_id
        assert res.promotion_status == "rejected"
        assert res.review_reason == "Rejected after verification audit"


@pytest.mark.asyncio
async def test_promotion_route_workspace_not_found():
    workspace_id = uuid4()
    user_id = uuid4()
    mock_session = AsyncMock()
    mock_service = MagicMock()

    with patch("app.api.routes.promotions.WorkspaceRepository") as mock_ws_repo_cls:
        mock_ws_repo = mock_ws_repo_cls.return_value
        mock_ws_repo.get_workspace = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await list_promotions(
                workspace_id=workspace_id,
                current_user=user_id,
                session=mock_session,
                service=mock_service
            )

        assert exc_info.value.status_code == 404
