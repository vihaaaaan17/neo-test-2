# Ticket 01: Ground Execution Adapter & Open Notebook Streaming Integration

**What to build:**
Route all Ground turn execution—both unary request/response and real-time streaming—strictly through `OpenNotebookGroundEngine` using canonical, source-isolated `GroundContext`. Eliminate the direct raw OpenAI client bypass in `ChatService`. Ensure citation mapping translates Open Notebook IDs back into canonical Neosis source UUIDs with zero knowledge memory or research state contamination.

**Blocked by:** None (can start immediately).

**Status:** completed

## Scope & Changes
1. **`app/integrations/open_notebook/ground_engine.py`**:
   - Extend `OpenNotebookGroundEngine.run(...)` to accept `workspace_id`, `conversation_id`, `turn_id`, `query`, `source_scope`, and `GroundContext`.
   - Add streaming generator method `astream(...)` that consumes upstream Open Notebook chat/ask stream and yields token chunks and canonical citation metadata.
   - Enforce that Ground execution receives only canonical sources and Ground-only conversation history; strictly reject any research context.
   - Maintain strict citation mapping to canonical Neosis source UUIDs via `map_citations`.

2. **`app/services/chat/service.py`**:
   - Refactor `_execute_ground_stream_background` and unary Ground execution to call `OpenNotebookGroundEngine` exclusively.
   - Remove the direct raw OpenAI client instantiation and bypass from `ChatService`.
   - Ensure Ground turns finalize with `assistant_message`, `ground_evidence_refs`, and `provenance_status` without writing to `KnowledgeMemory` or enqueuing Neo4j sync.

3. **Verification**:
   - Unit tests verifying `OpenNotebookGroundEngine` streaming and unary execution with canonical `GroundContext`.
   - Verification that Ground never writes to `KnowledgeMemory` or triggers graph sync.

## Acceptance Criteria
- [x] `OpenNotebookGroundEngine` supports both unary and streaming execution with `GroundContext`.
- [x] `ChatService` contains zero raw OpenAI client calls for Ground execution; all calls delegate through `OpenNotebookGroundEngine`.
- [x] Ground turn answers and citation evidence reference canonical Neosis source UUIDs.
- [x] Ground execution never writes to `KnowledgeMemory` and never enqueues Neo4j graph synchronization.
- [x] Unit and integration tests for Ground execution pass cleanly.
