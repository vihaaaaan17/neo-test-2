# 04: Legacy Route Compatibility & Open Notebook Binding Cutover

**What to build:**  
The migration and cutover layer that guarantees zero regressions across existing integrations and tests. This ticket migrates `OpenNotebookConversationBinding` to the canonical `Conversation` model, refactors legacy endpoints (`/ask-ground-mode`, `/chat-ground-mode`, `/research`, `/runs`) to internally delegate to the canonical `ChatService` with HTTP `Deprecation` headers, removes dead placeholder enqueueing paths, and validates that 100% of the repository's test suites pass cleanly.

**Blocked by:** 03: Unified SSE Token Streaming & Reconnect Event Replay

**Status:** ready-for-agent

### Acceptance Criteria
- [ ] `OpenNotebookConversationBinding` model in `app/models/open_notebook_binding.py` is migrated to reference canonical `Conversation` instead of `GroundConversation`.
- [ ] Legacy endpoint `POST /api/v1/workspaces/{id}/ask-ground-mode` internally creates or uses an active conversation, executes a Ground turn via `ChatService`, and returns the legacy response schema with `Deprecation: true` and `Link` headers.
- [ ] Legacy endpoint `POST /api/v1/workspaces/{id}/chat-ground-mode` delegates to `ChatService` with deprecation headers while maintaining backward compatibility for streaming SSE.
- [ ] Dead placeholder function `enqueue_research_job()` in `app/api/routes/research.py` is removed; all research submissions route through canonical admission and turn creation.
- [ ] Old `GroundModeOrchestrator` Ground-turn KnowledgeMemory write (`KnowledgeMemoryCreate` + `sync_knowledge_to_graph_job`) is completely excised; Ground answers persist exclusively to turns.
- [ ] All pre-existing test suites (`tests/test_ground_mode.py`, `tests/test_ground_mode_api.py`, `tests/test_workspaces.py`, `tests/integration/...`) pass with zero regressions.
- [ ] Complete Phase 1 verification passes against the full test harness.
