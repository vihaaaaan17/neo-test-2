# GATES — Ticket 04: Rollback + State Integrity + Legacy

## Gates

- [x] G1: Workspace commit creation atomically updates `active_commit_id` and records a complete manifest of active knowledge, scratchpad, and graph state
  - CHECK: `python -m pytest tests/unit/workspace/test_rollback_state_integrity.py -k test_commit_creation_atomicity_and_manifest -v`
  - EXPECT: passed
  - EVIDENCE: Passed. `create_commit_with_manifest` in `WorkspaceRepository` atomically updates `workspace.active_commit_id` under lock in the same transaction, capturing active `knowledge_memory_ids`, `scratchpad_ids`, and graph state in the commit manifest.

- [x] G2: `build_research_context` queries only entities present in active commit manifest, preventing rolled-back memories and scratchpads from leaking into context
  - CHECK: `python -m pytest tests/unit/workspace/test_rollback_state_integrity.py -k test_build_research_context_rollback_aware -v`
  - EXPECT: passed
  - EVIDENCE: Passed. `build_research_context` resolves `workspace.active_commit_id` manifest and restricts `KnowledgeMemory` and `ScratchpadEntry` strictly to active lineage entities, leaving rolled-back entities invisible.

- [x] G3: Scratchpad creation and updates fail closed if referenced IDs (`run_id`, `conversation_id`, `evidence_ids`) do not belong to the workspace
  - CHECK: `python -m pytest tests/unit/workspace/test_rollback_state_integrity.py -k test_scratchpad_repository_cross_linked_id_fail_closed -v`
  - EXPECT: passed
  - EVIDENCE: Passed. `ScratchpadRepository._validate_workspace_integrity` verifies cross-linked IDs against workspace_id on `create_entry`, `update_entry`, and `supersede_entry`, raising `ScratchpadWorkspaceMismatchError` if mismatched.

- [x] G4: Legacy `/workspaces/{id}/ask` and research endpoints execute strictly via `ChatService` with zero untracked state or parallel conversations
  - CHECK: `python -m pytest tests/unit/workspace/test_rollback_state_integrity.py -k test_legacy_routes_delegate_to_chatservice -v`
  - EXPECT: passed
  - EVIDENCE: Passed. Removed direct bypass fallbacks in `start_research`; reused active conversations across `/ask`, `/ask/stream`, and `/research` endpoints, delegating execution strictly to `ChatService`.

## Status
Completed