# Local Setup & Development

This guide explains how to spin up NeosisLM locally.

## Prerequisites

- **Python 3.10+**
- **Docker & Docker Compose** (for Redis, Postgres, and Neo4j)
- API Keys: 
  - Gemini (or OpenAI)
  - Tavily (for web research)

## Infrastructure Setup

1. Start the supporting databases using Docker:
   ```bash
   docker-compose up -d
   ```
   *This starts PostgreSQL on port 5432, Redis on port 6379, and Neo4j on port 7687.*

2. Run Alembic Database Migrations:
   ```bash
   alembic upgrade head
   ```

## Application Components

NeosisLM consists of three primary processes that should be run concurrently during local development.

### 1. The FastAPI Backend
This serves the REST API for integrations and external clients.
```bash
uvicorn app.main:app --reload --port 8000
```

### 2. The Arq Background Worker
Handles asynchronous jobs like exporting workspaces or syncing the Graph.
```bash
python -m arq app.workers.settings.WorkerSettings
```

### 3. The Streamlit Testing UI
A pre-built frontend interface to easily test Autonomous Research and Ground Mode.
```bash
streamlit run streamlit_app.py
```

## Environment Variables
Copy `.env.example` to `.env` and fill in your keys:
- `DATABASE_URL`
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- `REDIS_URL`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_ENDPOINT_URL`, `S3_BUCKET`
- `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY` (For LangSmith selective tracing)
