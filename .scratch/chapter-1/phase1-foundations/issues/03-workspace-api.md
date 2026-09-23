# 03: Workspace Lifecycle API

**What to build:** An end-to-end API to create, read, update, and archive a `Workspace`. This includes defining the strict Pydantic domain schemas, the Postgres repository implementation, and the FastAPI routes.

**Blocked by:** 02: Database Connection & Alembic Migrations

**Status:** ready-for-agent

- [ ] Pydantic schemas defined for Workspace creation, reading, and updating
- [ ] WorkspaceRepository interface implemented for PostgreSQL
- [ ] FastAPI endpoints (POST, GET, PATCH, DELETE) wired up to the repository
- [ ] End-to-end tests verify workspace lifecycle
