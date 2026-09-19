# 02: Phase 2 Unified Research Repository

**What to build:** 
A unified repository `app/repositories/research.py` to handle persistence for all models introduced in Ticket 01. It must explicitly enforce `workspace_id` validation to ensure that cross-workspace evidence or report access is structurally impossible.

**Blocked by:** 01 (01-canonical-research-models-and-migrations.md)

**Status:** ready-for-agent

- [ ] Create `app/repositories/research.py`.
- [ ] Implement CRUD operations for `ResearchEvidence`, `ResearchArtifact`, `ResearchReport`, `ResearchUsage`, and `ResearchEvent`.
- [ ] Ensure every read and write operation requires and filters on `workspace_id`.
- [ ] Write integration tests verifying database persistence and enforcing cross-workspace isolation.
