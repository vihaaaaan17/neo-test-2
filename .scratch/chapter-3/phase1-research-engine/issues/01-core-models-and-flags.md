# 01: Core Models & Feature Flags

**What to build:** Introduce the foundational database and configuration elements for the Advanced Research Engine. This includes the global environment variable kill-switch, the workspace-level engine selector, and the canonical state models (`ResearchRun` and `ResearchTask`) to ensure Neosis owns the final state separately from the upstream execution engines.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Add `ENABLE_ADVANCED_RESEARCH` (boolean) to the global application configuration (`app/core/config.py`).
- [ ] Add `research_engine` enum (`legacy`, `new`, `auto`) to the Postgres `Workspace` model.
- [ ] Create `app/models/research.py` with SQLAlchemy models for `ResearchRun` and `ResearchTask` (fields: `run_id`, `workspace_id`, `owner_id`, `objective`, `status`, `engine`).
- [ ] Generate and apply Alembic migration for the new fields and models.
