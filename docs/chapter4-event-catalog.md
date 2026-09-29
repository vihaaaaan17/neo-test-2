# Chapter 4: Server-Sent Events (SSE) Event Catalog

**Version:** 1.0.0 (Frozen)  
**Status:** Canonical  
**Content-Type:** `text/event-stream`  
**Wire Encoding:** UTF-8  
**Replay Endpoint:** `GET /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}/events?stream=true&after_sequence={seq}`

---

## 1. Protocol Overview & Framing

All streaming responses in NeosisLM adhere to the standard W3C Server-Sent Events (SSE) specification:

```
event: <event_type>\n
id: <sequence_number>\n
data: <json_stringified_payload>\n\n
```

### Key Protocol Invariants
1. **Contiguous Sequencing:** Every event in a turn is assigned a strictly monotonic integer `sequence` starting at `1`. The `id:` field on the wire contains this integer formatted as a string.
2. **Heartbeats / Keep-Alive:** When execution is processing without emitting domain events (e.g., long LLM reasoning or web scraping), the server periodically emits SSE comments:
   ```
   : ping\n\n
   ```
   Clients should reset their timeout timers upon receiving keep-alive comments.
3. **Stream Termination:** A stream terminates when either:
   - The `done` event is received.
   - An unrecoverable `error` event is received.
   - The TCP connection is closed.
4. **Reconnection & Deduplication:** When a network disconnect occurs, the client includes `Last-Event-ID: <seq>` in the HTTP headers or passes `?after_sequence=<seq>` in the query string to replay only unacknowledged events.

---

## 2. Event Catalog Summary Table

| Event Name | Category | Direction | Terminal? | Typical Frequency |
|:---|:---|:---|:---:|:---|
| `token` | Ground / Stream | Server -> Client | No | 20–100 per sec |
| `citation` | Ground | Server -> Client | No | 1–10 per turn |
| `ground_answer` | Ground | Server -> Client | No | 1 per ground turn |
| `turn.research_started` | Research | Server -> Client | No | 1 per research turn |
| `turn.research_planning`| Research | Server -> Client | No | 1–3 per research turn |
| `turn.researching` | Research | Server -> Client | No | 5–30 per research turn |
| `scratchpad_entry` | Research | Server -> Client | No | 1–10 per research turn |
| `turn.synthesizing` | Research | Server -> Client | No | 1–2 per research turn |
| `turn.promotion_available` | Research | Server -> Client | No | 1–5 per research turn |
| `turn.completed` | General | Server -> Client | No | 1 per successful turn |
| `turn.partial` | General | Server -> Client | No | Periodic |
| `turn.failed` | General | Server -> Client | No | 1 on error |
| `status_change` | General | Server -> Client | No | 2–5 per turn |
| `aborted_by_timeline_fence` | Concurrency / Fencing | Server -> Client | **Yes** | 1 on rollback fence abort |
| `done` | Protocol | Server -> Client | **Yes** | 1 per stream |
| `error` | Protocol | Server -> Client | **Yes** | 1 on stream abort |


---

## 3. Detailed Event Payloads & Schemas

### 3.1 `token` (Text Generation Chunk)
Emitted during LLM generation for responsive real-time token rendering.
```
event: token
id: 12
data: {"delta": " superconductivity", "accumulated": "High-temperature superconductivity"}
```
- **Fields:**
  - `delta` (`string`): Newly emitted token chunk.
  - `accumulated` (`string`): Complete accumulated text up to this token.

---

### 3.2 `citation` (Ground Citation Anchor)
Emitted when an evidence chunk from the workspace knowledge base is cited in the response.
```
event: citation
id: 13
data: {
  "source_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "chunk_id": "7fa85f64-5717-4562-b3fc-2c963f66afa6",
  "score": 0.92,
  "snippet": "YBCO was the first material discovered to become superconducting above 77 K (liquid nitrogen boiling point).",
  "citation_number": 1
}
```
- **Fields:**
  - `source_id` (`UUID`): ID of the original source file.
  - `chunk_id` (`UUID`): ID of the specific chunk in vector/hybrid store.
  - `score` (`float`): Similarity or relevance confidence score (`0.0` to `1.0`).
  - `snippet` (`string`): Verbatim excerpt cited from the source.
  - `citation_number` (`int`): 1-indexed citation reference matching `[1]` in generated text.

---

### 3.3 `ground_answer` (Ground Synthesis Complete)
Emitted upon completion of a Ground turn, providing full synthesized answer and provenance metadata.
```
event: ground_answer
id: 14
data: {
  "answer": "YBCO achieves superconductivity at 93 K [1], which was first observed in 1987 [2].",
  "citations": [ ... ],
  "provenance_status": "verified",
  "confidence": 0.98
}
```
- **Fields:**
  - `answer` (`string`): The complete markdown-formatted answer.
  - `citations` (`list[object]`): Array of citation objects matching the citations emitted earlier.
  - `provenance_status` (`string`): `"verified"`, `"unverified"`, or `"inferred"`.
  - `confidence` (`float`): Numerical confidence score.

---

### 3.4 `turn.research_started` (Research Execution Enqueued/Started)
Emitted when background worker starts executing a research turn.
```
event: turn.research_started
id: 2
data: {
  "run_id": "8fa85f64-5717-4562-b3fc-2c963f66afa6",
  "turn_id": "1fa85f64-5717-4562-b3fc-2c963f66afa6",
  "engine": "open_deep_research",
  "engine_revision": "v1.2",
  "started_at": "2026-09-29T12:00:01Z"
}
```

---

### 3.5 `turn.research_planning` (Decomposition & Plan Formed)
Emitted when the research engine breaks down the objective into discrete investigative paths.
```
event: turn.research_planning
id: 3
data: {
  "plan": [
    "Search recent experimental papers on YBCO oxygen stoichiometry",
    "Identify dopant effects on critical current density",
    "Synthesize consensus timeline"
  ],
  "sub_queries": [
    "YBCO oxygen deficiency Tc relationship",
    "YBa2Cu3O7-x critical temperature annealing"
  ]
}
```

---

### 3.6 `turn.researching` (Tool / Search Execution Step)
Emitted for each distinct research action (search query, scrape, document retrieval).
```
event: turn.researching
id: 5
data: {
  "step": 2,
  "action": "web_search",
  "query": "YBCO oxygen deficiency Tc relationship",
  "sources_found": 8,
  "duration_ms": 1240
}
```

---

### 3.7 `scratchpad_entry` (Intermediate Finding / Hypothesis)
Emitted whenever the agent records an intermediate hypothesis, insight, or note directly to the scratchpad.
```
event: scratchpad_entry
id: 6
data: {
  "entry_id": "7fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "Hypothesis: Tc degradation below O6.9",
  "entry_type": "hypothesis",
  "content": "Multiple sources confirm Tc drops sharply from 93K to 60K as oxygen content drops below 6.9.",
  "pinned": false,
  "lifecycle": "active"
}
```

---

### 3.8 `turn.synthesizing` (Compiling Output Graph)
Emitted when the research agent begins compiling raw evidence into candidate knowledge structures and the Output Knowledge Graph.
```
event: turn.synthesizing
id: 18
data: {
  "nodes_count": 4,
  "edges_count": 5,
  "candidates_count": 2
}
```

---

### 3.9 `turn.promotion_available` (Human Review Required)
Emitted when a candidate artifact has been prepared and is ready for human review via the Promotions modal.
```
event: turn.promotion_available
id: 19
data: {
  "artifact_id": "6fa85f64-5717-4562-b3fc-2c963f66afa6",
  "run_id": "8fa85f64-5717-4562-b3fc-2c963f66afa6",
  "artifact_type": "knowledge_memory",
  "preview": "YBCO exhibits high-Tc superconductivity up to 93 K dependent on oxygen stoichiometry > 6.93.",
  "confidence": 0.98
}
```

---

### 3.10 `turn.completed` (Turn Finished Successfully)
Emitted when turn execution finishes successfully and all artifacts have been persisted.
```
event: turn.completed
id: 20
data: {
  "turn_id": "1fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "done",
  "duration_ms": 14200,
  "completed_at": "2026-09-29T12:00:15Z"
}
```

---

### 3.11 `turn.cancelled` (Turn Aborted)
Emitted when a turn is cancelled by user request.
```
event: turn.cancelled
id: 10
data: {
  "turn_id": "1fa85f64-5717-4562-b3fc-2c963f66afa6",
  "reason": "User requested cancellation"
}
```

---

### 3.12 `turn.failed` (Turn Aborted by Error)
Emitted when turn execution encounters an unhandled exception or fatal quota breach.
```
event: turn.failed
id: 11
data: {
  "turn_id": "1fa85f64-5717-4562-b3fc-2c963f66afa6",
  "error_code": "PROVIDER_QUOTA_EXCEEDED",
  "error_message": "Search provider rate limit exceeded. Please retry in 60s."
}
```

---

### 3.13 `status_change` (Status Transition Notice)
Emitted whenever the turn or research run changes status.
```
event: status_change
id: 4
data: {
  "entity": "turn",
  "entity_id": "1fa85f64-5717-4562-b3fc-2c963f66afa6",
  "from_status": "pending",
  "to_status": "running"
}
```

---

### 3.14 `done` (Terminal Stream Marker)
Always emitted as the final event of any successful or gracefully terminated stream.
```
event: done
id: 21
data: {"status": "done"}
```

---

### 3.15 `error` (Stream Transport Error)
Emitted if the SSE generator encounters a server-side transport or pipeline error.
```
event: error
id: 22
data: {
  "error_code": "STREAM_DISRUPTED",
  "detail": "Connection to worker queue was lost."
}
```

---

## 4. Reconnection & Stream Recovery Semantics

### Client Reconnection Flow
When an SSE connection drops:
1. Client inspects the last processed event ID: `lastId = 15`.
2. Client opens a new connection to the replay endpoint:
   ```
   GET /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}/events?stream=true&after_sequence=15
   ```
   *Alternatively*, client sets the standard HTTP header:
   ```
   Last-Event-ID: 15
   ```
3. The server immediately yields all events with `sequence > 15` in strict order.
4. If the turn is already in terminal state (`done`, `failed`, `cancelled`), the server replays all remaining stored events, sends the terminal `turn.completed` / `turn.failed` event, sends `done`, and closes the connection cleanly.
5. If the turn is still actively running, the server replays historical events and seamlessly transitions into the live event broadcast.
