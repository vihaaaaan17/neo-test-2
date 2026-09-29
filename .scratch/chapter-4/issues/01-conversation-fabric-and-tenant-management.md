# 01: Canonical Conversation Fabric & Tenant Management

**What to build:**  
The complete end-to-end conversation foundation enabling users to create, list, retrieve, and archive persistent, mode-agnostic conversations within their workspace. This ticket delivers the database models, database migration, repository operations, REST API routes, and strict workspace tenant validation so that conversations are securely isolated and ready to host Ground and Research turns.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

### Acceptance Criteria
- [ ] Alembic migration creates `conversations`, `conversation_turns`, and `chat_events` tables with appropriate indexes, unique constraints, and foreign key cascades.
- [ ] `research_runs` table is extended with nullable foreign keys `conversation_id` and `turn_id`.
- [ ] `Conversation` and `ConversationTurn` SQLAlchemy models in `app/models/conversation.py` map all canonical fields (`workspace_id`, `owner_id`, `title`, `status`, `last_turn_sequence`, `metadata_`).
- [ ] `ConversationRepository` in `app/repositories/conversation.py` provides transactional CRUD operations (`create_conversation`, `get_conversation`, `list_conversations`, `update_conversation_status`).
- [ ] REST API routes in `app/api/routes/chat.py` expose:
  - `POST /api/v1/workspaces/{workspace_id}/conversations`
  - `GET /api/v1/workspaces/{workspace_id}/conversations`
  - `GET /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}`
- [ ] Strict tenant isolation is enforced: a user cannot read, list, or create conversations in a workspace they do not have access to (returns 403 or 404).
- [ ] Integration tests in `tests/integration/chat/test_conversation.py` verify full conversation lifecycle and tenant isolation with 100% pass rate.
