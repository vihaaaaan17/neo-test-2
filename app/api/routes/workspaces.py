from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.api.deps.auth import get_current_user
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse, WorkspaceUpdate
from app.repositories.workspace import WorkspaceRepository
from app.schemas.file import FileUploadResponse
from app.schemas.source import SourceResponse
from app.repositories.source import SourceRepository
from app.services.storage import ObjectStoreProtocol, get_object_store
from app.api.deps.arq import get_arq_redis
from app.api.deps.rate_limit import limiter
from arq import ArqRedis
import hashlib

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

def get_workspace_repository(db: AsyncSession = Depends(get_db)) -> WorkspaceRepository:
    return WorkspaceRepository(db)

def get_source_repository(db: AsyncSession = Depends(get_db)) -> SourceRepository:
    return SourceRepository(db)

@router.post("/", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    workspace_in: WorkspaceCreate,
    current_user_id: UUID = Depends(get_current_user),
    repo: WorkspaceRepository = Depends(get_workspace_repository)
):
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
    arq_redis: ArqRedis = Depends(get_arq_redis)
):
    workspace = await repo.get_workspace(workspace_id, current_user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    file_bytes = await file.read()
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
