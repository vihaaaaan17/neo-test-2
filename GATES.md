# GATES.md — Ticket 16: Tenant Quotas & LLM Backpressure

## Leaf 1: Quota Configuration
- [x] G1: Quota settings added to `app/core/config.py`
  - CHECK: `python -c "from app.core.config import settings; assert hasattr(settings, 'MAX_WORKSPACES_PER_USER')"`
  - EXPECT: True

## Leaf 2: QuotaService
- [x] G2: `QuotaService` created at `app/services/quota.py`
  - CHECK: `python -c "import os; assert os.path.exists('app/services/quota.py')"`
  - EXPECT: True
- [x] G3: `QuotaService` methods implemented (`check_workspace_limit`, `check_source_limit`, `check_storage_limit`, `check_knowledge_limit`)
  - CHECK: `python -c "from app.services.quota import QuotaService; qs = QuotaService(None); assert hasattr(qs, 'check_workspace_limit')"`
  - EXPECT: True

## Leaf 3: Enforce Quotas in Endpoints
- [x] G4: `QuotaService` injected in Workspace creation
  - CHECK: `python -c "from app.api.routes.workspaces import create_workspace; assert 'QuotaService' in create_workspace.__annotations__.values() or 'quota' in create_workspace.__code__.co_varnames"`
  - EXPECT: True
- [x] G5: `QuotaService` injected in Source upload
  - CHECK: `python -c "from app.api.routes.workspaces import upload_file_to_workspace; assert 'QuotaService' in upload_file_to_workspace.__annotations__.values() or 'quota' in upload_file_to_workspace.__code__.co_varnames"`
  - EXPECT: True

## Leaf 4: LLM Backpressure
- [x] G6: Semaphore and tenacity retry added to `app/services/episodic.py`
  - CHECK: `python -c "import tenacity; from app.services.episodic import _summarize_source_content; assert getattr(_summarize_source_content, 'retry', None) is not None"`
  - EXPECT: True

## Leaf 5: Verification
- [x] G7: Tests added for Quota enforcement
  - CHECK: `python -c "import os; assert os.path.exists('tests/test_quota.py')"`
  - EXPECT: True
- [x] G8: All tests pass
  - CHECK: `pytest tests/`
  - EXPECT: 0
