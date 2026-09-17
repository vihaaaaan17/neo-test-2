<!-- converted from research_workspace_02_memory_state_data.xlsx -->

## Sheet: Index
| 02 — Memory, State & Data Contracts |  |  |  |
| --- | --- | --- | --- |
| Sheet | Purpose | Source Coverage | Notes |
| 6 Memory Systems | Final six logical memory systems and routing/retention policies. | Knowledge, Source, Research, Episodic, Working, User/Workspace | Logical categories, not six physical databases. |
| 8 State Systems | Final eight state domains and transitions. | Workspace, Research, Plan, Task, Run, Tool, Evidence, Graph, Version (source currently contains 9 rows including header plus 9 state records) | Preserves the current architecture sheet exactly. |
| Core Data Contracts | Required vs extensible fields for core objects. | Memory Envelope, Claim, Evidence, Research Task, Research Run, Graph Node, Graph Edge, Event, Commit, Artifact | Typed core + extensible metadata. |
## Sheet: 6 Memory Systems
| Memory Type | Definition | What It Stores | Retrieval Behavior | Write Behavior | Retention | Canonical Source | Prompt Policy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Knowledge Memory | Persistent semantic knowledge | Facts; concepts; entities; claims; relationships; derived knowledge | Retrieved by semantic/keyword/graph relevance | Validated writes only | Long-lived | PostgreSQL + Internal KG projection | Selective; only task-relevant knowledge |
| Source Memory | Immutable evidence substrate | Documents; snapshots; chunks; source metadata | Usually strict source retrieval | Created by ingestion/reprocessing | Long-lived | Object Store + PostgreSQL | Retrieved for grounding; cite exact source refs |
| Research Memory | Persistent knowledge about investigations | Findings; hypotheses; conclusions; unresolved questions | Research/task scoped | Agent/user promotion from working/episodic evidence | Long-lived | PostgreSQL + Output KG projection | Use only when relevant to current research |
| Episodic Memory | Important prior experiences | Past discoveries; failures; decisions; notable run outcomes | Similarity + recency + task relevance | Summarized from events/runs | Long-lived with compaction | Event Log + summaries | Never dump raw episodes; retrieve selectively |
| Working Memory | Active reasoning context | Current evidence; active hypotheses; intermediate findings; tool outputs | Direct indexed context | Mutable during run | Ephemeral | Run checkpoint store | Aggressively bounded and compacted |
| User/Workspace Memory | Human-curated persistent context | Notes; terminology; project instructions; preferences | Scope + importance + semantic relevance | User or controlled agent promotion | Long-lived | PostgreSQL | Explicitly selected or strongly relevant |
## Sheet: 8 State Systems
| State Type | Definition | Core Fields | Transitions | Retention | Canonical Store | Who Can Mutate |
| --- | --- | --- | --- | --- | --- | --- |
| Workspace State | Current active project context | workspace_id; active_branch; active_mode; state_version | created→active→archived | Long-lived | PostgreSQL | User + system |
| Research State | Overall investigation status | research_id; objective; status; state_version | planned→running→blocked→completed/abandoned | Long-lived | PostgreSQL | Agent through reducers + user |
| Plan State | Current research strategy | plan_id; version; steps; status | draft→active→revised→completed | Versioned | PostgreSQL/Run Checkpoints | Agent through planner/reducer |
| Task State | Subtask lifecycle | task_id; objective; status; parent_task_id | queued→running→blocked→completed/failed | Long-lived | PostgreSQL | Orchestrator |
| Run State | Single execution checkpoint | run_id; step; status; state_version | created→running→paused→completed/failed | Retained | LangGraph/PostgreSQL | Orchestrator |
| Tool State | Tool-call execution state | tool_call_id; tool; status; retry_count | requested→running→succeeded/failed | Per run + audit | Event Log | Tool runner |
| Evidence State | Support/verification status | evidence_id; status; refs; version | discovered→unverified→verified/conflicting/rejected | Long-lived | PostgreSQL | Verifier + user review |
| Graph State | Graph mutation/projection state | graph_id; version; change_set_id; status | pending→applied→verified | Versioned | Neo4j + commit metadata | Graph service/reducer |
| Version State | Git-like research history | commit_id; parent_id; branch; change_set | commit→branch→merge/revert | Long-lived | PostgreSQL + Object Store | System + user action |
## Sheet: Core Data Contracts
| Object | Hard Required Fields | Optional / Extensible Fields | Ownership Rule | Why |
| --- | --- | --- | --- | --- |
| Memory Envelope | id; memory_type; scope_id; content_ref; provenance_ref; created_at | importance; status; expires_at; metadata | Canonical in relational store; graph is projection | Common envelope without forcing identical semantic shape |
| Claim | claim_id; text; claim_type; provenance_refs; status | confidence; subject/predicate/object; qualifiers; tags | Knowledge Memory owns claim | Claims must be provenance-aware |
| Evidence | evidence_id; source_id; locator; content_ref; evidence_type; status | quote; page; timestamp; confidence; checksum | Source Memory owns underlying evidence; Evidence State owns status | Citation/provenance without a separate citation graph |
| Research Task | task_id; objective; status; parent_task_id; created_at | priority; dependencies; assigned_to; budget; result_refs | Task State owns lifecycle | Allows parallel/retryable research |
| Research Run | run_id; research_id; status; started_at; workflow_version | model_id; cost; stop_reason; parent_run_id | Run State owns checkpoint | Stable execution envelope |
| Graph Node | node_id; object_id; node_type; graph_id | label; summary; status; display_metadata | Graph is projection | Avoid duplicate source of truth |
| Graph Edge | edge_id; graph_id; source_node_id; target_node_id; relation_type; created_at | confidence; provenance_refs; valid_from; valid_to; metadata | Graph projection | Keeps ontology explicit |
| Event | event_id; type; aggregate_id; timestamp; actor; schema_version | payload; correlation_id; causation_id | Append-only event log | Foundation of state history and audit |
| Commit | commit_id; parent_id; actor; created_at; message; change_set_ref | branch; merge_parent; tags; snapshot_ref | Immutable version store | Git-like research history |
| Artifact | artifact_id; type; uri; checksum; status; created_at | title; mime_type; version; provenance_refs; build_ref | Artifact Registry | Generated outputs remain first-class and versionable |