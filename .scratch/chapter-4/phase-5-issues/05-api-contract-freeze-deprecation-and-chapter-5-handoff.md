# 05: Canonical API Contract Freeze, Deprecation Cleanup & Chapter 5 Frontend Handoff

**What to build:**
The final API contract freeze, deprecation cleanup, and comprehensive Chapter 5 frontend handoff package:
1. **API Contract Freeze & OpenAPI Validation**:
   - Validate and freeze canonical schemas for `Conversation`, `ConversationTurn`, `ChatEvent`, `ResearchRun`, `PromotionCandidate`, `ScratchpadEntry`, `WorkspaceCommit`, and `OutputGraph`.
   - Verify OpenAPI documentation (`/docs`, `/openapi.json`) generates valid specifications without leaking internal ODR, LangGraph, or SurrealDB implementation details.
2. **Deprecation Cleanup**:
   - Verify all legacy routes (`/workspaces/{id}/research`, `/workspaces/{id}/ask`, etc.) emit RFC 8288 `Deprecation: true` and `Link` successor-version headers while delegating 100% of execution to canonical `ChatService`.
   - Add explicit runtime `DeprecationWarning` to legacy orchestrator classes (`GroundModeOrchestrator`, `ResearchModeOrchestrator`) while preserving them as compatibility shims for external callers.
   - Retire any genuinely dead, uncalled private helpers.
3. **Chapter 5 Frontend Handoff Documentation**:
   - Create 4 comprehensive, concrete handoff specifications under `docs/`:
     - `docs/chapter4-api-contract.md`: Exhaustive endpoints list, HTTP methods, path/query parameters, request bodies, response schemas, and standardized error envelopes.
     - `docs/chapter4-state-model.md`: Domain entity relationship diagram (ERD), full lifecycle state transitions for Conversation, Turn, ResearchRun, Candidate, Scratchpad, and Workspace Commit.
     - `docs/chapter4-event-catalog.md`: Complete catalog of SSE event types (`token`, `citation`, `ground_answer`, `turn.research_started`, `turn.research_planning`, `turn.researching`, `scratchpad_entry`, `turn.synthesizing`, `turn.promotion_available`, `turn.completed`, `turn.cancelled`, `turn.failed`, `done`), exact payloads, keep-alive heartbeats, and reconnect semantics (`Last-Event-ID`).
     - `docs/chapter4-ui-handoff.md`: Concrete TypeScript type declarations, UI client state machine specifications, sequence diagrams, and implementation recipes for:
       - Starting and streaming Ground turns
       - Starting and streaming Research turns
       - Reconnecting to active streams
       - Polling and displaying candidate review modals
       - Executing Accept / Reject actions
       - Viewing and pinning Scratchpad entries
       - Workspace commit history and rollback invocation
       - Visualizing Output KG nodes with provenance links.

**Blocked by:** 04: Concurrency, Race Condition & Network Failure Resilience Verification Suite

**Status:** completed

- [x] Validate FastAPI OpenAPI schema generation and assert no internal engine leaks in public schemas.
- [x] Verify runtime `DeprecationWarning` on legacy orchestrators and RFC 8288 headers on compatibility routes.
- [x] Create `docs/chapter4-api-contract.md`.
- [x] Create `docs/chapter4-state-model.md`.
- [x] Create `docs/chapter4-event-catalog.md`.
- [x] Create `docs/chapter4-ui-handoff.md` with complete TypeScript interfaces, state machines, and sequence diagrams.
- [x] Verify zero frontend implementation code is added in Phase 5.
- [x] Verify final Chapter 4 definition of done and update master gate ledger.
