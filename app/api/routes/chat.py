from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from arq.connections import ArqRedis

from app.core.database import get_db
from app.api.deps.auth import get_current_user
from app.api.deps.arq import get_arq_redis
from app.repositories.workspace import WorkspaceRepository
from app.repositories.conversation import ConversationRepository
from app.services.chat.service import ChatService
from app.services.chat.events import format_sse_event
from app.schemas.chat import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationListResponse,
    TurnCreate,
    TurnResponse,
    TurnListResponse,
    ChatEventResponse,
    ChatEventListResponse
)

router = APIRouter(prefix="/workspaces/{workspace_id}/conversations", tags=["conversations"])


def get_workspace_repository(db: AsyncSession = Depends(get_db)) -> WorkspaceRepository:
    return WorkspaceRepository(db)


def get_conversation_repository(db: AsyncSession = Depends(get_db)) -> ConversationRepository:
    return ConversationRepository(db)


from app.services.ground.factory import get_ground_engine, GroundEngineProtocol


def get_chat_service(
    db: AsyncSession = Depends(get_db),
    conv_repo: ConversationRepository = Depends(get_conversation_repository),
    workspace_repo: WorkspaceRepository = Depends(get_workspace_repository),
    arq_redis: Optional[ArqRedis] = Depends(get_arq_redis),
    ground_engine: Optional[GroundEngineProtocol] = Depends(get_ground_engine)
) -> ChatService:
    return ChatService(
        db=db,
        conv_repo=conv_repo,
        workspace_repo=workspace_repo,
        arq_redis=arq_redis,
        ground_engine=ground_engine
    )


async def _verify_workspace_access(
    workspace_id: UUID,
    current_user_id: UUID,
    workspace_repo: WorkspaceRepository
):
    workspace = await workspace_repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or access denied"
        )
    return workspace


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation in workspace"
)
async def create_conversation(
    workspace_id: UUID,
    request: ConversationCreate,
    current_user_id: UUID = Depends(get_current_user),
    workspace_repo: WorkspaceRepository = Depends(get_workspace_repository),
    conv_repo: ConversationRepository = Depends(get_conversation_repository)
):
    await _verify_workspace_access(workspace_id, current_user_id, workspace_repo)
    conversation = await conv_repo.create_conversation(
        workspace_id=workspace_id,
        owner_id=current_user_id,
        title=request.title,
        metadata=request.metadata
    )
    return conversation


@router.get(
    "",
    response_model=ConversationListResponse,
    summary="List conversations in workspace"
)
async def list_conversations(
    workspace_id: UUID,
    status_filter: Optional[str] = Query("active", alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user_id: UUID = Depends(get_current_user),
    workspace_repo: WorkspaceRepository = Depends(get_workspace_repository),
    conv_repo: ConversationRepository = Depends(get_conversation_repository)
):
    await _verify_workspace_access(workspace_id, current_user_id, workspace_repo)
    conversations, total = await conv_repo.list_conversations(
        workspace_id=workspace_id,
        owner_id=current_user_id,
        status=status_filter,
        limit=limit,
        offset=offset
    )
    return ConversationListResponse(conversations=conversations, total=total)


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get conversation by ID"
)
async def get_conversation(
    workspace_id: UUID,
    conversation_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    workspace_repo: WorkspaceRepository = Depends(get_workspace_repository),
    conv_repo: ConversationRepository = Depends(get_conversation_repository)
):
    await _verify_workspace_access(workspace_id, current_user_id, workspace_repo)
    conversation = await conv_repo.get_conversation(workspace_id, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    if conversation.owner_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to conversation"
        )
    return conversation


@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Update or archive conversation"
)
async def update_conversation(
    workspace_id: UUID,
    conversation_id: UUID,
    request: ConversationUpdate,
    current_user_id: UUID = Depends(get_current_user),
    workspace_repo: WorkspaceRepository = Depends(get_workspace_repository),
    conv_repo: ConversationRepository = Depends(get_conversation_repository)
):
    await _verify_workspace_access(workspace_id, current_user_id, workspace_repo)
    existing = await conv_repo.get_conversation(workspace_id, conversation_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    if existing.owner_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to conversation"
        )

    updated = await conv_repo.update_conversation(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        title=request.title,
        status=request.status,
        metadata=request.metadata
    )
    return updated


# ============================================================================ #
# Turn Execution & Retrieval Endpoints
# ============================================================================ #

@router.post(
    "/{conversation_id}/turns",
    summary="Submit and execute a conversation turn"
)
async def submit_turn(
    workspace_id: UUID,
    conversation_id: UUID,
    request: TurnCreate,
    response: Response,
    stream: bool = Query(False, description="Stream events via SSE"),
    current_user_id: UUID = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    if stream:
        event_gen = await chat_service.stream_turn(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            owner_id=current_user_id,
            turn_create=request
        )
        return StreamingResponse(
            event_gen,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    turn = await chat_service.submit_turn(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        owner_id=current_user_id,
        turn_create=request,
        stream=False
    )
    if turn.mode == "research" or turn.status in ["running", "pending"]:
        response.status_code = status.HTTP_202_ACCEPTED
    else:
        response.status_code = status.HTTP_200_OK
    return TurnResponse.model_validate(turn)


@router.get(
    "/{conversation_id}/turns",
    response_model=TurnListResponse,
    summary="List turns in conversation"
)
async def list_turns(
    workspace_id: UUID,
    conversation_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user_id: UUID = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    turns, total = await chat_service.list_turns(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        owner_id=current_user_id,
        limit=limit,
        offset=offset
    )
    return TurnListResponse(turns=turns, total=total)


@router.get(
    "/{conversation_id}/turns/{turn_id}",
    response_model=TurnResponse,
    summary="Get turn by ID"
)
async def get_turn(
    workspace_id: UUID,
    conversation_id: UUID,
    turn_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    turn = await chat_service.get_turn(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        turn_id=turn_id,
        owner_id=current_user_id
    )
    return turn


@router.get(
    "/{conversation_id}/turns/{turn_id}/events",
    response_model=ChatEventListResponse,
    summary="Replay historical events for a turn"
)
async def list_turn_events(
    workspace_id: UUID,
    conversation_id: UUID,
    turn_id: UUID,
    after_sequence: int = Query(0, ge=0, description="Retrieve events strictly after sequence number"),
    stream: bool = Query(False, description="Stream events as SSE instead of JSON"),
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
    current_user_id: UUID = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    # Resolve reconnect cursor: Last-Event-ID header takes precedence over QS param
    cursor: int = after_sequence
    if last_event_id is not None:
        try:
            cursor = int(last_event_id)
        except (ValueError, TypeError):
            pass  # malformed header — fall back to query param

    # Always validate workspace + conversation + turn ownership
    await chat_service.get_turn_events(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        turn_id=turn_id,
        owner_id=current_user_id,
        after_sequence=cursor,
    )

    if stream:
        return StreamingResponse(
            chat_service.stream_turn_events(turn_id, after_sequence=cursor),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    events = await chat_service.event_repo.list_events_after(turn_id, after_sequence=cursor)
    return ChatEventListResponse(
        events=[ChatEventResponse.model_validate(ev) for ev in events],
        total=len(events)
    )


@router.post(
    "/{conversation_id}/turns/{turn_id}/cancel",
    response_model=TurnResponse,
    summary="Cancel an in-flight conversation turn"
)
async def cancel_turn(
    workspace_id: UUID,
    conversation_id: UUID,
    turn_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    turn = await chat_service.cancel_turn(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        turn_id=turn_id,
        owner_id=current_user_id
    )
    return TurnResponse.model_validate(turn)



DEFAULT_STUDY_REPORT_REQUEST = "Compile everything we've discussed in this study session into a research paper."


@router.post(
    "/{conversation_id}/study-report",
    summary="Compile the conversation into a cited study-session paper (explicit request)"
)
async def compile_study_report(
    workspace_id: UUID,
    conversation_id: UUID,
    body: Optional[dict] = None,
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    workspace_repo: WorkspaceRepository = Depends(get_workspace_repository),
    conv_repo: ConversationRepository = Depends(get_conversation_repository)
):
    """
    Runs the StudyReportCompiler over this conversation only: its completed turns, the workspace sources its Ground turns
    cited, the evidence its Research runs collected and its scratchpad notes. No research is run. Creates one
    study-session ResearchReport and one pending_review memory candidate; nothing is promoted.
    """
    from app.services.research.study_report import StudyReportCompiler, StudySessionEmpty, StudySessionNotFound

    await _verify_workspace_access(workspace_id, current_user_id, workspace_repo)
    request = ((body or {}).get("request") or DEFAULT_STUDY_REPORT_REQUEST).strip()
    try:
        # The compiler itself enforces workspace + owner scoping (service layer), not only this route.
        return await StudyReportCompiler(db).compile(workspace_id=workspace_id, conversation_id=conversation_id,
                                                     request=request, owner_id=current_user_id)
    except StudySessionNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    except StudySessionEmpty:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="study_session_empty")


@router.get(
    "/{conversation_id}/study-reports",
    summary="List the study-session papers compiled for this conversation"
)
async def list_study_reports(
    workspace_id: UUID,
    conversation_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    workspace_repo: WorkspaceRepository = Depends(get_workspace_repository),
    conv_repo: ConversationRepository = Depends(get_conversation_repository)
):
    from sqlalchemy import select
    from app.models.research import ResearchReport

    await _verify_workspace_access(workspace_id, current_user_id, workspace_repo)
    conversation = await conv_repo.get_conversation(workspace_id, conversation_id)
    if not conversation or conversation.owner_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    rows = (await db.execute(
        select(ResearchReport)
        .where(ResearchReport.scope == "study_session", ResearchReport.workspace_id == workspace_id,
               ResearchReport.conversation_id == conversation_id)
        .order_by(ResearchReport.created_at.desc())
    )).scalars().all()
    return {"items": [_study_report_dict(r) for r in rows]}


def _study_report_dict(r) -> dict:
    return {
        "report_id": str(r.report_id), "version": r.version, "objective": r.objective, "content": r.content,
        "citations": r.citations, "source_summary": r.source_summary, "warnings": r.warnings,
        "limitations": r.limitations, "status": r.status, "created_at": r.created_at.isoformat(),
    }


@router.get(
    "/{conversation_id}/study-reports/{report_id}",
    summary="Get one study-session paper of this conversation"
)
async def get_study_report(
    workspace_id: UUID,
    conversation_id: UUID,
    report_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    workspace_repo: WorkspaceRepository = Depends(get_workspace_repository),
    conv_repo: ConversationRepository = Depends(get_conversation_repository)
):
    from sqlalchemy import select
    from app.models.research import ResearchReport

    await _verify_workspace_access(workspace_id, current_user_id, workspace_repo)
    conversation = await conv_repo.get_conversation(workspace_id, conversation_id)
    if not conversation or conversation.owner_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    report = (await db.execute(
        select(ResearchReport).where(ResearchReport.report_id == report_id, ResearchReport.scope == "study_session",
                                     ResearchReport.workspace_id == workspace_id,
                                     ResearchReport.conversation_id == conversation_id)
    )).scalars().first()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study report not found")
    return _study_report_dict(report)
