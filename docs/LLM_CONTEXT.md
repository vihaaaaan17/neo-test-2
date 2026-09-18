# NeosisLM — LLM Context Document

> **What this file is**: Give this document to any LLM agent that will work on the NeosisLM codebase. It contains everything the agent needs to understand the project, its constraints, what has been built, and how to navigate the code.

---

## Identity

**NeosisLM** is a dual-mode AI research platform. It combines:

1. **Ground Mode** — Source-grounded question-answering. Answers strictly from documents the user uploaded to their workspace. No hallucinations, no web access. Every answer includes provenance back to the source paragraph. Think: NotebookLM.

2. **Research Mode** — Autonomous deep-research. Given a high-level objective, a multi-agent LangGraph pipeline plans a research strategy, scrapes the web via Tavily, synthesizes findings, and produces a semantic Knowledge Graph mapping concepts and their relationships. Think: Open Deep Research / STORM.

Both modes share a single canonical memory and knowledge fabric within a `Workspace`. A discovery made in Research Mode becomes a citable fact in Ground Mode.

---

## Authoritative References

These are the two documents that govern all architectural decisions. If there is ever a conflict between what you think is right and what these documents say, **these documents win**:

- **`inital-plan.md`** (root) — The Master Architecture & Implementation Inventory. Every component, its fields, lifecycle, tech stack, and migration strategy. This is the holy grail.
- **`.scratch/neosis-architecture/spec.md`** — The detailed architectural spec.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API | FastAPI | Async REST API |
| Database | PostgreSQL + SQLAlchemy | Canonical data store |
| Vector Search | pgvector | Semantic retrieval |
| Text Search | PostgreSQL FTS | Keyword retrieval |
| Graph Database | Neo4j | Output Knowledge Graph projection |
| Object Storage | S3-compatible (aioboto3) | Immutable blob storage |
| Job Queue | arq + Redis | Async background tasks |
| Agent Framework | LangGraph | Multi-step agent orchestration |
| LLM Gateway | LiteLLM | Provider-agnostic model access |
| Web Search | Tavily | Autonomous web research tool |
| Observability | OpenTelemetry + LangSmith | Tracing & evaluation |
| Frontend (test) | Streamlit | End-to-end testing UI |
| Migrations | Alembic | Database schema evolution |

---

## Directory Structure

```
NeosisLM/
├── app/
│   ├── api/
│   │   ├── deps/          # FastAPI dependencies (auth, arq, rate_limit, llm)
│   │   └── routes/        # workspaces.py, jobs.py
│   ├── core/              # config.py, database.py, telemetry.py
│   ├── models/            # SQLAlchemy models (workspace, source, block, knowledge, episodic)
│   ├── orchestration/     # ground_mode.py, research_mode.py (LangGraph)
│   ├── repositories/      # Data access layer (workspace, source, block, knowledge, episodic, graph)
│   ├── schemas/           # Pydantic request/response models
│   ├── services/          # Business logic (storage, parsing, chunking, episodic, memory_router,
│   │                      #   hybrid_retrieval, web_search, quota, export)
│   └── workers/           # arq job definitions (settings.py, tasks.py)
├── alembic/               # Database migrations
├── tests/                 # 21 test files
├── docs/                  # Documentation (architecture, setup, API, orchestrators, migrations, pitch)
├── streamlit_app.py       # 4-tab testing UI
├── docker-compose.yml     # Postgres, Redis, Neo4j
├── requirements.txt       # Python dependencies
└── inital-plan.md         # THE authoritative architecture spec
```

---

## Architectural Rules (NEVER VIOLATE)

1. **Provider Agnosticism** — All LLM calls go through LiteLLM. All storage through `ObjectStoreProtocol`. All graph through `GraphRepository`. Never import a vendor SDK directly in business logic.

2. **Tenant Isolation** — Every endpoint validates `workspace_id` against `current_user_id`. No cross-tenant data access. Ever.

3. **Two Graphs** — Internal KG lives in Postgres (canonical). Output KG lives in Neo4j (projection). Neo4j is never the source of truth.

4. **Background Execution** — Anything taking >500ms goes into an arq job. Never block the API request cycle with heavy computation.

5. **Ground Mode Integrity** — `GroundModeOrchestrator` must NEVER access web search. It answers from workspace evidence only, or honestly rejects the query.

6. **Blobs Never in Postgres** — Uploaded files are stored in S3. Postgres stores metadata and URIs only.

7. **Schema-First** — All data contracts use Pydantic models. State mutations go through typed schemas, not raw dicts.

---

## What Has Been Built (Phases 1–6)

| Phase | Focus | Key Components |
|-------|-------|---------------|
| 1 | Foundations | Workspace/Source/Block models, S3 storage, Alembic migrations, auth, health check |
| 2 | Memory & State | KnowledgeMemory, EpisodicMemory, WorkingMemory, git-like commits/rollback |
| 2.5 | Scalability | arq+Redis queue, rate limiting, CORS, quotas, DB hardening (NullPool, GIN indexes) |
| 3 | Knowledge Graph | Neo4j adapter, GraphRepository, Output KG projection, HybridRetrievalService |
| 4 | Research Mode | LangGraph orchestrators (Research + Ground), Tavily search, SSE streaming, Streamlit UI |
| 5 | Reliability | MemoryRouter (dedup + sync), selective LangSmith tracing |
| 6 | Production Hardening | WorkspaceExportService (Parquet+JSON→ZIP), export background job, Streamlit export tab |

---

## What Has NOT Been Built Yet

From the Master Architecture Inventory, these components remain:

### High Priority (Spec says P0/P1)
- **Evidence Verifier** — LLM-as-judge checking if claims are actually supported by evidence
- **Research Critic** — Agent that challenges findings, finds gaps, weak conclusions
- **Contradiction Detector** — Identifies conflicting claims across sources
- **Report Generator** — Produces structured, citation-aware research outputs
- **Offline Eval Suite** — LangChain/LangSmith-based regression testing
- **Code/Compute Sandbox** — Safe execution of data analysis code
- **Internal KG Core Taxonomy** — Full node/edge taxonomy in Neo4j (currently only Output KG)
- **Temporal Model** — Valid-from/valid-to/observed-at fields on graph nodes

### Medium Priority
- **Reranker** — Cross-encoder second-stage ranking for retrieval
- **Online Eval** — Production quality monitoring via sampled traces
- **Human Review Loop** — User feedback/correction on claims and graph edges
- **Math Engine** — SymPy integration for deterministic calculations
- **Prompt Injection Defense** — Treat retrieved content as untrusted input

### Lower Priority / Future
- **LaTeX Pipeline** — Publication-ready artifact generation
- **Grounded Conversation** — Multi-turn chat with source pinning
- **Dual Write / Shadow Read** — Safe storage migration infrastructure

---

## How to Run

```bash
# 1. Infrastructure
docker-compose up -d

# 2. Migrations
alembic upgrade head

# 3. API server
uvicorn app.main:app --reload --port 8000

# 4. Background worker
python -m arq app.workers.settings.WorkerSettings

# 5. Test UI
streamlit run streamlit_app.py
```

---

## Handoff Reference

For the detailed handoff with commit history, technical debt, and file-by-file breakdown, see:
- `.scratch/phase1_to_6_handoff.md`

For the master architecture spec:
- `inital-plan.md`
