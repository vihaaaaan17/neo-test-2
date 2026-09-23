from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.api.deps.auth import get_current_user
from app.schemas.workspace import (
    WorkspaceCreate, WorkspaceResponse, WorkspaceUpdate,
    WorkspaceCommitResponse, RollbackRequest, ResearchRequest
)
from app.repositories.workspace import WorkspaceRepository
from app.schemas.file import FileUploadResponse
from app.schemas.source import SourceResponse
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
        select(OpenNotebookSourceBinding.status, func.count(OpenNotebookSourceBinding.source_id))
        .join(Source, Source.source_id == OpenNotebookSourceBinding.source_id)
        .where(Source.workspace_id == workspace_id)
        .group_by(OpenNotebookSourceBinding.status)
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    counts = {status: count for status, count in rows}
    
    return {
        "status": counts
    }

from app.services.ground.factory import get_ground_engine, GroundEngineProtocol

@router.post("/{workspace_id}/ask", response_model=AskResponse)
async def ask_ground_mode(
    workspace_id: UUID,
    request: AskRequest,
    current_user_id: UUID = Depends(get_current_user),
    repo: WorkspaceRepository = Depends(get_workspace_repository),
    db: AsyncSession = Depends(get_db),
    memory_router: MemoryRouter = Depends(get_memory_router),
    ground_engine: GroundEngineProtocol = Depends(get_ground_engine)
):
    workspace = await repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # The ground engine abstracts away the feature flag check
    state = await ground_engine.run(workspace_id=workspace_id, query=request.query, db=db)
    
    if not state.get("is_grounded", False):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail="Unable to generate a grounded answer from the provided context."
        )

    # Check for legacy engine mapping
    evidence_uuids = []
    if "context_docs" in state:
        evidence_uuids = [doc["id"] for doc in state["context_docs"] if "id" in doc]
    elif "evidence" in state:
        evidence_uuids = state["evidence"]
        
    memory_data = KnowledgeMemoryCreate(
        knowledge_type="answer",
        content=state["answer"],
        status="verified",
        provenance=Provenance(
            source_refs=evidence_uuids,
            source_mode="ground"
        ),
        domain="qa"
    )
    
    # Store answer and enqueue graph sync via memory router
    memory = await memory_router.route_to_memory(
        owner_id=current_user_id,
        workspace_id=workspace_id,
        data=memory_data
    )
    
    return AskResponse(
        answer=state["answer"],
        evidence=evidence_uuids,
        knowledge_id=memory.knowledge_id,
        provenance_status=state.get("provenance_status")
    )

from fastapi.responses import StreamingResponse

@router.post("/{workspace_id}/ask/stream")
async def ask_ground_mode_stream(
    workspace_id: UUID,
    request: AskRequest,
    current_user_id: UUID = Depends(get_current_user),
    repo: WorkspaceRepository = Depends(get_workspace_repository),
    db: AsyncSession = Depends(get_db),
    ground_engine: GroundEngineProtocol = Depends(get_ground_engine)
):
    from app.core.config import settings
    if not settings.OPEN_NOTEBOOK_ENABLED:
        raise HTTPException(status_code=501, detail="Streaming is only supported when Open Notebook is enabled.")
        
    workspace = await repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    # Verify the workspace has an active Open Notebook binding
    from sqlalchemy import select
    from app.models.open_notebook_binding import OpenNotebookWorkspaceBinding
    stmt = select(OpenNotebookWorkspaceBinding).where(
        OpenNotebookWorkspaceBinding.workspace_id == workspace_id,
        OpenNotebookWorkspaceBinding.status == "ACTIVE"
    )
    result = await db.execute(stmt)
    ws_binding = result.scalars().first()
    
    if not ws_binding:
        raise HTTPException(status_code=400, detail="Workspace does not have an active Open Notebook binding.")
        
    # We know it's the OpenNotebook engine since the flag is enabled
    client = ground_engine.client
    
    return StreamingResponse(
        client.ask_stream(
            question=request.query,
            strategy_model=ground_engine.default_strategy_model,
            answer_model=ground_engine.default_answer_model,
            final_answer_model=ground_engine.default_final_answer_model
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

from app.schemas.conversation import ChatRequest, ChatResponse
from app.models.conversation import GroundConversation
from app.models.open_notebook_binding import OpenNotebookConversationBinding, OpenNotebookWorkspaceBinding
from app.integrations.open_notebook.client import OpenNotebookClient

@router.post("/{workspace_id}/chat", response_model=ChatResponse)
async def chat_ground_mode(
    workspace_id: UUID,
    request: ChatRequest,
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import select
    
    # Verify workspace access
    from app.repositories.workspace import WorkspaceRepository
    repo = WorkspaceRepository(db)
    workspace = await repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    # Get Open Notebook workspace binding
    stmt = select(OpenNotebookWorkspaceBinding).where(
        OpenNotebookWorkspaceBinding.workspace_id == workspace_id,
        OpenNotebookWorkspaceBinding.status == "ACTIVE"
    )
    result = await db.execute(stmt)
    ws_binding = result.scalars().first()
    
    if not ws_binding:
        raise HTTPException(status_code=400, detail="Workspace does not have an active Open Notebook binding.")
        
    notebook_id = ws_binding.open_notebook_notebook_id
    client = OpenNotebookClient(workspace_id=str(workspace_id))
    
    conversation_id = request.conversation_id
    on_session_id = None
    
    if conversation_id:
        # Verify conversation belongs to this workspace and user
        conv_stmt = select(GroundConversation).where(
            GroundConversation.conversation_id == conversation_id,
            GroundConversation.workspace_id == workspace_id,
            GroundConversation.owner_id == current_user_id
        )
        conv_result = await db.execute(conv_stmt)
        conversation = conv_result.scalars().first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
            
        # Get ON session ID
        bind_stmt = select(OpenNotebookConversationBinding).where(
            OpenNotebookConversationBinding.conversation_id == conversation_id
        )
        bind_result = await db.execute(bind_stmt)
        on_binding = bind_result.scalars().first()
        if not on_binding:
            raise HTTPException(status_code=404, detail="Conversation binding not found")
            
        on_session_id = on_binding.open_notebook_session_id
    else:
        # Create new session
        on_session_id = await client.create_chat_session(notebook_id)
        
        conversation = GroundConversation(
            workspace_id=workspace_id,
            owner_id=current_user_id
        )
        db.add(conversation)
        await db.flush() # flush to get conversation_id
        
        conversation_id = conversation.conversation_id
        
        on_binding = OpenNotebookConversationBinding(
            conversation_id=conversation_id,
            open_notebook_session_id=on_session_id
        )
        db.add(on_binding)
        await db.commit()
        
    # Execute Chat
    chat_result = await client.chat_execute(
        session_id=on_session_id,
        notebook_id=notebook_id,
        message=request.message
    )
    
    return ChatResponse(
        answer=chat_result["answer"],
        conversation_id=conversation_id
    )

@router.post("/{workspace_id}/commits", response_model=WorkspaceCommitResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace_commit(
    workspace_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    repo: WorkspaceRepository = Depends(get_workspace_repository),
    knowledge_repo: KnowledgeRepository = Depends(get_knowledge_repository)
):
    workspace = await repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    # Get the current active knowledge ids
    current_knowledge = await knowledge_repo.list_workspace_knowledge(
        workspace_id=workspace_id, 
        owner_id=current_user_id,
        allowed_ids=None # We want all knowledge to snapshot the current true state
    )
    
    active_knowledge_ids = [k.knowledge_id for k in current_knowledge]
    
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
    repo: WorkspaceRepository = Depends(get_workspace_repository)
):
    workspace = await repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    # Verify commit exists and belongs to workspace
    commit = await repo.get_commit(request.commit_id, workspace_id)
    if not commit:
        raise HTTPException(status_code=404, detail="Commit not found in this workspace")
        
    workspace = await repo.set_active_commit(workspace_id, request.commit_id)
    return workspace

@router.post("/{workspace_id}/research", status_code=status.HTTP_202_ACCEPTED)
async def start_research(
    workspace_id: UUID,
    request: ResearchRequest,
    current_user_id: UUID = Depends(get_current_user),
    repo: WorkspaceRepository = Depends(get_workspace_repository),
    research_repo: ResearchRepository = Depends(get_research_repository),
    arq_redis: ArqRedis = Depends(get_arq_redis)
):
    workspace = await repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    engine = workspace.research_engine or "legacy"
    
    admission_controller = ResearchAdmissionController(
        quota_service=ResearchQuotaService(research_repo),
        rate_limiter=ProviderRateLimiter(arq_redis),
        repository=research_repo
    )
    run = await admission_controller.admit_research_run(
        workspace_id=workspace_id,
        owner_id=current_user_id,
        objective=request.objective,
        engine=engine
    )
        
    import uuid
    job_id = str(uuid.uuid4())
    
    await arq_redis.enqueue_job(
        "run_research_agent_job",
        workspace_id=str(workspace_id),
        objective=request.objective,
        run_id=str(run.run_id),
        _job_id=job_id,
        _queue_name="research-standard"
    )
    
    return {"job_id": job_id, "run_id": str(run.run_id), "status": "accepted"}
