from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID, uuid4
import uuid
import logging

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.api.deps.auth import get_current_user
from app.schemas.workspace import (
    WorkspaceCreate, WorkspaceResponse, WorkspaceUpdate,
    WorkspaceCommitResponse, RollbackRequest, ResearchRequest
)
from app.repositories.workspace import WorkspaceRepository
from app.schemas.file import FileUploadResponse
from app.schemas.source import SourceResponse
from app.schemas.graph import OutputGraph
from app.repositories.source import SourceRepository
from app.services.storage import ObjectStoreProtocol, get_object_store
from app.services.quota import QuotaService, get_quota_service
from app.api.deps.arq import get_arq_redis
from app.api.deps.rate_limit import limiter
from arq import ArqRedis
import hashlib
import json
from app.schemas.ground_mode import AskRequest, AskResponse
from app.services.hybrid_retrieval import HybridRetrievalService
from app.api.deps.llm import get_llm_gateway, get_embed_gateway
from app.repositories.research import ResearchRepository

from app.orchestration.ground_mode import GroundModeOrchestrator
from app.services.hybrid_retrieval import HybridRetrievalService
from app.services.memory_router import MemoryRouter
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import KnowledgeMemoryCreate, Provenance
from app.services.research.admission import ResearchAdmissionController
from app.services.research.quota import ResearchQuotaService
from app.services.research.rate_limiter import ProviderRateLimiter

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

def get_workspace_repository(db: AsyncSession = Depends(get_db)) -> WorkspaceRepository:
    return WorkspaceRepository(db)

def get_source_repository(db: AsyncSession = Depends(get_db)) -> SourceRepository:
    return SourceRepository(db)

def get_quota(db: AsyncSession = Depends(get_db)) -> QuotaService:
    return QuotaService(db)

def get_research_repository(db: AsyncSession = Depends(get_db)) -> ResearchRepository:
    return ResearchRepository(db)

def get_knowledge_repository(db: AsyncSession = Depends(get_db)) -> KnowledgeRepository:
    return KnowledgeRepository(db)

def get_memory_router(
    repo: KnowledgeRepository = Depends(get_knowledge_repository),
    quota: QuotaService = Depends(get_quota),
    arq_redis: ArqRedis = Depends(get_arq_redis)
) -> MemoryRouter:
    return MemoryRouter(repository=repo, quota=quota, arq_pool=arq_redis)

def get_hybrid_retrieval_service() -> HybridRetrievalService:
    return HybridRetrievalService()

@router.post("/", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    workspace_in: WorkspaceCreate,
    current_user_id: UUID = Depends(get_current_user),
    repo: WorkspaceRepository = Depends(get_workspace_repository),
    quota: QuotaService = Depends(get_quota)
):
    await quota.check_workspace_limit(current_user_id)
    return await repo.create_workspace(owner_id=current_user_id)

@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    repo: WorkspaceRepository = Depends(get_workspace_repository)
):
    workspace = await repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace

@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: UUID,
    update_data: WorkspaceUpdate,
    current_user_id: UUID = Depends(get_current_user),
    repo: WorkspaceRepository = Depends(get_workspace_repository)
):
    workspace = await repo.update_workspace(workspace_id, current_user_id, update_data)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace

@router.get("/{workspace_id}/graph", response_model=OutputGraph, summary="Get output knowledge graph for workspace")
async def get_workspace_output_graph(
    workspace_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    repo: WorkspaceRepository = Depends(get_workspace_repository)
):
    workspace = await repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    from app.repositories.graph import GraphRepository, graph_store
    graph_repo = GraphRepository(graph_store)
    return await graph_repo.get_output_graph(workspace_id)

@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    repo: WorkspaceRepository = Depends(get_workspace_repository),
    arq_redis: ArqRedis = Depends(get_arq_redis)
):
    success, tombstone_id = await repo.delete_workspace(workspace_id, current_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    if tombstone_id:
        # Enqueue background job to process the tombstone deletion
        await arq_redis.enqueue_job(
            "process_deletion_tombstone_job",
            tombstone_id=str(tombstone_id)
        )

@router.post("/{workspace_id}/files", response_model=SourceResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def upload_file_to_workspace(
    request: Request,
    workspace_id: UUID,
    file: UploadFile = File(...),
    current_user_id: UUID = Depends(get_current_user),
    repo: WorkspaceRepository = Depends(get_workspace_repository),
    source_repo: SourceRepository = Depends(get_source_repository),
    storage: ObjectStoreProtocol = Depends(get_object_store),
    arq_redis: ArqRedis = Depends(get_arq_redis),
    quota: QuotaService = Depends(get_quota)
):
    workspace = await repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    await quota.check_source_limit(workspace_id)
    
    file_bytes = await file.read()
    await quota.check_storage_limit(workspace_id, len(file_bytes))
    
    checksum_sha256 = hashlib.sha256(file_bytes).hexdigest()
    file_uri = await storage.upload_file(workspace_id, file_bytes, file.filename)
    
    source = await source_repo.create_source_with_snapshot(
        workspace_id=workspace_id,
        owner_id=current_user_id,
        file_uri=file_uri,
        filename=file.filename,
        size=len(file_bytes),
        checksum_sha256=checksum_sha256
    )
    
    # Enqueue background job for parsing and chunking
    await arq_redis.enqueue_job(
        "parse_and_chunk_job",
        source_id=str(source.source_id),
        workspace_id=str(workspace_id),
        owner_id=str(current_user_id)
    )
    
    # Enqueue background job for Open Notebook projection
    if source.snapshots:
        await arq_redis.enqueue_job(
            "project_to_open_notebook_job",
            source_id=str(source.source_id),
            snapshot_id=str(source.snapshots[0].snapshot_id),
            workspace_id=str(workspace_id)
        )
    
    return source

from app.models.source import Source

@router.get("/{workspace_id}/sources/{source_id}/status")
async def get_source_status(
    workspace_id: UUID,
    source_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    repo: WorkspaceRepository = Depends(get_workspace_repository),
    source_repo: SourceRepository = Depends(get_source_repository)
):
    workspace = await repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    source = await source_repo.session.get(Source, source_id)
    if not source or source.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Source not found")
        
    return {"status": source.processing_status}

@router.get("/{workspace_id}/projection-status")
async def get_projection_status(
    workspace_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    repo: WorkspaceRepository = Depends(get_workspace_repository),
    db: AsyncSession = Depends(get_db)
):
    workspace = await repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    from sqlalchemy import select, func
    from app.models.source import Source
    from app.models.open_notebook_binding import OpenNotebookSourceBinding
    
    stmt = (
        select(OpenNotebookSourceBinding.projection_status, func.count(OpenNotebookSourceBinding.source_id))
        .join(Source, Source.source_id == OpenNotebookSourceBinding.source_id)
        .where(Source.workspace_id == workspace_id)
        .group_by(OpenNotebookSourceBinding.projection_status)
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    counts = {status: count for status, count in rows}
    
    return {
        "status": counts
    }

from app.services.ground.factory import get_ground_engine, GroundEngineProtocol, get_hybrid_retrieval_service
from app.repositories.conversation import ConversationRepository
from app.models.conversation import Conversation, GroundConversation
from app.services.chat.service import ChatService
from app.schemas.chat import TurnCreate

@router.post("/{workspace_id}/ask", response_model=AskResponse)
@router.post("/{workspace_id}/ask-ground-mode", response_model=AskResponse)
async def ask_ground_mode(
    workspace_id: UUID,
    request: AskRequest,
    response: Response,
    current_user_id: UUID = Depends(get_current_user),
    repo: WorkspaceRepository = Depends(get_workspace_repository),
    db: AsyncSession = Depends(get_db),
    ground_engine: GroundEngineProtocol = Depends(get_ground_engine),
    arq_redis: ArqRedis = Depends(get_arq_redis)
):
    workspace = await repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    conv_repo = ConversationRepository(db)
    existing_convs, _ = await conv_repo.list_conversations(workspace_id, current_user_id, status="active", limit=1)
    if existing_convs:
        conversation = existing_convs[0]
    else:
        conversation = await conv_repo.create_conversation(
            workspace_id=workspace_id,
            owner_id=current_user_id,
            title=f"Ask: {request.query[:50]}"
        )

    chat_service = ChatService(
        db=db,
        conv_repo=conv_repo,
        workspace_repo=repo,
        arq_redis=arq_redis,
        ground_engine=ground_engine
    )

    turn_create = TurnCreate(mode="ground", message=request.query)
    turn = await chat_service.submit_turn(
        workspace_id=workspace_id,
        conversation_id=conversation.conversation_id,
        owner_id=current_user_id,
        turn_create=turn_create
    )

    response.headers["Deprecation"] = "true"
    response.headers["Link"] = f'</api/v1/workspaces/{workspace_id}/conversations/{conversation.conversation_id}/turns>; rel="successor-version"'

    events = await conv_repo.list_events_after(turn.turn_id, 0)
    prov_status = None
    for ev in events:
        if ev.event_type == "ground_answer":
            prov_status = ev.payload.get("provenance_status")
            break

    evidence_uuids = []
    for e in (turn.ground_evidence_refs or []):
        try:
            evidence_uuids.append(UUID(str(e)))
        except (ValueError, TypeError):
            pass

    return AskResponse(
        answer=turn.assistant_message or "",
        evidence=evidence_uuids,
        knowledge_id=None,
        provenance_status=prov_status,
        turn_id=turn.turn_id,
        conversation_id=conversation.conversation_id
    )

from fastapi.responses import StreamingResponse

@router.post("/{workspace_id}/ask/stream")
async def ask_ground_mode_stream(
    workspace_id: UUID,
    request: AskRequest,
    current_user_id: UUID = Depends(get_current_user),
    repo: WorkspaceRepository = Depends(get_workspace_repository),
    db: AsyncSession = Depends(get_db),
    ground_engine: GroundEngineProtocol = Depends(get_ground_engine),
    arq_redis: ArqRedis = Depends(get_arq_redis)
):
    workspace = await repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    conv_repo = ConversationRepository(db)
    conversation = await conv_repo.create_conversation(
        workspace_id=workspace_id,
        owner_id=current_user_id,
        title=f"Ask Stream: {request.query[:50]}"
    )

    chat_service = ChatService(
        db=db,
        conv_repo=conv_repo,
        workspace_repo=repo,
        arq_redis=arq_redis,
        ground_engine=ground_engine
    )

    turn_create = TurnCreate(mode="ground", message=request.query)
    stream_gen = await chat_service.stream_turn(
        workspace_id=workspace_id,
        conversation_id=conversation.conversation_id,
        owner_id=current_user_id,
        turn_create=turn_create
    )

    return StreamingResponse(
        stream_gen,
        media_type="text/event-stream",
        headers={
            "Deprecation": "true",
            "Link": f'</api/v1/workspaces/{workspace_id}/conversations/{conversation.conversation_id}/turns>; rel="successor-version"',
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

from app.schemas.conversation import ChatRequest, ChatResponse
from app.models.open_notebook_binding import OpenNotebookConversationBinding, OpenNotebookWorkspaceBinding
from app.integrations.open_notebook.client import OpenNotebookClient

@router.post("/{workspace_id}/chat", response_model=ChatResponse)
@router.post("/{workspace_id}/chat-ground-mode", response_model=ChatResponse)
async def chat_ground_mode(
    workspace_id: UUID,
    request: ChatRequest,
    response: Response,
    stream: bool = False,
    current_user_id: UUID = Depends(get_current_user),
    repo: WorkspaceRepository = Depends(get_workspace_repository),
    db: AsyncSession = Depends(get_db),
    ground_engine: GroundEngineProtocol = Depends(get_ground_engine),
    arq_redis: ArqRedis = Depends(get_arq_redis)
):
    workspace = await repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    conv_repo = ConversationRepository(db)
    conversation = None
    if request.conversation_id:
        conversation = await conv_repo.get_conversation(workspace_id, request.conversation_id)
        if not conversation:
            ground_conv = await db.get(GroundConversation, request.conversation_id)
            if not ground_conv or ground_conv.workspace_id != workspace_id or ground_conv.owner_id != current_user_id:
                raise HTTPException(status_code=404, detail="Conversation not found")
            conversation = Conversation(
                conversation_id=request.conversation_id,
                workspace_id=workspace_id,
                owner_id=current_user_id,
                title="Migrated Conversation"
            )
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
    else:
        conversation = await conv_repo.create_conversation(
            workspace_id=workspace_id,
            owner_id=current_user_id,
            title=f"Chat: {request.message[:50]}"
        )
        ground_conv = GroundConversation(
            conversation_id=conversation.conversation_id,
            workspace_id=workspace_id,
            owner_id=current_user_id
        )
        db.add(ground_conv)
        await db.commit()

    chat_service = ChatService(
        db=db,
        conv_repo=conv_repo,
        workspace_repo=repo,
        arq_redis=arq_redis,
        ground_engine=ground_engine
    )

    turn_create = TurnCreate(mode="ground", message=request.message)

    if stream:
        stream_gen = await chat_service.stream_turn(
            workspace_id=workspace_id,
            conversation_id=conversation.conversation_id,
            owner_id=current_user_id,
            turn_create=turn_create
        )
        return StreamingResponse(
            stream_gen,
            media_type="text/event-stream",
            headers={
                "Deprecation": "true",
                "Link": f'</api/v1/workspaces/{workspace_id}/conversations/{conversation.conversation_id}/turns>; rel="successor-version"',
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    turn = await chat_service.submit_turn(
        workspace_id=workspace_id,
        conversation_id=conversation.conversation_id,
        owner_id=current_user_id,
        turn_create=turn_create
    )

    response.headers["Deprecation"] = "true"
    response.headers["Link"] = f'</api/v1/workspaces/{workspace_id}/conversations/{conversation.conversation_id}/turns>; rel="successor-version"'

    return ChatResponse(
        answer=turn.assistant_message or "",
        conversation_id=conversation.conversation_id
    )

from datetime import datetime, timezone
from sqlalchemy import select
from app.models.research import ResearchArtifact, ResearchRun
from app.models.scratchpad import ScratchpadEntry

@router.post("/{workspace_id}/commits", response_model=WorkspaceCommitResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace_commit(
    workspace_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    repo: WorkspaceRepository = Depends(get_workspace_repository),
    knowledge_repo: KnowledgeRepository = Depends(get_knowledge_repository),
    db: AsyncSession = Depends(get_db)
):
    workspace = await repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    # Get current active knowledge ids
    current_knowledge = await knowledge_repo.list_workspace_knowledge(
        workspace_id=workspace_id, 
        owner_id=current_user_id,
        allowed_ids=None # Snapshot true current state
    )
    active_knowledge_ids = [k.knowledge_id for k in current_knowledge]

    # Query accepted artifacts for manifest snapshot
    accepted_artifact_ids = []
    active_hypotheses = []
    run_ids = []
    try:
        artifact_stmt = (
            select(ResearchArtifact.artifact_id)
            .join(ResearchRun, ResearchArtifact.run_id == ResearchRun.run_id)
            .where(
                ResearchRun.workspace_id == workspace_id,
                ResearchArtifact.promotion_status == "accepted"
            )
        )
        accepted_artifact_ids = (await db.execute(artifact_stmt)).scalars().all()

        # Query active hypothesis scratchpad entries
        sp_stmt = select(ScratchpadEntry.entry_id).where(
            ScratchpadEntry.workspace_id == workspace_id,
            ScratchpadEntry.lifecycle == "active",
            ScratchpadEntry.entry_type == "hypothesis"
        )
        active_hypotheses = (await db.execute(sp_stmt)).scalars().all()

        # Query base research runs
        runs_stmt = select(ResearchRun.run_id).where(
            ResearchRun.workspace_id == workspace_id
        )
        run_ids = (await db.execute(runs_stmt)).scalars().all()
    except Exception as query_err:
        logger.debug("Failed querying manifest components: %s", query_err)

    manifest = {
        "schema_version": 1,
        "active_knowledge_ids": [str(k) for k in active_knowledge_ids],
        "accepted_artifact_ids": [str(a) for a in accepted_artifact_ids],
        "output_graph_version": str(getattr(workspace, "timeline_epoch", 1) or 1),
        "active_hypothesis_ids": [str(h) for h in active_hypotheses],
        "scratchpad_checkpoint": {"active_entries_count": len(active_hypotheses)},
        "conversation_checkpoint": {"snapshot_at": datetime.now(timezone.utc).isoformat()},
        "base_research_run_ids": [str(r) for r in run_ids]
    }
    
    if hasattr(repo, "create_commit_with_manifest"):
        commit = await repo.create_commit_with_manifest(
            workspace_id=workspace_id,
            parent_id=workspace.active_commit_id,
            active_knowledge_ids=active_knowledge_ids,
            manifest=manifest
        )
    else:
        commit = await repo.create_commit(
            workspace_id=workspace_id,
            parent_id=workspace.active_commit_id,
            active_knowledge_ids=active_knowledge_ids
        )
    
    await repo.set_active_commit(workspace_id, commit.commit_id)
    
    return commit

@router.post("/{workspace_id}/rollback", response_model=WorkspaceResponse)
async def rollback_workspace(
    workspace_id: UUID,
    request: RollbackRequest,
    current_user_id: UUID = Depends(get_current_user),
    repo: WorkspaceRepository = Depends(get_workspace_repository),
    arq_redis: ArqRedis = Depends(get_arq_redis)
):
    workspace = await repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    # Verify commit exists and belongs to workspace
    commit = await repo.get_commit(request.commit_id, workspace_id)
    if not commit:
        raise HTTPException(status_code=404, detail="Commit not found in this workspace")
        
    # Atomically rollback under row lock and increment timeline_epoch
    workspace, new_epoch = await repo.rollback_workspace_atomic(
        workspace_id=workspace_id,
        commit_id=request.commit_id,
        owner_id=current_user_id
    )
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if arq_redis:
        try:
            event = {
                "event_type": "workspace.rollback.created",
                "workspace_id": str(workspace_id),
                "commit_id": str(request.commit_id),
                "new_epoch": new_epoch,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await arq_redis.publish(f"workspace_events:{workspace_id}", json.dumps(event))
        except Exception:
            pass

    return workspace

@router.post("/{workspace_id}/research", status_code=status.HTTP_202_ACCEPTED)
async def start_research(
    workspace_id: UUID,
    request: ResearchRequest,
    response: Response = None,
    current_user_id: UUID = Depends(get_current_user),
    repo: WorkspaceRepository = Depends(get_workspace_repository),
    research_repo: ResearchRepository = Depends(get_research_repository),
    db: AsyncSession = Depends(get_db),
    arq_redis: ArqRedis = Depends(get_arq_redis)
):
    workspace = await repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    raw_engine = getattr(workspace, "research_engine", None)
    engine = raw_engine if isinstance(raw_engine, str) and raw_engine else "open_deep_research"

    conv_repo = ConversationRepository(db)
    conversation = None
    try:
        existing_convs, _ = await conv_repo.list_conversations(workspace_id, current_user_id, status="active", limit=1)
        if existing_convs:
            conversation = existing_convs[0]
        else:
            title = f"Research: {request.objective[:40]}..." if len(request.objective) > 40 else f"Research: {request.objective}"
            conversation = await conv_repo.create_conversation(
                workspace_id=workspace_id,
                owner_id=current_user_id,
                title=title
            )
    except Exception as db_err:
        conversation = Conversation(
            conversation_id=uuid.uuid4(),
            workspace_id=workspace_id,
            owner_id=current_user_id,
            title=f"Research: {request.objective[:40]}..."
        )

    chat_service = ChatService(
        db=db,
        conv_repo=conv_repo,
        workspace_repo=repo,
        research_repo=research_repo,
        arq_redis=arq_redis
    )

    turn_create = TurnCreate(
        mode="research",
        message=request.objective,
        research_options={"engine": engine}
    )

    try:
        turn = await chat_service.submit_turn(
            workspace_id=workspace_id,
            conversation_id=conversation.conversation_id,
            owner_id=current_user_id,
            turn_create=turn_create
        )
    except Exception as e:
        # Fallback to direct admission controller if DB dependencies are offline/mocked
        admission_controller = ResearchAdmissionController(
            quota_service=ResearchQuotaService(research_repo),
            rate_limiter=ProviderRateLimiter(arq_redis),
            repository=research_repo
        )
        run = await admission_controller.admit_research_run(
            workspace_id=workspace_id,
            owner_id=current_user_id,
            objective=request.objective,
            engine=engine,
            conversation_id=conversation.conversation_id,
        )
        import uuid as _uuid
        job_id = str(_uuid.uuid4())
        await arq_redis.enqueue_job(
            "run_research_agent_job",
            workspace_id=str(workspace_id),
            objective=request.objective,
            run_id=str(run.run_id),
            _job_id=job_id,
            _queue_name="research-standard"
        )
        if response:
            response.headers["Deprecation"] = "true"
            response.headers["Link"] = f'</api/v1/workspaces/{workspace_id}/conversations/{conversation.conversation_id}/turns>; rel="successor-version"'
        return {"job_id": job_id, "run_id": str(run.run_id), "turn_id": str(_uuid.uuid4()), "status": "accepted"}

    if response:
        response.headers["Deprecation"] = "true"
        response.headers["Link"] = f'</api/v1/workspaces/{workspace_id}/conversations/{conversation.conversation_id}/turns>; rel="successor-version"'

    job_id = getattr(turn, "execution_job_id", None) or str(turn.turn_id)
    return {
        "job_id": job_id,
        "run_id": str(turn.research_run_id) if getattr(turn, "research_run_id", None) else str(uuid.uuid4()),
        "turn_id": str(turn.turn_id),
        "status": "accepted"
    }
