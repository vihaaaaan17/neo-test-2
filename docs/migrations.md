# Scaling & Migrations

This guide dictates operational standards for scaling NeosisLM beyond local development.

## Database Migrations (Alembic)
NeosisLM uses `alembic` to manage PostgreSQL schema changes safely.

**Rule**: NEVER modify SQLAlchemy models (`app/models/*.py`) without generating and applying a migration!

1. Edit the model in python.
2. Generate the migration script:
   ```bash
   alembic revision --autogenerate -m "Add new feature table"
   ```
3. Apply to database:
   ```bash
   alembic upgrade head
   ```

## Scaling Strategy

NeosisLM is architected to scale horizontally. Since the API is stateless, you can scale the backend processes simply by running more containers.

### Hardening for Scale (1,000+ Users)
- **NullPool Database Connections**: Due to the heavily asynchronous nature of the FastAPI endpoints and background workers, default SQLAlchemy connection pools can deadlock. We utilize `NullPool` combined with a connection multiplexer (like PgBouncer) deployed in front of the database for massive concurrency.
- **JSONB Indexes**: Advanced querying (such as checking `source_mode` on memory objects) requires GIN indexes on JSONB columns to avoid sequential scans. These are explicitly defined in our migrations.
- **Tenant Quotas**: Before generating content or uploading blobs, the `QuotaService` checks row-counts and storage totals grouped by `owner_id`. This prevents runaway consumption by a single user.

## Telemetry
We use **LangSmith** selectively. Agent planning loops are traced, but trivial health checks and manual API actions are ignored to keep telemetry bills strictly tied to LLM reasoning cycles.
