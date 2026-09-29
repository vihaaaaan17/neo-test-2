# Chapter 4: Frontend UI Handoff Specification (Chapter 5 Bridge)

**Version:** 1.0.0 (Frozen)  
**Status:** Canonical  
**Target:** Chapter 5 Frontend Engineers (React, Next.js, TypeScript)  
**Scope:** Complete TypeScript Type Definitions, UI Client State Machines, Sequence Diagrams, and Integration Recipes.

---

## 1. Concrete TypeScript Type Declarations

The following type definitions map 1:1 with the canonical Pydantic schemas exposed by the NeosisLM Chapter 4 API.

```typescript
// ==========================================
// Identifiers & Primitives
// ==========================================
export type UUID = string;
export type ISO8601Timestamp = string;

// ==========================================
// Workspace Models
// ==========================================
export type WorkspaceStatus = 'active' | 'archived' | 'deleted';
export type ResearchEngineType = 'open_deep_research' | 'mock';

export interface WorkspaceResponse {
  workspace_id: UUID;
  name: string;
  description?: string | null;
  owner_id: UUID;
  status: WorkspaceStatus;
  active_commit_id?: UUID | null;
  ground_version: number;
  timeline_epoch: number;
  research_engine: ResearchEngineType;
  created_at: ISO8601Timestamp;
  updated_at: ISO8601Timestamp;
}

export interface WorkspaceCreate {
  name: string;
  description?: string | null;
  research_engine?: ResearchEngineType;
}

export interface WorkspaceUpdate {
  name?: string | null;
  description?: string | null;
  research_engine?: ResearchEngineType | null;
}

export interface WorkspaceCommitManifest {
  schema_version: number;
  active_knowledge_ids: UUID[];
  accepted_artifact_ids: UUID[];
  output_graph_version: string;
  active_hypothesis_ids: UUID[];
  scratchpad_checkpoint?: {
    active_entries_count: number;
  };
  conversation_checkpoint?: {
    snapshot_at: ISO8601Timestamp;
  };
  base_research_run_ids: UUID[];
}

export interface WorkspaceCommitResponse {
  commit_id: UUID;
  workspace_id: UUID;
  parent_id?: UUID | null;
  manifest: WorkspaceCommitManifest;
  created_at: ISO8601Timestamp;
}

export interface RollbackRequest {
  commit_id: UUID;
}

// ==========================================
// Conversation & Turn Models
// ==========================================
export type ConversationStatus = 'active' | 'archived';
export type TurnMode = 'ground' | 'research';
export type TurnStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'aborted_by_timeline_fence';


export interface ConversationResponse {
  conversation_id: UUID;
  workspace_id: UUID;
  owner_id: UUID;
  title: string;
  status: ConversationStatus;
  last_turn_sequence: number;
  created_at: ISO8601Timestamp;
  updated_at: ISO8601Timestamp;
}

export interface ConversationCreate {
  title: string;
  mode?: string;
}

export interface ConversationUpdate {
  title?: string | null;
  status?: ConversationStatus | null;
}

export interface ConversationListResponse {
  conversations: ConversationResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface TurnCreate {
  message: string;
  mode: TurnMode;
  client_request_id?: string | null;
  source_scope?: UUID[] | null;
  selected_source_ids?: UUID[] | null;
  research_options?: {
    engine?: string;
    engine_revision?: string;
    max_iterations?: number;
    [key: string]: unknown;
  } | null;
}

export interface TurnResponse {
  turn_id: UUID;
  conversation_id: UUID;
  sequence: number;
  mode: TurnMode;
  status: TurnStatus;
  user_message: string;
  assistant_message?: string | null;
  research_run_id?: UUID | null;
  client_request_id?: string | null;
  source_scope?: UUID[] | null;
  ground_evidence_refs?: UUID[] | null;
  context_version: {
    ground_version?: number;
    timeline_epoch?: number;
    [key: string]: unknown;
  };
  error_code?: string | null;
  error_message?: string | null;
  created_at: ISO8601Timestamp;
  started_at?: ISO8601Timestamp | null;
  completed_at?: ISO8601Timestamp | null;
}

export interface TurnListResponse {
  turns: TurnResponse[];
  total: number;
}

// ==========================================
// Chat Event & Streaming Models
// ==========================================
export type ChatEventType =
  | 'token'
  | 'citation'
  | 'ground_answer'
  | 'turn.research_started'
  | 'turn.research_planning'
  | 'turn.researching'
  | 'scratchpad_entry'
  | 'turn.synthesizing'
  | 'turn.promotion_available'
  | 'turn.completed'
  | 'turn.partial'
  | 'turn.cancelled'
  | 'turn.failed'
  | 'status_change'
  | 'done'
  | 'error';

export interface ChatEventResponse {
  event_id: UUID;
  turn_id: UUID;
  sequence: number;
  event_type: ChatEventType;
  payload: Record<string, unknown>;
  created_at: ISO8601Timestamp;
}

export interface ChatEventListResponse {
  events: ChatEventResponse[];
  total: number;
}

// ==========================================
// Candidate Promotion Models
// ==========================================
export type CandidateType = 'memory_candidate' | 'graph_candidate';

export type PromotionStatus =
  | 'pending_review'
  | 'accepted'
  | 'rejected'
  | 'superseded'
  | 'not_promotable';

export interface PromotionCandidateResponse {
  artifact_id: UUID;
  run_id: UUID;
  artifact_type: CandidateType;
  promotion_status: PromotionStatus;
  payload: Record<string, unknown>;
  created_at: ISO8601Timestamp;
}

export interface ResearchRunResponse {
  run_id: UUID;
  workspace_id: UUID;
  owner_id: UUID;
  objective: string;
  status: string;
  engine: string;
  engine_revision?: string | null;
  current_attempt_id?: UUID | null;
  conversation_id?: UUID | null;
  turn_id?: UUID | null;
  timeline_epoch: number;
  created_at: ISO8601Timestamp;
  updated_at: ISO8601Timestamp;
}

export interface PromotionReviewRequest {
  notes?: string;
}

export interface PromotionReviewResponse {
  artifact_id: UUID;
  promotion_status: PromotionStatus;
  promoted_entity_id?: UUID | null;
  reviewed_at: ISO8601Timestamp;
  reviewer_notes?: string | null;
}

// ==========================================
// Scratchpad Models
// ==========================================
export type ScratchpadLifecycle = 'active' | 'promoted' | 'dismissed' | 'superseded';
export type ScratchpadEntryType = 'hypothesis' | 'insight' | 'note' | 'citation';

export interface ScratchpadEntryCreate {
  title: string;
  entry_type: ScratchpadEntryType;
  content: string;
  pinned?: boolean;
  tags?: string[];
}

export interface ScratchpadEntryUpdate {
  title?: string;
  content?: string;
  pinned?: boolean;
  lifecycle?: ScratchpadLifecycle;
  tags?: string[];
}

export interface ScratchpadEntryResponse {
  entry_id: UUID;
  workspace_id: UUID;
  conversation_id: UUID;
  turn_id?: UUID | null;
  title: string;
  entry_type: ScratchpadEntryType;
  content: string;
  pinned: boolean;
  lifecycle: ScratchpadLifecycle;
  tags: string[];
  created_at: ISO8601Timestamp;
  updated_at: ISO8601Timestamp;
}

export interface ScratchpadEntryListResponse {
  entries: ScratchpadEntryResponse[];
  total: number;
}

// ==========================================
// Output Knowledge Graph Models
// ==========================================
export interface ProvenanceBundle {
  derived_from_refs: UUID[];
  calculation?: string | null;
  verification_status?: string | null;
}

export interface OutputGraphNode {
  id: string;
  label: string;
  properties: Record<string, unknown>;
  provenance?: ProvenanceBundle | null;
}

export interface OutputGraphEdge {
  source_id: string;
  target_id: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface OutputGraph {
  nodes: OutputGraphNode[];
  edges: OutputGraphEdge[];
}
```

---

## 2. UI Client State Machine

The frontend UI client maintains a localized finite state machine to manage turn streaming, user input gating, and background polling.

```mermaid
stateDiagram-v2
    [*] --> Idle

    Idle --> SubmittingTurn : User submits query (ground or research)
    
    SubmittingTurn --> StreamingGround : mode="ground" (stream=true)
    SubmittingTurn --> PollingResearch : mode="research" (202 Accepted)
    SubmittingTurn --> ErrorState : 4xx / 5xx error response

    StreamingGround --> StreamingGround : Receiving "token", "citation"
    StreamingGround --> TurnComplete : Receiving "done" / "turn.completed"
    StreamingGround --> Reconnecting : Network error / stream dropped
    StreamingGround --> TurnCancelled : User clicks "Cancel"

    PollingResearch --> StreamingResearch : Subscribed to turn SSE stream
    StreamingResearch --> StreamingResearch : Receiving ODR progress events
    StreamingResearch --> CandidateModalPrompt : Receiving "turn.promotion_available"
    StreamingResearch --> TurnComplete : Receiving "turn.completed"
    StreamingResearch --> Reconnecting : Network error / stream dropped
    StreamingResearch --> TurnCancelled : User clicks "Cancel"

    CandidateModalPrompt --> StreamingResearch : User postpones / continues watching
    CandidateModalPrompt --> ReviewingCandidate : User opens review modal

    ReviewingCandidate --> CandidateModalPrompt : Accept / Reject submitted (200 OK)

    Reconnecting --> StreamingGround : Reconnected with Last-Event-ID
    Reconnecting --> StreamingResearch : Reconnected with Last-Event-ID
    Reconnecting --> ErrorState : Max retries exceeded

    TurnCancelled --> Idle : State reset
    TurnComplete --> Idle : Ready for next turn
    ErrorState --> Idle : User dismisses error
```

---

## 3. End-to-End Sequence Diagrams

### 3.1 Scenario 1: Starting & Streaming a Ground Turn

Ground turns are optimized for fast response times. The client connects via SSE and streams tokens and citations directly to the chat window.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as ChatWindow (UI)
    participant API as NeosisLM API
    participant Engine as GroundEngine (OpenNotebook)

    User->>UI: Types query & presses Enter
    UI->>UI: Set state = SubmittingTurn, disable input
    UI->>API: POST /workspaces/{ws}/conversations/{c}/turns?stream=true<br/>Body: {message, mode: "ground"}
    API->>Engine: Run Hybrid Search & Synthesis
    API-->>UI: 200 OK (text/event-stream)

    loop Token Streaming
        Engine-->>API: Yield token chunk
        API-->>UI: event: token\nid: 1\ndata: {"delta": "YBCO", "accumulated": "YBCO"}
        UI->>UI: Append token to assistant message bubble
    end

    Engine-->>API: Yield Citation
    API-->>UI: event: citation\nid: 2\ndata: {source_id, snippet, citation_number: 1}
    UI->>UI: Render interactive citation badge [1]

    Engine-->>API: Synthesis Complete
    API-->>UI: event: ground_answer\nid: 3\ndata: {answer, citations, provenance_status}
    API-->>UI: event: turn.completed\nid: 4\ndata: {turn_id, status: "done"}
    API-->>UI: event: done\nid: 5\ndata: {"status": "done"}

    UI->>UI: Set state = Idle, re-enable input
```

---

### 3.2 Scenario 2: Starting & Streaming a Research Turn

Research turns are long-running asynchronous workflows executed by background workers.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as ChatWindow (UI)
    participant API as NeosisLM API
    participant Worker as Background ARQ Worker (ODR)

    User->>UI: Submits objective with mode="research"
    UI->>API: POST /workspaces/{ws}/conversations/{c}/turns<br/>Body: {message: "Deep research...", mode: "research"}
    API-->>UI: 202 Accepted (TurnResponse {status: "running", research_run_id})

    UI->>API: GET /workspaces/{ws}/conversations/{c}/turns/{turn_id}/events?stream=true
    API-->>UI: 200 OK (text/event-stream)

    Worker-->>API: Decompose objective
    API-->>UI: event: turn.research_planning\ndata: {plan: [...], sub_queries: [...]}
    UI->>UI: Show progress timeline (Planning step)

    loop Evidence Gathering
        Worker-->>API: Search / Scrape step complete
        API-->>UI: event: turn.researching\ndata: {step: 2, action: "web_search", sources_found: 6}
        UI->>UI: Update live search counter
    end

    Worker-->>API: Intermediate finding found
    API-->>UI: event: scratchpad_entry\ndata: {entry_id, title, content, entry_type: "hypothesis"}
    UI->>UI: Insert card into Scratchpad sidebar

    Worker-->>API: Materialize candidate artifact
    API-->>UI: event: turn.promotion_available\ndata: {artifact_id, preview, confidence: 0.98}
    UI->>UI: Display notification toast: "New Knowledge Candidate Available"

    Worker-->>API: Research finished
    API-->>UI: event: turn.completed\ndata: {turn_id, status: "done"}
    API-->>UI: event: done\ndata: {"status": "done"}
    UI->>UI: Set state = Idle, highlight Promotions modal button
```

---

### 3.3 Scenario 3: Stream Disconnection & Reconnection

When network connectivity falters, the client recovers lost events without duplicate rendering.

```mermaid
sequenceDiagram
    autonumber
    participant UI as Client Stream Handler
    participant API as NeosisLM API

    Note over UI,API: Stream drops unexpectedly after event id: 14
    UI->>UI: Detect TCP disconnect, record lastEventId = 14
    UI->>UI: Wait backoff (1s), state = Reconnecting

    UI->>API: GET .../turns/{id}/events?stream=true&after_sequence=14<br/>Header: Last-Event-ID: 14
    API-->>UI: 200 OK (text/event-stream)

    Note over API,UI: Server replays missing events strictly > 14
    API-->>UI: event: token\nid: 15\ndata: {"delta": " properties"}
    API-->>UI: event: turn.completed\nid: 16\ndata: {turn_id, status: "done"}
    API-->>UI: event: done\nid: 17\ndata: {"status": "done"}

    UI->>UI: Complete message assembly, state = Idle
```

---

### 3.4 Scenario 4: Human-in-the-Loop Candidate Review & Promotion

```mermaid
sequenceDiagram
    autonumber
    actor Reviewer
    participant UI as PromotionModal (UI)
    participant API as NeosisLM API
    participant DB as Postgres (Row Lock)

    Reviewer->>UI: Clicks "Review Candidates" (badge: 1 pending)
    UI->>API: GET /api/v1/workspaces/{ws}/promotions?status=pending_review
    API-->>UI: 200 OK (List of PromotionCandidateResponse)
    UI->>Reviewer: Displays candidate card with diff preview & confidence

    alt Reviewer Accepts
        Reviewer->>UI: Clicks "Accept" (optional notes)
        UI->>API: POST /api/v1/workspaces/{ws}/promotions/{artifact_id}/accept<br/>Body: {notes: "Verified"}
        API->>DB: SELECT ... FOR UPDATE (pessimistic lock)
        API->>DB: Insert into KnowledgeMemory, set status='accepted'
        API-->>UI: 200 OK (PromotionReviewResponse)
        UI->>Reviewer: Show success toast, refresh list
    else Reviewer Rejects
        Reviewer->>UI: Clicks "Reject" (optional reason)
        UI->>API: POST /api/v1/workspaces/{ws}/promotions/{artifact_id}/reject<br/>Body: {notes: "Invalid"}
        API->>DB: SELECT ... FOR UPDATE
        API->>DB: Set status='rejected'
        API-->>UI: 200 OK (PromotionReviewResponse)
        UI->>Reviewer: Remove candidate from review queue
    end
```

---

### 3.5 Scenario 5: Workspace Snapshot Commit & Rollback

```mermaid
sequenceDiagram
    autonumber
    actor Admin
    participant UI as Settings/Timeline (UI)
    participant API as NeosisLM API

    Admin->>UI: Clicks "Create Checkpoint"
    UI->>API: POST /api/v1/workspaces/{ws}/commits
    API-->>UI: 201 Created (WorkspaceCommitResponse {commit_id, manifest})
    UI->>Admin: Displays commit in version history

    Note over Admin,UI: Later: Bad knowledge introduced, Admin wants rollback
    Admin->>UI: Selects previous commit -> "Rollback to this state"
    UI->>API: POST /api/v1/workspaces/{ws}/rollback<br/>Body: {commit_id: "prev-commit-uuid"}
    API-->>UI: 200 OK (WorkspaceResponse {active_commit_id, timeline_epoch: 2})
    UI->>Admin: Displays success banner: "Workspace restored to epoch 2"
```

---

### 3.6 Scenario 6: Visualizing the Output Knowledge Graph

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as GraphViewer (Cytoscape / Force Graph)
    participant API as NeosisLM API

    User->>UI: Navigates to "Knowledge Graph" tab
    UI->>API: GET /api/v1/workspaces/{ws}/graph
    API-->>UI: 200 OK (OutputGraph {nodes, edges})
    UI->>UI: Render interactive graph nodes and colored edges

    User->>UI: Clicks on Node ("YBCO")
    UI->>UI: Open node inspector drawer
    UI->>UI: Display properties: transition_temp=93K
    UI->>UI: Display provenance bundle with clickable source reference links
```

---

## 4. Frontend Implementation Recipes & Best Practices

1. **SSE Client Library:** Use native `EventSource` with the `fetch-event-source` polyfill (from `@microsoft/fetch-event-source`) to support custom `Authorization: Bearer` headers and automatic reconnects with `Last-Event-ID`.
2. **Idempotency Keys:** For turn submission, generate a unique UUID v4 on the client as `client_request_id`. If the network times out during submission, safely retry with the same `client_request_id` to prevent duplicate turn creation.
3. **Turn Mutex Handling:** If the server returns `HTTP 409 Conflict` on `POST /turns`, a turn is currently in flight. Check `GET /turns` to locate the running turn and subscribe to its event stream.
4. **Citation Badges:** Render citations inline using superscript buttons (`[1]`). On click or hover, open a popover containing the source excerpt snippet and file link.
5. **No Frontend Code in Chapter 4:** This document serves as the formal handoff bridge into Chapter 5. Chapter 5 will implement the UI components based strictly on these types and contracts.
