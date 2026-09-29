# 01: Ground + Streaming Fabric

**What to build:**
Fix the Ground execution boundary and Server-Sent Events (SSE) transport fabric in the existing Chapter 4 implementation. In `app/services/chat/context.py`, `app/integrations/open_notebook/ground_engine.py`, and `app/integrations/open_notebook/client.py`, map canonical Neosis `source_scope` UUIDs to Open Notebook source IDs via `OpenNotebookSourceBinding` and pass `{ "sources": { on_sid: "full content" } }` in `context_config` to Open Notebook `/api/chat/context` to enforce source scoping upstream before LLM synthesis. Fail closed with `HTTP 422 ground_provenance_failure` if an explicit `source_scope` is provided but cannot be mapped. Deliver incremental token chunking in `OpenNotebookClient.chat_stream()`, eliminate session rehydration races with row-level locking on `OpenNotebookConversationBinding`, and ensure conversation history is preserved during rehydration. Format SSE events with canonical sequence IDs (`id: <sequence>\nevent: <type>\ndata: <json>\n\n`) and establish a unified streaming generator in `ChatService.stream_turn()` and `list_turn_events()` that respects `Last-Event-ID` (and `after_sequence`), subscribes to Redis PubSub `turn_events:{turn_id}` first, replays historical PostgreSQL events, deduplicates by sequence, and streams live multi-process worker events until terminal completion.

**Blocked by:** None (can start immediately)

**Status:** completed

- [x] `resolve_ground_source_scope` and `OpenNotebookGroundEngine` reject unmapped/foreign source IDs and inject mapped upstream source IDs into Open Notebook `context_config`.
- [x] Ground streaming delivers incremental token chunks rather than a single completed string.
- [x] `OpenNotebookConversationBinding` creation uses row-level locking to prevent duplicate session generation under concurrent first turns.
- [x] `format_sse_event` emits `id: <sequence>` for all SSE events.
- [x] Unified SSE stream generator in `app/api/routes/chat.py` and `app/services/chat/service.py` accepts `Last-Event-ID`, replays historical PostgreSQL events after the cursor, transitions to live Redis pub/sub without gaps or duplicates, and terminates cleanly on done/error.
