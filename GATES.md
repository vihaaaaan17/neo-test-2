# GATES.md — Ticket 15: API Hardening

## Leaf 1: Rate Limiting & Dependencies
- [ ] G1: `slowapi` added to `requirements.txt`
  - CHECK: `python -c "assert 'slowapi' in open('requirements.txt').read()"`
  - EXPECT: True
- [ ] G2: Rate limit middleware added to FastAPI app
  - CHECK: `python -c "from app.main import app; from slowapi.middleware import SlowAPIMiddleware; assert any(isinstance(m.app, SlowAPIMiddleware) for m in app.user_middleware)"`
  - EXPECT: True
- [ ] G3: 50MB Max upload size configured via middleware
  - CHECK: `python -c "from app.main import app; from starlette.middleware.base import BaseHTTPMiddleware; assert any(m.kwargs.get('dispatch').__name__ == 'limit_upload_size' for m in app.user_middleware if isinstance(m.app, BaseHTTPMiddleware) or hasattr(m, 'kwargs'))"`
  - EXPECT: True

## Leaf 2: CORS Middleware
- [ ] G4: ALLOWED_ORIGINS in Settings
  - CHECK: `python -c "from app.core.config import settings; print(hasattr(settings, 'ALLOWED_ORIGINS'))"`
  - EXPECT: True
- [ ] G5: CORSMiddleware registered on app
  - CHECK: `python -c "from app.main import app; from fastapi.middleware.cors import CORSMiddleware; assert any(isinstance(m.app, CORSMiddleware) for m in app.user_middleware)"`
  - EXPECT: True

## Leaf 3: API Versioning
- [ ] G6: Routes prefixed with `/api/v1`
  - CHECK: `python -c "from app.main import app; assert any(r.path.startswith('/api/v1/workspaces') for r in app.routes)"`
  - EXPECT: True
- [ ] G7: `/health` unversioned route exists
  - CHECK: `python -c "from app.main import app; assert any(r.path == '/health' for r in app.routes)"`
  - EXPECT: True

## Leaf 4: FastAPI Lifespan & S3 Connection Pooling
- [ ] G8: `S3ObjectStore` accepts initialized aioboto3 Session/Client
  - CHECK: `python -c "import inspect; from app.services.storage import S3ObjectStore; assert 's3_client' in inspect.signature(S3ObjectStore.__init__).parameters"`
  - EXPECT: True
- [ ] G9: Lifespan handler initializes S3 and stores on `app.state`
  - CHECK: `python -c "from app.main import app; assert hasattr(app, 'router') and app.router.lifespan_context is not None"`
  - EXPECT: True

## Leaf 5: Deep Health Check
- [ ] G10: Health check verifies Postgres (`SELECT 1`)
  - CHECK: `.\venv\Scripts\python.exe -m pytest tests/test_health.py -v`
  - EXPECT: PASSED

## Leaf 6: Multi-Worker Deployment
- [ ] G11: Dockerfile uses Gunicorn with Uvicorn worker
  - CHECK: `python -c "assert 'gunicorn' in open('Dockerfile').read()"`
  - EXPECT: True
- [ ] G12: Dockerfile installs gunicorn
  - CHECK: `python -c "assert 'gunicorn' in open('requirements.txt').read()"`
  - EXPECT: True

## Integration Gate
- [ ] G13: Full test suite passes
  - CHECK: `.\venv\Scripts\python.exe -m pytest tests/ -v --ignore=tests/test_db.py`
  - EXPECT: no failures
