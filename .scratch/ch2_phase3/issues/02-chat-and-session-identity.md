# 02 - Chat Session Identity & Endpoint

## Objective
Establish the Neosis `GroundConversation` canonical identity and integrate Open Notebook chat.

## Requirements
1. **Database Models**:
   - Create `GroundConversation` in `app/models/conversation.py`. Fields: `conversation_id`, `workspace_id`, `owner_id`.
   - Create `OpenNotebookConversationBinding`. Fields: `conversation_id`, `open_notebook_session_id`.

2. **Integration Endpoint**:
   - Implement `POST /api/v1/workspaces/{workspace_id}/chat` facade.
   - If conversation doesn't exist, create it in Neosis, then call Open Notebook `POST /api/chat` to get a session, and bind it.
   - Send messages through `OpenNotebookClient.chat(...)`.

3. **Session Expiry**:
   - If Open Notebook returns 404 for a session, trap it and return a 400 Bad Request with a clear `conversation_session_expired` error. Do *not* auto-rehydrate.

## Acceptance Criteria
- Conversation API enforces strict workspace isolation.
- Open Notebook session IDs are hidden from the user.
- Chat history is maintained correctly by the upstream engine for active bindings.
