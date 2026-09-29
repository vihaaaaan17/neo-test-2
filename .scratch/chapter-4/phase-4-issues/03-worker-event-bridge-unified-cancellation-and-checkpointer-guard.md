# Ticket 03: Worker Event Bridging, Unified Turn Cancellation & Production Checkpointer Guard

**What to build:**
Implement real-time synchronous bridging from execution-level `ResearchEvent` records to canonical `ChatEvent`s in PostgreSQL and Redis `turn_events:{turn_id}`; expose the canonical turn cancellation endpoint `POST /workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}/cancel` cascading into underlying execution engines; and enforce the production checkpointer fail-fast guard at startup for both FastAPI and ARQ workers.

**Blocked by:** Ticket 01, Ticket 02.

**Status:** ready-for-agent

## Scope & Changes
1. **Synchronous ResearchEvent to ChatEvent Bridge (`app/workers/tasks.py` & `app/services/chat/events.py`)**:
   - Define standardized event constants in `app/schemas/chat.py`:
     - `turn.research_started`, `turn.research_planning`, `turn.researching`, `turn.synthesizing`, `turn.promotion_available`, `turn.completed`, `turn.partial`, `turn.cancelled`, `turn.failed`.
   - In `run_research_agent_job`: Whenever research status changes or engine emits milestones, call `ChatEventRepository.append_event` to persist to PostgreSQL and publish to `turn_events:{turn_id}` in the same lifecycle transition.
   - Attach the completed `ResearchRun` to `ConversationTurn.research_run_id` and finalize `ConversationTurn.status = 'completed'` (or `'failed'`/`'cancelled'`).

2. **Unified Turn Cancellation Endpoint (`app/api/routes/chat.py` & `app/services/chat/service.py`)**:
   - Expose `POST /workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}/cancel`.
   - For Research turns: Lookup attached `ResearchRun`, trigger cooperative engine cancellation, transition `ResearchRun` to `cancelled`, update `ConversationTurn.status = 'cancelled'`, and emit `turn.cancelled`.
   - For Ground turns: Cancel in-flight background task or streaming generator, update turn status, and emit `turn.cancelled`.
   - Ensure cancellation respects `timeline_epoch` and never promotes candidates.

3. **Production Checkpointer Guard (`app/services/working_memory.py`, `app/main.py`, `app/workers/settings.py`)**:
   - Implement `validate_checkpointer(env: str)`:
     - When `settings.NEOSIS_ENV == "production"`, initialize `AsyncPostgresSaver`; if connection fails or checkpointer is not configured, raise fatal `RuntimeError("Production checkpointer requirement violated: AsyncPostgresSaver is unavailable")`.
     - In `development` and `test` environments, permit `MemorySaver`.
   - Invoke `validate_checkpointer` during FastAPI startup lifespan (`app/main.py`) and ARQ worker startup (`app/workers/settings.py`).

## Acceptance Criteria
- [ ] Research execution lifecycle events bridge synchronously into PostgreSQL `chat_events` and publish to `turn_events:{turn_id}`.
- [ ] Research completion cleanly finalizes `ConversationTurn` and records assistant summary.
- [ ] `POST .../turns/{turn_id}/cancel` cleanly cancels in-flight research and ground turns and publishes `turn.cancelled`.
- [ ] Production checkpointer guard aborts startup with `RuntimeError` if `NEOSIS_ENV == "production"` and `AsyncPostgresSaver` fails.
- [ ] Dedicated unit tests for event bridging, cancellation, and checkpointer guard pass cleanly.
