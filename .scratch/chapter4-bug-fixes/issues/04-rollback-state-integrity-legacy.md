# 04: Rollback + State Integrity + Legacy

**What to build:**
Fix workspace commit manifest atomicity, rollback-aware context resolution, scratchpad validation, and legacy route delegation in the existing Chapter 4 implementation. Make `create_commit_with_manifest` atomic with updating `workspace.active_commit_id`, capturing active `knowledge_memory_ids`, `scratchpad_ids`, and graph references in the manifest. In `build_research_context()`, resolve the active commit manifest and query only `KnowledgeMemory` and `ScratchpadEntry` entities present in the active lineage, preventing post-rollback memories from leaking into context. In `ScratchpadRepository`, enforce fail-closed verification on cross-linked IDs (`run_id`, `conversation_id`, `evidence_ids`) to ensure they belong strictly to the caller's workspace. In `app/api/routes/workspaces.py`, remove legacy research route bypasses and delegate all legacy ask and research endpoints strictly to `ChatService` without creating parallel or unmonitored state.

**Blocked by:** 02: Turn + Event Concurrency, 03: Timeline + Promotion + Graph

**Status:** ready-for-agent

- [ ] Workspace commit creation atomically updates `active_commit_id` and records a complete manifest of active knowledge, scratchpad, and graph state.
- [ ] `build_research_context` queries only entities present in the active commit manifest, ensuring rolled-back memories and scratchpads remain invisible.
- [ ] Scratchpad creation and updates fail closed if referenced IDs do not belong to the workspace.
- [ ] Legacy `/workspaces/{id}/ask` and research endpoints execute strictly via `ChatService` with zero untracked state or parallel conversations.
