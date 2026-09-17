import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps.auth import get_current_user
from app.api.routes.workspaces import get_workspace_repository, get_knowledge_repository
import datetime

client = TestClient(app)

TEST_USER_ID = uuid4()
def mock_get_current_user(): return TEST_USER_ID

class MockWorkspace:
    def __init__(self, owner_id):
        self.workspace_id = uuid4()
        self.owner_id = owner_id
        self.status = "active"
        self.active_commit_id = None
        self.created_at = datetime.datetime.now()
        self.updated_at = datetime.datetime.now()

class MockCommit:
    def __init__(self, workspace_id, active_knowledge_ids, parent_id=None):
        self.commit_id = uuid4()
        self.parent_id = parent_id
        self.workspace_id = workspace_id
        self.active_knowledge_ids = active_knowledge_ids
        self.created_at = datetime.datetime.now()

class MockWorkspaceRepo:
    def __init__(self):
        self.workspaces = {}
        self.commits = {}
        
    async def create_workspace(self, owner_id):
        ws = MockWorkspace(owner_id)
        self.workspaces[ws.workspace_id] = ws
        return ws
        
    async def get_workspace(self, workspace_id, owner_id):
        return self.workspaces.get(workspace_id)
        
    async def create_commit(self, workspace_id, parent_id, active_knowledge_ids):
        commit = MockCommit(workspace_id, active_knowledge_ids, parent_id)
        self.commits[commit.commit_id] = commit
        return commit
        
    async def set_active_commit(self, workspace_id, commit_id):
        ws = self.workspaces.get(workspace_id)
        ws.active_commit_id = commit_id
        return ws
        
    async def get_commit(self, commit_id, workspace_id):
        return self.commits.get(commit_id)

class MockKnowledgeRepo:
    async def list_workspace_knowledge(self, workspace_id, owner_id, allowed_ids=None):
        return []

app.dependency_overrides[get_current_user] = mock_get_current_user
mock_workspace_repo = MockWorkspaceRepo()
app.dependency_overrides[get_workspace_repository] = lambda: mock_workspace_repo
mock_knowledge_repo = MockKnowledgeRepo()
app.dependency_overrides[get_knowledge_repository] = lambda: mock_knowledge_repo

# Mock other required deps for workspace creation
from app.api.routes.workspaces import get_quota
class MockQuotaService:
    async def check_workspace_limit(self, owner_id): pass
app.dependency_overrides[get_quota] = lambda: MockQuotaService()

def test_versioning():
    # 1. Create workspace
    res = client.post("/api/v1/workspaces/", json={})
    assert res.status_code == 201
    ws_id = res.json()["workspace_id"]
    
    # 2. Create commit
    commit_res = client.post(f"/api/v1/workspaces/{ws_id}/commits")
    assert commit_res.status_code == 201
    commit_id = commit_res.json()["commit_id"]
    
    # 3. Rollback
    rollback_res = client.post(f"/api/v1/workspaces/{ws_id}/rollback", json={"commit_id": commit_id})
    assert rollback_res.status_code == 200
    assert rollback_res.json()["active_commit_id"] == commit_id
