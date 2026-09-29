# Glossary

## Export Bundle
A portable, polyglot `.zip` archive containing a workspace's entire canonical state, extracted text chunks, and metadata. 
- **Analytical dump**: It is designed to be loaded into Pandas, Jupyter, or another agentic framework to prevent vendor lock-in, rather than being a rigid 1-to-1 backup for bidirectional restoration.
- **Polyglot format**: Uses `.json` for hierarchical metadata and `.parquet` for large tabular arrays (e.g., embeddings, source chunks).
- **Scope**: By default, the bundle contains only structured metadata and extracted content. Raw binaries (e.g., source PDFs) are optionally referenced via signed URLs rather than packaged into the zip to prevent archive bloat.

## Ground Engine
The execution substrate for Ground Mode. In Chapter 2, this is the actual upstream Open Notebook implementation running as an isolated internal HTTP service. Neosis delegates Ground-mode retrieval, search, ask, and chat execution to the Ground Engine. Neosis does not reimplement the engine's internal behavior.

## Source Projection
The process of uploading a canonical Neosis source file (from S3) into Open Notebook through its native source-ingestion pathway. The projection is derived and rebuildable from the canonical Neosis source snapshot. Projection is intentionally duplicative: the canonical source lives in Neosis S3; the execution copy lives in Open Notebook's SurrealDB.

## Workspace Binding
An explicit, persisted mapping record between a Neosis `workspace_id` and an Open Notebook `notebook_id`. These identifiers are never equated. The binding supports creation, lookup, synchronization state, and failure metadata.

## Source Binding
An explicit, persisted mapping record between a Neosis `source_id`/`snapshot_id` pair and an Open Notebook `source_id`. Keyed on `(workspace_id, source_id, snapshot_id, checksum_sha256)` for idempotency.

## Compatibility Layer
The thin integration boundary (`app/integrations/open_notebook/`) that owns HTTP transport, binding resolution, source projection, response translation, citation mapping, error translation, and health checking between Neosis and the Ground Engine. It must not become a second Ground engine.

## Upstream Revision
The pinned version of the Open Notebook implementation used as the Ground Engine runtime. Recorded in `UPSTREAM_REVISION.md` at the project root. Includes repository URL, Git tag/commit, Docker image tag, Docker image digest, and acquisition date. Upgrades are deliberate, controlled migrations.

---

# Core Architectural Invariant

> **Conversation history is canonical product state; Ground evidence remains canonical source state; Research memory/derived knowledge is a separate state class and is never promoted into Ground evidence.**

---

## Conversation & ConversationTurn
The canonical conversational abstraction spanning both Ground and Research modes.
- `Conversation`: The user-visible container for an interactive session within a workspace. Mode-agnostic.
- `ConversationTurn`: A single user message and its corresponding assistant response/execution lifecycle. Mode is stored per turn (`ground` or `research`). Both modes share the same durable turn lifecycle in PostgreSQL (`pending` → `running` → `completed` | `partial` | `failed` | `cancelled`), while internal transport can be direct streaming or asynchronous background processing.

## Promotion Candidate
An intermediate research finding (`memory_candidate`, `graph_candidate`, `finding_candidate`, `hypothesis_candidate`) generated during research runs that requires explicit user verification before crossing into durable workspace memory.
- Lifecycle: `pending_review` → `under_review` → `accepted` | `rejected` | `superseded`.
- Research completion is decoupled from promotion acceptance: a run can be `completed` while its candidates remain `pending_review`.

## Promotion Decision
An auditable user action (`accept` or `reject`) recorded against a promotion candidate. Acceptance is executed as a fast transaction in PostgreSQL, which then enqueues an idempotent ARQ background job to materialize the candidate into `KnowledgeMemory` or project nodes into the Neo4j Output KG. Rejection is terminal and permanent.

## Timeline Fence
A concurrency guard created during workspace rollback. When a workspace reverts to a prior commit, a new timeline fence invalidates and cancels any in-flight execution, preventing background workers belonging to older runs from committing durable state or promoting candidates into the rolled-back workspace.

## Semantic Support Verification
Layer C verification assessing whether cited evidence actually entails or supports a claim (classified as supporting, partially supporting, contradicting, unrelated, or insufficient), distinct from referential integrity (which merely confirms that cited UUIDs exist).

## Derivation Record
A structured, reproducible record of mathematical or logical deduction (e.g. arithmetic expressions, statistical normalization, unit conversions) verified deterministically rather than through LLM self-approval.

## Contradiction Record
A structured quality and uncertainty signal identifying mutually incompatible claims or evidence across distinct sources. It informs researcher and user critique without necessarily failing the research run.

## ScratchpadEntry
A first-class, durable PostgreSQL working-state record (`note`, `observation`, `hypothesis`, `investigation`, `finding`) created during or between research turns.
- Lifecycle: `active` → `promoted` | `dismissed` | `superseded`.
- Interactive state: Distinct from immutable execution outputs (`ResearchArtifact`), scratchpad entries represent editable, pinnable reasoning artifacts.
- Scoping: Conversation-scoped by default, but can be elevated via workspace pinning.

## Context Policy Boundary
The deterministic security and integrity filter (`app/services/memory/policy.py`) that strictly dictates what context types each turn mode may read and write.
- Ground Policy: Permitted to read only canonical source scopes and Open Notebook sessions. Denies all `KnowledgeMemory`, `ResearchEvidence`, `ResearchReport`, `OutputGraph`, and `ScratchpadEntry` data.
- Research Policy: Permitted to read broader workspace state (prior Ground findings, working memory, scratchpads, accepted knowledge, evidence) under a deterministic token budget.

## Context Version Bundle
An immutable, auditable manifest generated during turn submission (`ConversationTurn.context_version`) recording the exact token budget, items included, and items evicted (with deterministic eviction reasons) when the prompt was submitted.

## Workspace Pinned Working State
An interactive `ScratchpadEntry` or evidence reference explicitly elevated from a specific conversation thread to the workspace level (`is_pinned_to_workspace = True`), making it eligible for injection into all subsequent research turns across the entire workspace.

## Workspace Commit Manifest
An immutable snapshot of approved workspace state capturing active `KnowledgeMemory` IDs, accepted `ResearchArtifact` candidate IDs, Output KG version reference, active hypothesis IDs, scratchpad checkpoint, conversation checkpoint, and base research runs. Commits record references to canonical state rather than duplicating content blobs.

## Timeline Epoch Fencing
The authoritative concurrency control mechanism implemented via PostgreSQL `workspace.timeline_epoch`. When a rollback occurs, `timeline_epoch` is incremented under an atomic row lock. In-flight background workers or promotion transactions verifying against a stale epoch are immediately aborted (`aborted_by_timeline_fence`), preventing historical runs from corrupting the active timeline while preserving all execution logs.

## Deterministic Verification Engine
A sandboxed, AST-based mathematical evaluator with strict resource limits (AST depth, operation count, magnitude) and whitelisted operations/functions that independently validates derived numeric claims without LLM self-evaluation or arbitrary code execution.

## Typed Provenance Reference (ProvenanceRef)
A strongly typed, workspace-scoped reference linking a research candidate or finding to its originating entity (`source`, `source_snapshot`, `block`, `research_evidence`, `research_artifact`, `knowledge_memory`, or `conversation_turn`). Provenance validation is strictly fail-closed: any cross-workspace or missing reference invalidates promotion.


