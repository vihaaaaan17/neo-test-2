# 02: Database Connection & Alembic Migrations

**What to build:** The application connects to a PostgreSQL database. We establish the initial Alembic migration environment and create a foundational `workspaces` table to validate the database connection and our Repository pattern interfaces.

**Blocked by:** 01: Core FastAPI Setup & OpenTelemetry Bootstrap

**Status:** ready-for-agent

- [ ] Application connects to a running PostgreSQL instance (e.g. via testcontainers or local docker-compose)
- [ ] Alembic is initialized and configured to run migrations
- [ ] Initial migration creates a `workspaces` table with basic schema (workspace_id, owner_id, status, created_at, updated_at)
- [ ] Basic connection test passes in CI
