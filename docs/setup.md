# Local Setup & Development

This guide explains how to spin up NeosisLM locally.

## Prerequisites

- **Python 3.10+**
- **Docker & Docker Compose** (for Redis, Postgres, and Neo4j)
- API Keys: 
  - Gemini (or OpenAI)
  - Tavily (for web research)

## Infrastructure Setup

1. Start the supporting databases and local S3 object store using Docker:
   ```bash
   docker compose up -d
   ```
   *This starts:*
   - **PostgreSQL** on port `5432`
   - **Redis** on port `6379`
   - **Neo4j** on port `7687`
   - **MinIO S3 API** on port `9000` (Console on port `9001`)
   - **MinIO Init** automatically creates default bucket `neosislm-dev`
   - **Open Notebook & SurrealDB** on port `5055`

2. Run Alembic Database Migrations:
   ```bash
   alembic upgrade head
   ```

## Application Components

NeosisLM consists of four primary processes that can be run concurrently during local development.

### 1. The FastAPI Backend
Serves the canonical REST & SSE API for integrations and external clients.
```bash
uvicorn app.main:app --reload --port 8000
```

### 2. The Arq Background Worker Fleet
Handles asynchronous parsing, chunking, Open Notebook projection, and research jobs.
```bash
python -m arq app.workers.settings.WorkerSettings
```

### 3. The Streamlit Integration Testbed
The developer console for end-to-end testing across Ground, Research, SSE streaming, and S3 storage.
```bash
streamlit run streamlit_app.py
```

### 4. MinIO Object Storage Console
Access the MinIO Web Console for inspecting raw stored files and bucket state:
- **URL**: `http://localhost:9001`
- **Default User**: `minioadmin`
- **Default Password**: `minioadmin`

## Environment Variables
Ensure `.env` contains the required infrastructure keys:
- `DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/neosislm`
- `REDIS_URL=redis://localhost:6379`
- `NEO4J_URI=bolt://localhost:7687`
- `NEO4J_USER=neo4j`
- `NEO4J_PASSWORD=password`
- `S3_ENDPOINT_URL=http://localhost:9000` *(for host processes; use `http://minio:9000` inside Docker)*
- `S3_BUCKET=neosislm-dev`
- `AWS_ACCESS_KEY_ID=minioadmin`
- `AWS_SECRET_ACCESS_KEY=minioadmin`
- `AWS_REGION=us-east-1`
- `OPEN_NOTEBOOK_ENABLED=false` *(or `true` if Open Notebook container is active)*

## Storage Pipeline Verification
1. Upload a file via Streamlit or `POST /api/v1/workspaces/{workspace_id}/files`.
2. Confirm the returned file URI has format `s3://neosislm-dev/{workspace_id}/{file_uuid}-{filename}`.
3. In Streamlit's **Storage / Ingestion Integration** tab, click **Verify Object in MinIO** to download and compare the raw bytes and SHA256 checksum.
4. Verify the ARQ worker runs `parse_and_chunk_job` and status transitions from `pending` -> `processing` -> `completed`.
