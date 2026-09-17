# GATES.md — Ticket 14: Background Job Queue (arq + Redis)

## Leaf 1: Infrastructure (docker-compose + config + requirements)
- [ ] G1: Redis service present in docker-compose.yml
  - CHECK: `python -c "import yaml; d=yaml.safe_load(open('docker-compose.yml')); print('redis' in d['services'])"`
  - EXPECT: True
- [ ] G2: REDIS_URL in Settings
  - CHECK: `python -c "from app.core.config import settings; print(hasattr(settings, 'REDIS_URL'))"`
  - EXPECT: True
- [ ] G3: arq importable
  - CHECK: `.\venv\Scripts\python.exe -c "import arq; print('ok')"`
  - EXPECT: ok

## Leaf 2: Worker tasks (app/workers/)
- [ ] G4: workers/__init__.py exists
  - CHECK: `python -c "import os; print(os.path.exists('app/workers/__init__.py'))"`
  - EXPECT: True
- [ ] G5: parse_and_chunk_job is importable
  - CHECK: `python -c "from app.workers.tasks import parse_and_chunk_job; print('ok')"`
  - EXPECT: ok
- [ ] G6: compress_episodic_job is importable
  - CHECK: `python -c "from app.workers.tasks import compress_episodic_job; print('ok')"`
  - EXPECT: ok
- [ ] G7: WorkerSettings is importable with correct functions registered
  - CHECK: `python -c "from app.workers.settings import WorkerSettings; fns=[f.__name__ for f in WorkerSettings.functions]; print(sorted(fns))"`
  - EXPECT: `['compress_episodic_job', 'parse_and_chunk_job']`
- [ ] G8: Job idempotency — parse_and_chunk_job checks snapshot status before executing
  - EVIDENCE: app/workers/tasks.py line 65 checks `if source.processing_status != "pending":` and returns skipped

## Leaf 3: Source model + status field
- [ ] G9: Source model has `processing_status` column
  - CHECK: `python -c "from app.models.source import Source; print('processing_status' in [c.name for c in Source.__table__.columns])"`
  - EXPECT: True
- [ ] G10: Alembic migration for processing_status column exists
  - CHECK: `python -c "import os; files=os.listdir('alembic/versions'); print(any('processing_status' in f for f in files))"`
  - EXPECT: True

## Leaf 4: Upload endpoint -> 202 Accepted
- [ ] G11: Upload endpoint returns 202 (not 201)
  - CHECK: `.\venv\Scripts\python.exe -m pytest tests/test_workspaces.py::test_upload_file_to_workspace -v`
  - EXPECT: PASSED
- [ ] G12: Response body contains source_id and status pending
  - EVIDENCE: tests/test_workspaces.py line 191 asserts data contains source_id
- [ ] G13: Endpoint does NOT call parser or chunking inline
  - EVIDENCE: app/api/routes/workspaces.py line 102 calls `await arq_redis.enqueue_job("parse_and_chunk_job", ...)`

## Leaf 5: Job status endpoint
- [ ] G14: GET /workspaces/{workspace_id}/sources/{source_id}/status exists and tested
  - CHECK: `.\venv\Scripts\python.exe -m pytest tests/test_workspaces.py::test_source_status_endpoint -v`
  - EXPECT: PASSED
- [ ] G15: Status endpoint returns one of pending/processing/completed/failed
  - EVIDENCE: tests/test_workspaces.py line 230 asserts `status_resp.json()["status"] == "processing"`

## Leaf 6: Episodic compression as background job
- [ ] G16: EpisodicMemoryService has enqueue_compression method
  - CHECK: `python -c "from app.services.episodic import EpisodicMemoryService; print(hasattr(EpisodicMemoryService, 'enqueue_compression'))"`
  - EXPECT: True

## Integration gate
- [ ] G17: Full test suite 0 failures
  - CHECK: `.\venv\Scripts\python.exe -m pytest tests/ -v --ignore=tests/test_db.py`
  - EXPECT: no failures
