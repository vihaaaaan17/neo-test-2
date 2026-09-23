# NeosisLM Phase 1–6 Handoff Document

> **Purpose**: Enable any fresh agent session to continue work on NeosisLM from exactly where Phase 6 ended, without re-reading the entire conversation history.
> 
> **Date**: 2026-09-18  
> **Last Commit**: `c8b7b8c feat(export): Integrate export button in Streamlit UI (Phase 6 Ticket 3)`

---

## 1. What Is NeosisLM?

A dual-mode AI research platform combining:
- **Ground Mode** — Strict source-grounded Q&A (NotebookLM style). Answers only from uploaded workspace documents. Zero hallucination tolerance.
- **Research Mode** — Autonomous deep-research agent (LangGraph + Tavily web search). Plans, executes, synthesizes, and maps findings into a semantic Knowledge Graph.

Both modes share a single canonical memory fabric so discoveries in Research Mode become citable facts in Ground Mode.

The holy-grail spec document is: `.scratch/neosis-architecture/spec.md` and `inital-plan.md` (the Master Architecture Inventory).

---

## 2. What Has Been Built (Phase 1 → 6)

### Phase 1 — Foundations
- PostgreSQL schema: `Workspace`, `Source`, `SourceSnapshot`, `Block`, `Chunk` models
- S3-compatible `ObjectStoreProtocol` / `S3ObjectStore` for immutable blob storage
- `WorkspaceRepository`, `SourceRepository`, `BlockRepository` 
- Alembic migration pipeline
- JWT-based `get_current_user` auth dependency
- FastAPI app skeleton with health check

### Phase 2 — Memory & State
- Six-memory system: `KnowledgeMemory`, `EpisodicMemory`, `WorkingMemory` models + repos
- `EpisodicCompressionService` (LLM-based summarization of event history)
- Git-like workspace versioning: `WorkspaceCommit` model, `create_commit`, `set_active_commit`, rollback
- Pydantic schemas: `KnowledgeMemoryCreate`, `Provenance`, `ResearchContext`

### Phase 2.5 — Scalability
- `arq` + Redis background job queue (`WorkerSettings`, 5 registered jobs)
- API hardening: `slowapi` rate limits, CORS, 50MB upload cap, lifespan management
- `QuotaService`: workspace/source/storage limits per tenant
- Database hardening: `NullPool`, JSONB GIN indexes, scalability migrations

### Phase 3 — Knowledge Graph
- Neo4j integration: `Neo4jAdapter` (driver-managed), `GraphRepository`
- `project_output_graph` — projects Pydantic `OutputGraph` (nodes + edges) into Neo4j
- `sync_knowledge_to_graph_job` — background job syncing knowledge to graph
- `HybridRetrievalService` — combined pgvector semantic + Postgres FTS retrieval

### Phase 4 — Research Mode
- `ResearchModeOrchestrator` (LangGraph): `planner → executor → synthesizer → reporter` cycle
- `GroundModeOrchestrator`: strict internal-only Q&A with grounding verification
- `WebSearchTool` (Tavily integration)
- `/ask` endpoint (Ground Mode) and `/research` endpoint (Research Mode)
- SSE streaming via Redis Pub/Sub (`/jobs/{job_id}/stream`)
- `streamlit_app.py` — 3-tab testing UI (Workspace, Ground Mode, Research)

### Phase 5 — Evaluation & Reliability
- `MemoryRouter` service: deduplication, knowledge persistence, background graph sync
- Integration into both orchestrators
- Selective LangSmith tracing (agent loops traced, trivial calls skipped)

### Phase 6 — Production Hardening
- `WorkspaceExportService`: polyglot export (Parquet chunks + JSON metadata → ZIP → S3)
- `export_workspace_job`: arq background job with Redis Pub/Sub progress events
- Worker startup wired with S3 client (aioboto3)
- Streamlit Tab 4: "Export Data" with real-time Pub/Sub polling + presigned download link

---

## 3. Key File Map

| Area | Files |
|------|-------|
| **Config** | `app/core/config.py`, `app/core/database.py`, `app/core/telemetry.py` |
| **Models** | `app/models/workspace.py`, `source.py`, `block.py`, `knowledge.py`, `episodic.py` |
| **Repositories** | `app/repositories/workspace.py`, `source.py`, `block.py`, `knowledge.py`, `episodic.py`, `graph.py` |
| **Services** | `app/services/storage.py`, `parsing.py`, `chunking.py`, `episodic.py`, `memory_router.py`, `hybrid_retrieval.py`, `web_search.py`, `quota.py`, `export.py` |
| **Orchestration** | `app/orchestration/ground_mode.py`, `research_mode.py` |
| **API Routes** | `app/api/routes/workspaces.py`, `jobs.py` |
| **Workers** | `app/workers/settings.py`, `tasks.py` |
| **Schemas** | `app/schemas/workspace.py`, `knowledge.py`, `graph.py`, `ground_mode.py`, `context.py` |
| **Tests** | `tests/test_*.py` (21 test files) |
| **Migrations** | `alembic/versions/*.py` |
| **Frontend** | `streamlit_app.py` |
| **Docs** | `docs/README.md`, `architecture.md`, `setup.md`, `orchestrators.md`, `api.md`, `migrations.md`, `WHAT_IS_NEOSISLM.md` |

---

## 4. Commit History

```
c8b7b8c feat(export): Integrate export button in Streamlit UI (Phase 6 Ticket 3)
9482d00 feat(export): Build export_workspace_job background worker (Phase 6 Ticket 2)
565cfe7 feat(export): Build WorkspaceExportService (Phase 6 Ticket 1)
84e3c6f Phase 5 Ticket 3: Selective LangSmith Tracing
dfd01fd Phase 5 Ticket 2: Integrate Router into Orchestrators
e501ab0 Phase 5 Ticket 1: MemoryRouterService
61ad9a6 wip: Phase 4 completion
1c7cc4d feat(phase3): Ticket 17 - Local Neo4j Adapter
5236d30 fix(db): correct JSONB expression index for source_mode in migrations
b2cf866 feat(api): Ticket 16 - Tenant Quotas & LLM Backpressure
d571e70 feat(api): Ticket 15 - API Hardening (Rate Limits, CORS, Lifespan)
67c7705 feat(scalability): Ticket 14 - background job queue (arq + Redis)
87bacf0 feat(scalability): Ticket 13 - database hardening for 1000-user scale
```

---

## 5. Architecture Invariants (Do Not Break These)

1. **Provider Agnosticism**: All LLM calls go through `LiteLLM`. All storage goes through `ObjectStoreProtocol`. All graph ops go through `GraphRepository`. Never hardcode a vendor.
2. **Tenant Isolation**: Every API endpoint validates `workspace_id` against `current_user_id`. No cross-tenant data access is ever permitted.
3. **Two Graphs**: Internal KG (Postgres canonical) and Output KG (Neo4j projection). The Output KG is a derived view, never a source of truth.
4. **Background Execution**: Anything taking >500ms belongs in an `arq` job, never in the request cycle.
5. **Grounded Mode Integrity**: `GroundModeOrchestrator` must NEVER use web search. It answers from workspace evidence only, or rejects the query.

---

## 6. Known Technical Debt

- `WorkerSettings.on_startup` initializes `s3_client` inline rather than through a shared factory — acceptable for now but should be unified with the FastAPI lifespan pattern.
- `HybridRetrievalService` returns mock data for pgvector queries in tests since the local venv doesn't have a running Postgres with pgvector enabled.
- No `docker-compose.test.yml` for full integration tests with live databases.
- `streamlit_app.py` uses `asyncio.run()` which creates a new event loop per action — fine for testing UI but not production-grade.

---

## 7. Suggested Skills for Next Session

- **`implement`** — For executing any new tickets with the gated discipline.
- **`unlazy`** — For ensuring completeness via Depth Trees and Gate Ledgers.
- **`code-review`** — For two-axis review (Standards + Spec) of completed work.
- **`detective`** / **`diagnosing-bugs`** — If integration tests surface failures.
- **`domain-modeling`** — If new phases introduce domain concepts not yet in the schema.
- **`grilling`** — For stress-testing design decisions before committing to them.

---

## 8. What Comes Next

The user intends to begin **"Chapter 2"** of the build. The specific scope has not yet been defined, but based on the Master Architecture Inventory (`inital-plan.md`), the following components from the spec are **not yet implemented**:

- Phase 2 components: Internal KG core node taxonomy, temporal model, episodic compression triggers, reranker, code/compute sandbox
- Evaluation: Offline eval suite (LangSmith/LangChain based), online eval, human review loops
- Verification: Evidence verifier, contradiction detector, research critic
- Synthesis: Report generator with citation bundles
- Advanced agent tools: Math engine (SymPy), code sandbox
- Security: Prompt injection defense, sandboxing

The next session should read `inital-plan.md` and this handoff to determine priority order.
