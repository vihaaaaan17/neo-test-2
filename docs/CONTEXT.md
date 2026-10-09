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

## Research Engine
The upstream runtime that performs research: planning, task decomposition, the search/research loop, reflection, synthesis and report
generation. Three are supported: Open Deep Research (ODR, vendored under `app/integrations/research_engine/upstream/`), STORM (isolated
`venv-storm`) and GPT-Researcher. Neosis never reimplements an engine's algorithm.

## Engine Adapter
The thin Neosis class (`ResearchEngine` subclass, e.g. `OpenDeepResearchEngine`) that translates Neosis inputs into the upstream runtime's
configuration, injects bounded research context, and translates upstream execution signals into Neosis progress events. It owns no
research logic, persists no reports or candidates, and writes no environment variables.

## Supported Engines
`SUPPORTED_ENGINES` in `app/integrations/research_engine/engine.py`: the single allow-list of engine names admission accepts and the
factory can instantiate (`open_deep_research`, `storm`, `gpt_researcher`). Anything else is rejected at admission with `422 unsupported_research_engine`.

## Turn Response Event
`{"status": "turn_response", "text": <markdown>, "format": "conversational" | "article", "evidence_refs": [...]}` (built with
`turn_response()`) — the one event through which an engine hands its answer for a turn to the worker as data. Engines request a
conversational answer through their own controls (ODR: the user message; GPT-Researcher: `write_report(custom_prompt=...)`); STORM has
no such control and returns `format="article"`. The worker stores `text` as the turn's `assistant_message` and publishes it with the
evidence and routing record. It is never bridged to chat as a progress event and never becomes a ResearchReport.

## Routing Mode
`research_runs.routing_mode`: `auto` (the EngineRouter chooses; `engine` stays NULL until an attempt answers, then names the answering
engine) or `explicit` (the named engine, for testing/overrides). "auto" is never an engine name. Default for chat turns: `auto`.

## Engine Router
`EngineRouter` (`app/integrations/research_engine/router.py`), between the worker and the adapters.
- Deterministic intent rules: simple → ODR `low`; normal → ODR `balanced`; deep → STORM; broad → GPT-Researcher. The
  preferred specialist is used when it passes its Engine Readiness Gate and gets a capacity slot.
- A deterministic sufficiency assessment of ODR answers, calibrated in `tests/fixtures/routing/assessment_cases.json`, checks:
  unanswered parts, unresolved relationships, engine-reported gaps, uncited claims, relevant-domain coverage, duplication and
  depth.
- At most ONE sequential specialist escalation, chosen by the diagnosed deficiency.
- One Turn Budget across all attempts. Engines never run in parallel for one turn.

## Turn Budget
The execution policy shared by every attempt of one Research turn: a wall-clock deadline (`ROUTER_TURN_DEADLINE_S`, below the
ARQ job timeout), at most two attempts, a measured-token ceiling (`ROUTER_TURN_TOKEN_CEILING`), per-engine timeouts capped by
the remaining time, and specialist concurrency slots. It never resets between attempts.

## Preferred vs Actual Engine
`preferred_engine` is what the intent rules wanted; `engine` on the attempt / run is what actually executed and answered. They
differ when a specialist was not eligible, at capacity, or failed (then ODR answers).

## Engine Attempt
A row in `research_engine_attempts`: one engine execution in a run.
- Identity: sequence, actual `engine`, `preferred_engine`, `routing_mode`, budget profile, trigger, reason, status.
- Measurements: tokens, cost, `usage_quality` (whether tokens and cost were measured, estimated or unavailable), latency,
  and `timings` (router stages plus engine metrics).
- Outcome: evidence count, and the assessment with its escalation decision.

`research_runs.current_attempt_id` points to the answering attempt.

## Engine Readiness Gate
Per specialist: `ROUTER_AUTO_STORM` / `ROUTER_AUTO_GPT_RESEARCHER` = `auto` (default) | `off`, AND runtime prerequisites
(credentials, STORM env with `knowledge_storm`, `gpt_researcher` installed), AND a free capacity slot. States: eligible,
disabled, unavailable, at capacity. Distinct from production-capacity approval (see `docs/engine-readiness.md`).

## Ground Evidence Resolution
`app/integrations/open_notebook/ground_evidence.py`. A Ground answer's provenance (Open Notebook's inline `[source:<id>]`
citations, its chat evidence and its instance-wide search hits) is resolved to canonical `Source` records ONLY through this
workspace's `OpenNotebookSourceBinding` rows (never by title). Resolved sources carry stored metadata (file name, document
reference, an excerpt from the stored blocks).
- Provenance statuses:
  - `full`: every citation resolved;
  - `partial`: some citations resolved and the rest are listed in `unresolved_citations`;
  - `none`: the answer made no citation; it is kept and flagged as not verified.
- An answer whose citations ALL fail to resolve is rejected (`ground_provenance_failure`), because it may rest on another
  tenant's content.
- Foreign search hits are ignored.

## Turn Closure
Every Ground and Research turn ends in exactly one terminal state via compare-and-set on `pending`/`running`: failures,
unexpected upstream data, cancellation (including a cancelled HTTP request) and rejected scopes close the turn. A
source scope (or its `selected_source_ids` alias) is validated before the turn row exists. On submission, an active
turn that provably cannot still be executing (a stale Ground turn with no live task; a Research turn whose run is already
terminal) is recovered. A live turn still returns 409 `conversation_turn_in_progress`.

## Study-Session Report
A formal, cited paper compiled from a whole conversation by `StudyReportCompiler` (`app/services/research/study_report.py`), only on an
explicit request (`POST .../conversations/{id}/study-report`, or a turn such as "Compile everything we've discussed into a research
paper"). Stored as a `research_reports` row with `scope = "study_session"` anchored to the conversation (never to a run), plus one
`pending_review` memory candidate. One structured LLM call returns claims with kinds and catalog citations; citations must exist
in the session's catalog (cited workspace sources + the conversation's ResearchEvidence) and match the stored evidence text, or
the claim is marked unsupported.
- Support levels:
  - `verified_passage`: the claim's quote appears verbatim in the stored evidence and matches the claim's terms;
  - `related_source`: the cited source is only topically related, so the claim is labelled;
  - `none`: no support, so the claim is marked unsupported.
- References are generated from the catalog. Recompiles are versioned. It runs no research and is not a fact-check.

## Terminal State Owner
The research worker (`run_research_agent_job`). It alone decides and writes a run's terminal state (`completed`, `partial`, `failed`,
`cancelled`, `aborted_by_timeline_fence`) and publishes exactly one terminal event. Engines signal failure by raising; a run is
`completed` only if a non-empty Turn Response Event was received. Ordinary turns create no ResearchReport and no candidate.

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


