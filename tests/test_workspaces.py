import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.api.routes.workspaces import (
    get_workspace_repository, 
    get_object_store, 
    get_source_repository,
    get_quota
)
from app.api.deps.arq import get_arq_redis
from app.api.deps.auth import get_current_user
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate

client = TestClient(app)

TEST_USER_ID = uuid4()

def mock_get_current_user():
    return TEST_USER_ID

class MockWorkspace:
    def __init__(self, owner_id):
        self.workspace_id = uuid4()
        self.owner_id = owner_id
        self.status = "active"
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

class MockWorkspaceRepository:
    def __init__(self):
        self.db = {}

    async def create_workspace(self, owner_id):
        ws = MockWorkspace(owner_id)
        self.db[ws.workspace_id] = ws
        return ws

    async def get_workspace(self, workspace_id, owner_id):
        ws = self.db.get(workspace_id)
        if ws and ws.owner_id == owner_id and ws.status != "archived":
            return ws
        return None

    async def update_workspace(self, workspace_id, owner_id, update_data: WorkspaceUpdate):
        ws = await self.get_workspace(workspace_id, owner_id)
        if ws:
            ws.status = update_data.status
        return ws

    async def delete_workspace(self, workspace_id, owner_id):
        ws = await self.get_workspace(workspace_id, owner_id)
        if ws:
            ws.status = "archived"
            return True
        return False

mock_repo = MockWorkspaceRepository()
app.dependency_overrides[get_workspace_repository] = lambda: mock_repo
app.dependency_overrides[get_current_user] = mock_get_current_user

class MockObjectStore:
    async def upload_file(self, workspace_id, file_bytes, filename):
        return f"s3://mock-bucket/{workspace_id}/mock-uuid-{filename}"

    async def download_file(self, file_uri: str) -> bytes:
        return b"mock content"

mock_storage = MockObjectStore()
app.dependency_overrides[get_object_store] = lambda: mock_storage

class MockSourceSnapshot:
    def __init__(self, source_id, file_uri, filename, size, checksum):
        self.snapshot_id = uuid4()
        self.source_id = source_id
        self.file_uri = file_uri
        self.filename = filename
        self.size = size
        self.checksum_sha256 = checksum
        self.created_at = datetime.now(timezone.utc)

class MockSource:
    def __init__(self, workspace_id, owner_id):
        self.source_id = uuid4()
        self.workspace_id = workspace_id
        self.owner_id = owner_id
        self.source_type = "document"
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.snapshots = []

class MockSourceRepository:
    def __init__(self):
        self.db = {}

    async def create_source_with_snapshot(self, workspace_id, owner_id, file_uri, filename, size, checksum_sha256):
        source = MockSource(workspace_id, owner_id)
        snapshot = MockSourceSnapshot(source.source_id, file_uri, filename, size, checksum_sha256)
        source.snapshots.append(snapshot)
        self.db[source.source_id] = source
        return source

mock_source_repo = MockSourceRepository()
app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

class MockArqRedis:
    def __init__(self):
        self.jobs = []
    async def enqueue_job(self, function, *args, **kwargs):
        self.jobs.append((function, args, kwargs))

mock_arq_redis = MockArqRedis()
app.dependency_overrides[get_arq_redis] = lambda: mock_arq_redis

class MockQuotaService:
    async def check_workspace_limit(self, owner_id):
        pass
    async def check_source_limit(self, workspace_id):
        pass
    async def check_storage_limit(self, workspace_id, new_bytes):
        pass
    async def check_knowledge_limit(self, workspace_id):
        pass

mock_quota = MockQuotaService()
app.dependency_overrides[get_quota] = lambda: mock_quota

def test_unauthorized_access():
    # Remove auth override to test actual security guard
    app.dependency_overrides.pop(get_current_user, None)
    try:
        response = client.get(f"/api/v1/workspaces/{uuid4()}")
        assert response.status_code in (401, 403) # HTTPBearer returns 401 or 403 without credentials
    finally:
        # Restore override for other tests
        app.dependency_overrides[get_current_user] = mock_get_current_user

def test_create_workspace():
    response = client.post("/api/v1/workspaces/", json={})
    assert response.status_code == 201
    data = response.json()
    assert data["owner_id"] == str(TEST_USER_ID)
    assert data["status"] == "active"
    assert "workspace_id" in data

def test_get_workspace():
    create_response = client.post("/api/v1/workspaces/", json={})
    workspace_id = create_response.json()["workspace_id"]
    
    response = client.get(f"/api/v1/workspaces/{workspace_id}")
    assert response.status_code == 200
    assert response.json()["workspace_id"] == workspace_id

def test_cross_tenant_isolation():
    # Create workspace with User A
    create_response = client.post("/api/v1/workspaces/", json={})
    workspace_id = create_response.json()["workspace_id"]
    
    # Simulate request from User B
    app.dependency_overrides[get_current_user] = lambda: uuid4()
    
    response = client.get(f"/api/v1/workspaces/{workspace_id}")
    assert response.status_code == 404
    
    # Restore User A
    app.dependency_overrides[get_current_user] = mock_get_current_user

def test_update_workspace():
    create_response = client.post("/api/v1/workspaces/", json={})
    workspace_id = create_response.json()["workspace_id"]
    
    response = client.patch(f"/api/v1/workspaces/{workspace_id}", json={"status": "archived"})
    assert response.status_code == 200
    assert response.json()["status"] == "archived"

def test_delete_workspace():
    create_response = client.post("/api/v1/workspaces/", json={})
    workspace_id = create_response.json()["workspace_id"]
    
    response = client.delete(f"/api/v1/workspaces/{workspace_id}")
    assert response.status_code == 204
    
    response2 = client.get(f"/api/v1/workspaces/{workspace_id}")
    assert response2.status_code == 404

def test_upload_file_to_workspace():
    create_response = client.post("/api/v1/workspaces/", json={})
    workspace_id = create_response.json()["workspace_id"]
    
    files = {"file": ("test.pdf", b"dummy content", "application/pdf")}
    response = client.post(f"/api/v1/workspaces/{workspace_id}/files", files=files)
    
    assert response.status_code == 202
    data = response.json()
    assert data["source_type"] == "document"
    assert len(data["snapshots"]) == 1
    
    snapshot = data["snapshots"][0]
    assert "mock-uuid-test.pdf" in snapshot["file_uri"]
    assert snapshot["filename"] == "test.pdf"
    assert snapshot["size"] == 13
    assert snapshot["checksum_sha256"] is not None
    
    # Check that job was enqueued
    assert len(mock_arq_redis.jobs) > 0
    last_job = mock_arq_redis.jobs[-1]
    assert last_job[0] == "parse_and_chunk_job"
    assert last_job[2]["workspace_id"] == workspace_id
    
def test_source_status_endpoint():
    create_response = client.post("/api/v1/workspaces/", json={})
    workspace_id = create_response.json()["workspace_id"]
    
    files = {"file": ("test.pdf", b"dummy content", "application/pdf")}
    upload_resp = client.post(f"/api/v1/workspaces/{workspace_id}/files", files=files)
    source_id = upload_resp.json()["source_id"]
    
    # Needs a mock source in DB
    from uuid import UUID
    source_uuid = UUID(source_id)
    source = mock_source_repo.db[source_uuid]
    source.processing_status = "processing"
    
    # Also need to mock sqlalchemy session get for the endpoint
    class MockSession:
        async def get(self, model, id):
            return mock_source_repo.db.get(id)
    mock_source_repo.session = MockSession()
    
    status_resp = client.get(f"/api/v1/workspaces/{workspace_id}/sources/{source_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "processing"

def test_upload_file_cross_tenant_isolation():
    create_response = client.post("/api/v1/workspaces/", json={})
    workspace_id = create_response.json()["workspace_id"]
    
    app.dependency_overrides[get_current_user] = lambda: uuid4()
    
    try:
        files = {"file": ("test.pdf", b"dummy content", "application/pdf")}
        response = client.post(f"/api/v1/workspaces/{workspace_id}/files", files=files)
        assert response.status_code == 404
    finally:
        app.dependency_overrides[get_current_user] = mock_get_current_user
