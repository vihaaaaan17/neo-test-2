from fastapi import APIRouter, Depends, HTTPException, status, Response
from uuid import UUID
from typing import Dict, Any, Optional
from app.api.deps.auth import get_current_user
from app.api.deps.arq import get_arq_redis
from app.core.database import get_db
from app.repositories.research import ResearchRepository
from app.models.research import ResearchRun
from app.schemas.research import ResearchRunResponse
from app.services.chat.service import ChatService
from app.repositories.conversation import ConversationRepository
from app.schemas.chat import TurnCreate
from app.services.research.admission import ResearchAdmissionController
from app.services.research.quota import ResearchQuotaService
from app.services.research.rate_limiter import ProviderRateLimiter
from arq.connections import Redis
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/workspaces/{workspace_id}/research", response_model=ResearchRunResponse)
async def create_research_run(
    workspace_id: UUID,
    objective: str,
    engine: str = "open_deep_research",
    engine_revision: Optional[str] = None,
    conversation_id: Optional[UUID] = None,
    response: Response = None,
    current_user: Any = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_arq_redis),
):
    """
    Create a new research run (legacy route).
    Delegates to ChatService.submit_turn(mode="research") to ensure canonical turn fabric.
    """
    conv_repo = ConversationRepository(session)
    chat_service = ChatService(
        db=session,
        arq_redis=redis_client
    )

    # 1. Resolve or create conversation
    if conversation_id:
        conv = await conv_repo.get_conversation(workspace_id, conversation_id)
        if not conv or conv.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Conversation not found or access denied")
    else:
        title = f"Research: {objective[:40]}..." if len(objective) > 40 else f"Research: {objective}"
        conv = await conv_repo.create_conversation(
            workspace_id=workspace_id,
            owner_id=current_user.id,
            title=title
        )
        conversation_id = conv.conversation_id

    # 2. Submit research turn
    turn_create = TurnCreate(
        message=objective,
        mode="research",
        research_options={"engine": engine, "engine_revision": engine_revision}
    )
    turn = await chat_service.submit_turn(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        owner_id=current_user.id,
        turn_create=turn_create
    )

    # 3. Add RFC 8288 deprecation headers
    if response:
        response.headers["Deprecation"] = "true"
        response.headers["Link"] = f'</api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns>; rel="successor-version"'

    # 4. Fetch and return ResearchRun
    research_repo = ResearchRepository(session, redis_client)
    run = await research_repo.get_run(workspace_id=workspace_id, run_id=turn.research_run_id)
    if not run:
        raise HTTPException(status_code=500, detail="ResearchRun was not created for turn")
    return run

@router.get("/workspaces/{workspace_id}/research/queue-status", response_model=Dict[str, Any])
async def get_queue_status(
    workspace_id: UUID,
    current_user: Any = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_arq_redis),
):
    """
    Get the current queue status.
    """
    repository = ResearchRepository(session, redis_client)
    quota_service = ResearchQuotaService(repository)
    rate_limiter = ProviderRateLimiter(redis_client)
    admission_controller = ResearchAdmissionController(quota_service, rate_limiter, repository)

    return await admission_controller.get_queue_status()