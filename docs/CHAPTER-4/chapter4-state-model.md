# Chapter 4: Domain State Model & Lifecycle Transitions

**Version:** 1.0.0 (Frozen)  
**Status:** Canonical  
**Audience:** Chapter 5 Frontend Engineers, State Machine Implementers, QA Engineers

---

## 1. Entity-Relationship Model (ERD)

The following Mermaid diagram captures the relational and ownership boundaries between Workspace, Sources, Conversations, Turns, Research Runs, Candidates, Scratchpad Entries, and Commits.

```mermaid
erDiagram
    WORKSPACE ||--o{ SOURCE : contains
    WORKSPACE ||--o{ CONVERSATION : hosts
    WORKSPACE ||--o{ RESEARCH_RUN : executes
    WORKSPACE ||--o{ SCRATCHPAD_ENTRY : stores
    WORKSPACE ||--o{ WORKSPACE_COMMIT : versioned_by
    WORKSPACE ||--o{ KNOWLEDGE_MEMORY : owns

    CONVERSATION ||--o{ CONVERSATION_TURN : contains
    CONVERSATION ||--o{ SCRATCHPAD_ENTRY : contextualizes

    CONVERSATION_TURN ||--o{ CHAT_EVENT : emits
    CONVERSATION_TURN ||--o| RESEARCH_RUN : triggers

    RESEARCH_RUN ||--o{ RESEARCH_ARTIFACT : produces
    RESEARCH_ARTIFACT ||--o| KNOWLEDGE_MEMORY : promotes_to

    WORKSPACE_COMMIT ||--o{ WORKSPACE_COMMIT : parent

    WORKSPACE {
        uuid workspace_id PK
        uuid owner_id
        string name
        string status
        uuid active_commit_id FK
        int ground_version
        int timeline_epoch
        string research_engine
        datetime created_at
        datetime updated_at
    }

    CONVERSATION {
        uuid conversation_id PK
        uuid workspace_id FK
        uuid owner_id
        string title
        string status
        int last_turn_sequence
        datetime created_at
        datetime updated_at
    }

    CONVERSATION_TURN {
        uuid turn_id PK
        uuid conversation_id FK
        uuid workspace_id FK
        uuid owner_id
        int sequence
        string mode
        string status
        string user_message
        string assistant_message
        uuid research_run_id FK
        string client_request_id
        uuid_array source_scope
        uuid_array ground_evidence_refs
        jsonb context_version
        string error_code
        string error_message
        datetime created_at
        datetime started_at
        datetime completed_at
    }

    CHAT_EVENT {
        uuid event_id PK
        uuid turn_id FK
        int sequence
        string event_type
        jsonb payload
        datetime created_at
    }

    RESEARCH_RUN {
        uuid run_id PK
        uuid workspace_id FK
        uuid owner_id
        uuid conversation_id FK
        string objective
        string status
        string engine
        string engine_revision
        jsonb context_version
        datetime created_at
        datetime started_at
        datetime completed_at
    }

    RESEARCH_ARTIFACT {
        uuid artifact_id PK
        uuid run_id FK
        string artifact_type
        string promotion_status
        jsonb payload
        uuid promoted_entity_id FK
        datetime reviewed_at
        string reviewer_notes
        datetime created_at
    }

    SCRATCHPAD_ENTRY {
        uuid entry_id PK
        uuid workspace_id FK
        uuid conversation_id FK
        uuid turn_id FK
        string title
        string entry_type
        string content
        boolean pinned
        string lifecycle
        string_array tags
        datetime created_at
        datetime updated_at
    }

    WORKSPACE_COMMIT {
        uuid commit_id PK
        uuid workspace_id FK
        uuid parent_id FK
        uuid_array active_knowledge_ids
        jsonb manifest
        datetime created_at
    }
```

---

## 2. Conversation Lifecycle

Conversations provide continuous conversational context. A workspace may have multiple conversations, but each conversation belongs to exactly one workspace.

```mermaid
stateDiagram-v2
    [*] --> active : POST /conversations

    active --> archived : PATCH /conversations/{id} (status="archived")
    archived --> active : PATCH /conversations/{id} (status="active")

    active --> deleted : Workspace deletion cascade
    archived --> deleted : Workspace deletion cascade

    deleted --> [*]
```

### Transition Invariants
- `last_turn_sequence` starts at `0` and is monotonically incremented under row lock (`SELECT FOR UPDATE`) on each turn creation.
- An archived conversation rejects new turn submissions with `HTTP 400 Bad Request`.
- Conversations never delete turns on status change.

---

## 3. Conversation Turn Lifecycle

A turn represents a single user query and assistant response cycle. Turns can run in either `"ground"` or `"research"` mode.

```mermaid
stateDiagram-v2
    [*] --> pending : POST /conversations/{id}/turns

    pending --> running : Worker / Service acquires execution lock
    running --> done : Execution succeeds (Answer synthesized)
    running --> cancelled : POST /turns/{id}/cancel
    running --> failed : Execution error / unhandled exception
    pending --> cancelled : User cancels before execution begins

    done --> [*]
    failed --> [*]
    cancelled --> [*]
```

### Transition Invariants & Guard Rails
1. **Concurrency Lock:** At most one turn per conversation can be in `running` status at any time. Submitting a new turn while a turn is `running` returns `HTTP 409 Conflict`.
2. **Idempotency:** If `client_request_id` is supplied and matches an existing turn in the same conversation, the server returns the existing turn immediately without re-executing.
3. **Event Sequencing:** Every `ChatEvent` emitted during turn execution receives a strictly increasing, contiguous `sequence` number starting at `1`.
4. **Terminal States:** `done`, `failed`, and `cancelled` are terminal. No further events may be appended to a turn once it enters a terminal state.

---

## 4. Research Run Lifecycle

A `ResearchRun` represents the asynchronous multi-step execution conducted by Open Deep Research (ODR) or other pluggable engines.

```mermaid
stateDiagram-v2
    [*] --> pending : Turn submitted with mode="research"

    pending --> planning : ARQ worker starts job & admits run
    planning --> researching : Objective decomposed into sub-queries
    researching --> synthesizing : Web & document evidence gathered
    synthesizing --> done : Final output graph & artifacts materialized

    pending --> cancelled : Cancel request
    planning --> cancelled : Cancel request
    researching --> cancelled : Cancel request
    synthesizing --> cancelled : Cancel request

    planning --> failed : Quota exceeded / Provider error
    researching --> failed : Tool execution error / Timeout
    synthesizing --> failed : Synthesis or validation error

    done --> [*]
    failed --> [*]
    cancelled --> [*]
```

### State Definitions
- `pending`: Enqueued in Redis ARQ queue waiting for an available worker slot.
- `planning`: Generating query decomposition and research plan. Emits `turn.research_planning`.
- `researching`: Executing parallel web searches, reading documents, scraping. Emits `turn.researching`.
- `synthesizing`: Compiling findings into an `OutputGraph` and candidate `ResearchArtifact` records. Emits `turn.synthesizing`.
- `done`: Terminal success. Emits `turn.completed`.
- `failed`: Terminal failure. Emits `turn.failed` with error code.
- `cancelled`: Terminal cancellation. Emits `turn.cancelled`.

---

## 5. Research Artifact & Promotion Candidate Lifecycle

Research runs do not write directly into canonical workspace knowledge. Instead, they materialize `ResearchArtifact` records in `pending_review` status. A human reviewer must explicitly accept or reject each candidate.

```mermaid
stateDiagram-v2
    [*] --> pending_review : Materialized during research synthesis

    pending_review --> accepted : POST /promotions/{id}/accept
    pending_review --> rejected : POST /promotions/{id}/reject

    pending_review --> superseded : Overwritten by newer run or manual commit
    pending_review --> not_promotable : System policy flags candidate as ineligible

    accepted --> [*]
    rejected --> [*]
    superseded --> [*]
    not_promotable --> [*]
```

### Concurrency and Mutex Semantics
- Review actions (`/accept` and `/reject`) execute under pessimistic database row lock (`SELECT FOR UPDATE` on `research_artifacts`).
- Concurrent review requests for the same candidate are serialized; subsequent requests encounter terminal status (`accepted` or `rejected`) and return `HTTP 409 Conflict`.
- Upon `accepted`, the entity is atomically materialized into `KnowledgeMemory` (or Neo4j `OutputGraph`) and `promoted_entity_id` is recorded.
- Rejection preserves the candidate record for auditability without mutating workspace memory.

---

## 6. Scratchpad Entry Lifecycle

The scratchpad is a collaborative, persistent working buffer for intermediate research findings, hypotheses, and insights.

```mermaid
stateDiagram-v2
    [*] --> active : Created via API or research agent

    active --> active : Pinned / Unpinned / Edited
    active --> promoted : Transferred to permanent knowledge
    active --> dismissed : User dismisses entry from active view
    active --> superseded : Replaced by a more specific insight

    promoted --> [*]
    dismissed --> [*]
    superseded --> [*]
```

### Lifecycle Semantics
- `active`: Displayed on the conversation sidebar or scratchpad drawer. Supports live user edits.
- `promoted`: Marked as promoted after the user or agent copies it to workspace knowledge.
- `dismissed`: Hidden from default view but accessible via `?lifecycle=dismissed` filter.
- `superseded`: Automatically deprecated when a higher-fidelity hypothesis replaces it.

---

## 7. Workspace Commit & Rollback Model

NeosisLM employs an append-only, immutable commit graph for workspace state management.

```mermaid
gitGraph
    commit id: "Commit 1 (Initial Sources)"
    commit id: "Commit 2 (Research Run 1 Promoted)"
    commit id: "Commit 3 (Research Run 2 Promoted)"
    branch experimental
    checkout experimental
    commit id: "Commit 4 (Bad Knowledge Added)"
    checkout main
    merge experimental id: "Rollback to Commit 3 (New Epoch)"
```

### State & Epoch Rules
1. **Commit Immutability:** Once written, a `WorkspaceCommit` and its `manifest` JSON are completely immutable.
2. **Active Commit Pointer:** `workspaces.active_commit_id` points to the current active head commit.
3. **Atomic Rollback:** Invoking `POST /rollback` performs the following atomic operations under workspace row lock:
   - Verifies the target commit exists and belongs to the workspace.
   - Sets `workspace.active_commit_id = target_commit_id`.
   - Increments `workspace.timeline_epoch = workspace.timeline_epoch + 1`.
   - Returns the updated workspace.
4. **Epoch Quarantine:** Any knowledge memories or artifacts created with a `timeline_epoch` greater than the rollback epoch or not present in the target commit's manifest are excluded from Ground retrieval queries, preventing stale or reverted knowledge from leaking into active answers.
