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
from typing import Callable, Awaitable

from app.schemas.ground_mode import AskRequest, AskResponse
from app.api.deps.llm import get_llm_gateway, get_embed_gateway
from app.orchestration.ground_mode import GroundModeOrchestrator
from app.services.hybrid_retrieval import HybridRetrievalService
from app.services.memory_router import MemoryRouter
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import KnowledgeMemoryCreate, Provenance

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

def get_workspace_repository(db: AsyncSession = Depends(get_db)) -> WorkspaceRepository:
    return WorkspaceRepository(db)

def get_source_repository(db: AsyncSession = Depends(get_db)) -> SourceRepository:
    return SourceRepository(db)

def get_quota(db: AsyncSession = Depends(get_db)) -> QuotaService:
    return get_quota_service(db)

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
    repo: WorkspaceRepository = Depends(get_workspace_repository)
):
    success = await repo.delete_workspace(workspace_id, current_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workspace not found")

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

@router.post("/{workspace_id}/ask", response_model=AskResponse)
async def ask_ground_mode(
    workspace_id: UUID,
    request: AskRequest,
    current_user_id: UUID = Depends(get_current_user),
    repo: WorkspaceRepository = Depends(get_workspace_repository),
    memory_router: MemoryRouter = Depends(get_memory_router),
    hybrid_retriever: HybridRetrievalService = Depends(get_hybrid_retrieval_service),
    llm_gateway: Callable[[str], Awaitable[str]] = Depends(get_llm_gateway),
    embed_gateway: Callable[[str], Awaitable[list[float]]] = Depends(get_embed_gateway)
):
    workspace = await repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    orchestrator = GroundModeOrchestrator(
        hybrid_retriever=hybrid_retriever,
        llm_gateway=llm_gateway,
        embed_gateway=embed_gateway
    )
    
    state = await orchestrator.run(workspace_id=workspace_id, query=request.query)
    
    if not state.get("is_grounded", False):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail="Unable to generate a grounded answer from the provided context."
        )
        
    evidence_uuids = state.get("evidence", [])
    
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
        knowledge_id=memory.knowledge_id
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
    arq_redis: ArqRedis = Depends(get_arq_redis)
):
    workspace = await repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    import uuid
    job_id = str(uuid.uuid4())
    
    await arq_redis.enqueue_job(
        "run_research_agent_job",
        workspace_id=str(workspace_id),
        objective=request.objective,
        _job_id=job_id
    )
    
    return {"job_id": job_id, "status": "accepted"}
