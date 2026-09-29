# 02: Unified Turn Execution Engine (Ground & Research)

**What to build:**  
The unified turn submission and execution engine enabling users to submit prompts to a conversation specifying either `mode: "ground"` or `mode: "research"`. Ground turns execute against Open Notebook with canonical source citations and transparent 1-time 409 session rehydration. Research turns pass admission checks, create a linked `ResearchRun`, and enqueue background ARQ jobs. Both modes enforce transactional sequence allocation and idempotent submission via `client_request_id`.

**Blocked by:** 01: Canonical Conversation Fabric & Tenant Management

**Status:** ready-for-agent

### Acceptance Criteria
- [ ] `ChatService` in `app/services/chat/service.py` coordinates turn submission, mode dispatching, and turn finalization.
- [ ] Turn submission enforces monotonic, transaction-safe sequence numbers (`last_turn_sequence + 1`) per conversation under row lock (`FOR UPDATE`).
- [ ] Idempotency is enforced: duplicate submissions with the same `(conversation_id, client_request_id)` return the existing turn record without duplicate execution.
- [ ] Ground turn execution:
  - Queries `OpenNotebookGroundEngine` strictly against workspace canonical sources.
  - Updates turn with `status="completed"`, `assistant_message`, and resolved `ground_evidence_refs`.
  - Ground answers do NOT automatically write to `KnowledgeMemory` or trigger Neo4j graph sync.
- [ ] Transparent Open Notebook recovery:
  - On upstream `409 session_state_lost`, transparently creates a new Open Notebook session, updates the binding, and retries the turn once.
- [ ] Research turn execution:
  - Validates quotas and rate limits via `ResearchAdmissionController`.
  - Creates a canonical `ResearchRun` referencing `turn_id` and `conversation_id`.
  - Sets turn to `status="running"` with `research_run_id` and enqueues `run_research_agent_job` in ARQ queue `research-standard`.
  - Returns `202 Accepted` with the turn record.
- [ ] Endpoints exposed in `app/api/routes/chat.py`:
  - `POST /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns`
  - `GET /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns`
  - `GET /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}`
- [ ] Integration tests in `tests/integration/chat/test_turns.py` verify Ground execution, Research enqueueing, sequence monotonicity, idempotency, and 409 recovery.
