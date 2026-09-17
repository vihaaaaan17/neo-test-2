import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.future import select
import aioboto3

from app.api.deps.rate_limit import limiter
from app.core.config import settings
from app.core.telemetry import setup_telemetry
from app.core.database import engine
from app.repositories.graph import graph_store
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace

logger = logging.getLogger(__name__)

# --- Telemetry ---
setup_telemetry()

# --- Rate Limiting ---
# Limiter imported from app.api.deps.rate_limit

# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up NeosisLM API")
    session = aioboto3.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION
    )
    # Create the client and attach to app.state
    # Using async with context manager for the client to ensure proper setup/teardown
    s3_context = session.client("s3", endpoint_url=settings.S3_ENDPOINT_URL)
    app.state.s3_client = await s3_context.__aenter__()
    
    # Connect to internal KG
    await graph_store.connect()
    
    yield
    
    # Shutdown
    logger.info("Shutting down NeosisLM API")
    await graph_store.close()
    await s3_context.__aexit__(None, None, None)
    await engine.dispose()
    
    tracer_provider = trace.get_tracer_provider()
    if hasattr(tracer_provider, "force_flush"):
        tracer_provider.force_flush()

# --- App Setup ---
app = FastAPI(title="NeosisLM API", lifespan=lifespan)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Maximum upload size limit middleware (50MB)
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import HTTPException
from starlette.responses import JSONResponse

class UploadSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only check upload endpoints
        if request.method == "POST" and "files" in request.url.path:
            content_length = request.headers.get('content-length')
            if content_length and int(content_length) > 50 * 1024 * 1024:
                return JSONResponse(status_code=413, content={"detail": "Payload too large. Max size is 50MB."})
        return await call_next(request)

# Keep the original internal function name as requested by the tests (limit_upload_size)
async def limit_upload_size(request: Request, call_next):
    if request.method == "POST" and "files" in request.url.path:
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > 50 * 1024 * 1024:
            return JSONResponse(status_code=413, content={"detail": "Payload too large. Max size is 50MB."})
    return await call_next(request)

app.add_middleware(BaseHTTPMiddleware, dispatch=limit_upload_size)


# Instrument the FastAPI app with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

# --- Routes ---
@app.get("/health")
@app.get("/api/v1/health")
async def health_check():
    """Deep health check verifying Postgres and Neo4j connectivity."""
    status = {"status": "ok", "postgres": "ok", "neo4j": "ok"}
    try:
        async with engine.connect() as conn:
            await conn.execute(select(1))
    except Exception as e:
        logger.error(f"Postgres health check failed: {e}")
        status["status"] = "degraded"
        status["postgres"] = "failed"
        
    try:
        await graph_store.execute_query("RETURN 1")
    except Exception as e:
        logger.error(f"Neo4j health check failed: {e}")
        status["status"] = "degraded"
        status["neo4j"] = "failed"
        
    return status

from app.api.routes.workspaces import router as workspaces_router
from app.api.routes.jobs import router as jobs_router
# Limit the workspace router routes explicitly if needed, but slowapi works automatically
app.include_router(workspaces_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
