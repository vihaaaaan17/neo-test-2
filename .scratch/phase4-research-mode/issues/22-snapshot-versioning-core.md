# 22: Snapshot Versioning Core

**What to build:** The ability for a user to save the current state of their workspace's knowledge and revert to it if an autonomous research run pollutes the workspace with unwanted data.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Create `workspace_commits` table in Postgres tracking `commit_id`, `parent_id`, `workspace_id`, and a JSON array of `active_knowledge_ids`.
- [ ] Add API endpoint `POST /api/v1/workspaces/{id}/commits` to create a snapshot of all currently active knowledge memories in that workspace.
- [ ] Add API endpoint `POST /api/v1/workspaces/{id}/rollback` to revert the workspace's `active_commit_id` to a previous commit.
- [ ] Update `WorkspaceState` Pydantic models to track `active_commit_id`.
- [ ] Ensure knowledge retrieval logic only fetches memories whose IDs are within the `active_commit_id`'s snapshot array (or all memories if no snapshot is active).
