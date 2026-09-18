# API & Integrations

The NeosisLM API is built on FastAPI and follows strict RESTful conventions. 

## Endpoints Overview

All routes are prefixed with `/api/v1`.

### Workspaces (`/api/v1/workspaces`)
- `POST /` - Create a new workspace.
- `GET /{workspace_id}` - Retrieve workspace details.
- `PATCH /{workspace_id}` - Update workspace settings.
- `DELETE /{workspace_id}` - Delete a workspace.

### Ingestion & Sources
- `POST /{workspace_id}/files` - Upload a source file (PDF, TXT, etc.). This endpoint respects rate limiting (10 per min) and size caps (50MB). Files are streamed to S3, and a background `parse_and_chunk_job` is enqueued via Arq.
- `GET /{workspace_id}/sources/{source_id}/status` - Check the chunking/parsing progress of an uploaded file.

### Agents
- `POST /{workspace_id}/ask` - Triggers Ground Mode. Expects a `query` and returns a generated `answer` along with `evidence` references.
- `POST /{workspace_id}/research` - Triggers Research Mode. Expects an `objective` and enqueues a background `run_research_agent_job`, returning a `job_id`.

### Job Streaming (`/api/v1/jobs`)
- `GET /{job_id}/stream` - Returns a Server-Sent Events (SSE) stream, subscribing to Redis Pub/Sub so clients can render live real-time updates as the LangGraph agents execute their plans.

## Telemetry & Protection
The API is hardened by default:
- **CORS**: Strictly controlled by `ALLOWED_ORIGINS`.
- **Quotas**: Multi-tenant quotas protect against noisy neighbor abuse.
- **Lifespan**: S3 Clients, Database engines, and Graph drivers are properly initialized and disposed of using FastAPI `@asynccontextmanager` lifespans.
