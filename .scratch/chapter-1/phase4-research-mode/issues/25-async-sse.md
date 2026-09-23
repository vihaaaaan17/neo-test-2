# 25: Async Execution & ChatGPT-Style SSE Streaming

**What to build:** The scalable API and streaming UX layer. Research runs take minutes, so the API must immediately return a job ID and process the agent in the background while streaming its real-time "thoughts" to the frontend.

**Blocked by:** 24

**Status:** ready-for-agent

- [ ] Add `POST /api/v1/workspaces/{id}/research` endpoint that enqueues the `ResearchModeOrchestrator` into an `arq` background queue and returns `202 Accepted` with a `job_id`.
- [ ] Modify the LangGraph execution inside the `arq` worker to use `astream_events()` and publish those events (e.g., tool calls, state transitions) to a Redis Pub/Sub channel (`research:{job_id}`).
- [ ] Create `GET /api/v1/jobs/{job_id}/stream` endpoint in FastAPI that subscribes to the Redis channel and yields `text/event-stream` SSE payloads to the client.
- [ ] Ensure robust error handling (e.g., streaming error states if the agent fails or times out).
