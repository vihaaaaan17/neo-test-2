# NeosisLM Architecture & Chapter 1-4 Handoff Guide

## 1. Overview & Project Purpose
**NeosisLM** is an enterprise-grade, event-driven knowledge engine that balances two distinct interaction modes:
1. **Ground Mode**: Deterministic, source-grounded question-answering with strict provenance and citation mapping over indexed documents using Open Notebook.
2. **Research Mode**: Autonomous, multi-step deep research orchestrated via asynchronous worker pools (ARQ + Redis), multi-query web search, and evidence synthesis.

The system enforces strict execution isolation between Ground and Research modes, canonical Server-Sent Events (SSE) streaming, timeline fencing (monotonic epoch counter preventing zombie jobs from mutating state after rollback), and full turn replay/reconnection capabilities.

---

## 2. Chapter Breakdown & System Architecture

### Chapter 1: Foundational Architecture & Core Engine
* **Objective**: Establish the core data layer, persistence, object storage, and working memory checkpointer.
* **Key Components**:
  * **Relational Schema ([app/models/](file:///d:/koding/codes/NeosisLM/app/models/))**: PostgreSQL via SQLAlchemy 2.0 async. Defines `Workspace`, `Conversation`, `ConversationTurn`, `ChatEvent`, `Source`, `Commit`, and `Chunk`.
  * **Object Storage ([app/services/storage.py](file:///d:/koding/codes/NeosisLM/app/services/storage.py))**: `S3ObjectStore` powered by MinIO (or AWS S3) for raw file uploads and document snapshots.
  * **Document Parsing ([app/services/parsing.py](file:///d:/koding/codes/NeosisLM/app/services/parsing.py))**: Docling/local text parsing pipeline with fallback handling for plain-text extraction.
  * **Working Memory Checkpointer ([app/services/working_memory.py](file:///d:/koding/codes/NeosisLM/app/services/working_memory.py))**: Postgres-backed LangGraph checkpointer enabling state persistence across agent steps.
  * **Graph & Vector Stores**: Neo4j (`bolt://localhost:7687`) and pgvector for entity graph queries and semantic retrieval.
* **Specification References**:
  * [docs/architecture.md](file:///d:/koding/codes/NeosisLM/docs/architecture.md)
  * [docs/inital-plan.md](file:///d:/koding/codes/NeosisLM/docs/inital-plan.md)

---

### Chapter 2: Open Notebook Ground Mode Integration
* **Objective**: Integrate Open Notebook as a containerized ground-truth and semantic retrieval engine while strictly isolating Ground execution from speculative research state.
* **Key Components**:
  * **Open Notebook HTTP Client ([app/integrations/open_notebook/client.py](file:///d:/koding/codes/NeosisLM/app/integrations/open_notebook/client.py))**:
    * Async HTTP client interfacing with the Open Notebook container on port `5055`.
    * Handles notebook creation, document uploads, semantic search, and streaming Q&A.
    * Note: Fixed canonical endpoint `GET /api/models/defaults` (plural).
  * **Ground Engine ([app/integrations/open_notebook/ground_engine.py](file:///d:/koding/codes/NeosisLM/app/integrations/open_notebook/ground_engine.py))**:
    * Implements `OpenNotebookGroundEngine` adhering to strict source isolation: ignores unverified research artifacts.
    * Supports optional `source_scope` filtering to constrain Q&A to specific documents.
    * Provides lazy notebook binding so workspaces without an existing notebook bind on demand.
  * **Citation & Provenance Mapper ([app/integrations/open_notebook/citation_mapper.py](file:///d:/koding/codes/NeosisLM/app/integrations/open_notebook/citation_mapper.py))**:
    * Maps upstream citation indices back to workspace `Source` IDs and specific chunk ranges.
  * **Projection Worker ([app/workers/tasks.py](file:///d:/koding/codes/NeosisLM/app/workers/tasks.py))**:
    * `project_to_open_notebook_job`: Asynchronously projects uploaded and committed documents into the workspace's Open Notebook notebook.
* **Specification References**:
  * [docs/chapter-2/NEOSISLM_CHAPTER_2_IMPLEMENTATION_SPEC.md](file:///d:/koding/codes/NeosisLM/docs/chapter-2/NEOSISLM_CHAPTER_2_IMPLEMENTATION_SPEC.md)
  * [docs/chapter-2/OPEN_NOTEBOOK_GROUND_INTEGRATION_ARCHITECTURE_OPERATIONS_GUIDE.md](file:///d:/koding/codes/NeosisLM/docs/chapter-2/OPEN_NOTEBOOK_GROUND_INTEGRATION_ARCHITECTURE_OPERATIONS_GUIDE.md)

---

### Chapter 3: Autonomous Deep Research Engine Migration
* **Objective**: Deliver asynchronous background research with budget tracking, evidence management, and multi-query search.
* **Key Components**:
  * **Worker Settings & Tasks ([app/workers/settings.py](file:///d:/koding/codes/NeosisLM/app/workers/settings.py), [app/workers/tasks.py](file:///d:/koding/codes/NeosisLM/app/workers/tasks.py))**:
    * ARQ worker process connected to Redis (`redis://localhost:6379`).
    * Runs `run_research_agent_job`: executes background research jobs and publishes events to Redis Pub/Sub channels `research:{job_id}` and `research_events:{run_id}`.
    * `ctx["llm_call"]`: OpenAI-compatible LLM gateway function.
  * **Research Engine Factory & Strategy ([app/integrations/research_engine/](file:///d:/koding/codes/NeosisLM/app/integrations/research_engine/))**:
    * `legacy`: Multi-step iterative search, source evaluation, and report synthesis.
    * `open_deep_research`: LangGraph-based hierarchical research agent (planner, sub-researchers, synthesizer) with token and step budgeting.
  * **Research Data Models ([app/models/research.py](file:///d:/koding/codes/NeosisLM/app/models/research.py))**:
    * `ResearchRun`: Tracking lifecycle states (`admitted`, `planning`, `running`, `completed`, `failed`, `cancelled`).
    * `ResearchEvent`: Audit log of research progress.
    * `ResearchArtifact`: Intermediate search extractions and text scraps.
    * `ResearchReport`: Final synthesis markdown report.
  * **Web Search Tooling ([app/services/web_search.py](file:///d:/koding/codes/NeosisLM/app/services/web_search.py), [app/integrations/research_engine/tools/neosis_search_tools.py](file:///d:/koding/codes/NeosisLM/app/integrations/research_engine/tools/neosis_search_tools.py))**:
    * Tavily-based search tool supporting multi-query parallel batch retrieval.
* **Specification References**:
  * [docs/chapter-3/NEOSISLM_CHAPTER_3_FOUR_PHASE_IMPLEMENTATION_PLAN.md](file:///d:/koding/codes/NeosisLM/docs/chapter-3/NEOSISLM_CHAPTER_3_FOUR_PHASE_IMPLEMENTATION_PLAN.md)
  * [docs/chapter-3/CH3_RESEARCH_MIGRATION_RUNBOOK.md](file:///d:/koding/codes/NeosisLM/docs/chapter-3/CH3_RESEARCH_MIGRATION_RUNBOOK.md)

---

### Chapter 4: Full-Stack Integration, Canonical SSE Streaming, Timeline Fencing & Promotion
* **Objective**: End-to-end integration across the HTTP layer, SSE streaming, turn replay, timeline fencing, and artifact promotion.
* **Key Components**:
  * **Canonical SSE Streaming ([app/api/routes/turns.py](file:///d:/koding/codes/NeosisLM/app/api/routes/turns.py))**:
    * Serves `text/event-stream` with strict W3C compliance:
      ```
      id: 1
      event: turn.started
      data: {"turn_id": "...", ...}

      : keep-alive
      ```
    * Streams live events from Redis while ensuring all events are persisted to PostgreSQL `ChatEvent` records.
  * **Replay & Reconnection Protocol**:
    * Respects the `Last-Event-ID` request header.
    * Upon reconnection, queries `ChatEvent` rows where `sequence > Last-Event-ID`, replays them sequentially, and then transitions seamlessly to live Redis events.
  * **Timeline Fencing**:
    * Every workspace tracks a `timeline_epoch: int`.
    * When a rollback occurs ([app/api/routes/workspaces.py](file:///d:/koding/codes/NeosisLM/app/api/routes/workspaces.py)), the epoch is incremented.
    * Active background jobs and late-arriving events verify that `run.timeline_epoch == workspace.timeline_epoch`. If the epoch has changed, the job is fenced off and terminated without corrupting the rolled-back state.
  * **Artifact Promotion**:
    * Allows verified research reports and artifacts from completed research runs to be promoted into permanent workspace `Source` records and committed to the timeline.
* **Specification References**:
  * [docs/CHAPTER-4/CHAPTER_4_BACKEND_ARCHITECTURE_SPEC.md](file:///d:/koding/codes/NeosisLM/docs/CHAPTER-4/CHAPTER_4_BACKEND_ARCHITECTURE_SPEC.md)
  * [docs/CHAPTER-4/chapter4-api-contract.md](file:///d:/koding/codes/NeosisLM/docs/CHAPTER-4/chapter4-api-contract.md)
  * [docs/CHAPTER-4/chapter4-event-catalog.md](file:///d:/koding/codes/NeosisLM/docs/CHAPTER-4/chapter4-event-catalog.md)
  * [docs/CHAPTER-4/chapter4-state-model.md](file:///d:/koding/codes/NeosisLM/docs/CHAPTER-4/chapter4-state-model.md)

---

## 3. UI Testbed Console ([ui/app.py](file:///d:/koding/codes/NeosisLM/ui/app.py))

### Design Philosophy
The Streamlit testbed (`streamlit run streamlit_app.py`) serves as a **Zero Engine Bypass** developer testbed.
* **Zero Engine Bypass**: It **never** imports backend services, repositories, engines, or ORM models.
* **Pure HTTP/SSE Client**: Communicates exclusively through canonical FastAPI endpoints (`/api/v1/...`) via `httpx`.
* **Zero Emojis**: Conforms strictly to professional enterprise UI styling without emojis.
* **Safe JSON Rendering**: Uses `safe_display_json()` to avoid client-side JavaScript syntax errors on raw strings or SSE keepalive comments.

### The 6 Dedicated Panels & Tabs
1. **Chat & Execution (`tab_chat`)**:
   * Mode toggle: Ground Mode vs Research Mode.
   * Ground Mode: Source isolation multiselect (`selected_source_ids`).
   * Research Mode: Engine selector (`open_deep_research` vs `legacy`) and Token Budget input.
   * Controls: **Submit Turn**, **Cancel Turn**, and **Reconnect Stream**.
   * Real-time event log, live answer token accumulation, error reporting, and citation metadata display.
2. **Storage / Ingestion Integration (`tab_sources`)**:
   * File upload to MinIO/S3 via `/api/v1/workspaces/{id}/sources/upload`.
   * Commit source changes to timeline via `/api/v1/workspaces/{id}/commits`.
   * Triggers background parsing, chunking, and Open Notebook projection jobs.
   * Real-time inspection of workspace source list and commit history.
3. **Turn Replay & Inspection (`tab_replay`)**:
   * Test replay from arbitrary `Last-Event-ID`.
   * Validates that historical events match the canonical sequence and payload without event drops or duplication.
4. **Promotion Testing (`tab_promotions`)**:
   * Selects completed research runs and previews generated research reports.
   * Triggers promotion to workspace sources (`POST /api/v1/workspaces/{id}/promotions/promote`).
   * Verifies that promoted sources immediately become available for Ground Mode retrieval.
5. **Rollback & Timeline Fencing (`tab_rollback`)**:
   * Inspects commit log and selects a target commit for timeline rollback (`POST /api/v1/workspaces/{id}/rollback`).
   * Displays the newly incremented `timeline_epoch`.
   * Proves timeline fencing: executing or completing jobs with a stale epoch are rejected with `timeline_fenced`.
6. **Debug / Raw API Inspector (`tab_debug`)**:
   * Inspects the exact HTTP request/response traces (method, URL, headers with masked authorization tokens, status code, latency, and full JSON payload).

---

## 4. Key Fixes & Operational Gotchas

1. **Open Notebook Endpoint Plurality**:
   * Upstream Open Notebook spec exposes `GET /api/models/defaults` (plural). Calling singular `/default` returned `405 Method Not Allowed`, translated as `502 ground_execution_failed`. Fixed in [app/integrations/open_notebook/client.py](file:///d:/koding/codes/NeosisLM/app/integrations/open_notebook/client.py).
2. **LangSmith Context Error**:
   * LangGraph runs within an asynchronous generator. Unconditionally entering `with tracing_v2_enabled()` without `LANGCHAIN_API_KEY` caused `ValueError: <Token> was created in a different Context`. Guarded with `nullcontext()` across orchestrators.
3. **SSE Keep-Alive Line Handling**:
   * W3C SSE keepalive lines start with `:` (e.g. `: keep-alive`). The SSE parser in [ui/app.py](file:///d:/koding/codes/NeosisLM/ui/app.py) was updated to ignore comments rather than treating them as corrupted JSON events.
4. **S3 Client Injection in Background Worker**:
   * In [app/workers/tasks.py](file:///d:/koding/codes/NeosisLM/app/workers/tasks.py), `parse_and_chunk_job` was modified to construct `S3ObjectStore(s3_client)` using `ctx.get("s3_client")` instead of expecting a FastAPI `Request` object.
5. **Turn Failure Reason Exposure**:
   * In [app/workers/tasks.py](file:///d:/koding/codes/NeosisLM/app/workers/tasks.py), when a research run fails, the failure message is recorded into `assistant_message` on the `ConversationTurn` and emitted in `turn.failed` payload so the UI displays the exact failure reason instead of remaining blank.
6. **OpenAI Compatibility**:
   * The codebase relies on standard OpenAI client / `ChatOpenAI` paradigms (`OPENAI_API_KEY`, optional `OPENAI_BASE_URL`, model parameter). Custom or vendor-specific hardcodings (e.g. Gemini) are avoided in the core code to ensure universal provider compatibility.

---

## 5. Environment & Infrastructure Setup

### Services & Ports
* **PostgreSQL**: `localhost:5432` (`neosislm`)
* **Redis**: `localhost:6379`
* **Neo4j**: `localhost:7687` (HTTP: `localhost:7474`)
* **MinIO / S3**: `localhost:9000` (Console: `http://localhost:9001`, user: `minioadmin`, pass: `minioadmin`)
* **Open Notebook**: `localhost:5055`
* **FastAPI Backend**: `http://localhost:8000`
* **Streamlit UI**: `http://localhost:8501`

### Environment Files
* [.env](file:///d:/koding/codes/NeosisLM/.env): Core backend configuration (`DATABASE_URL`, `REDIS_URL`, `NEO4J_URI`, `S3_*`, `OPEN_NOTEBOOK_*`).
* [.env.ui](file:///d:/koding/codes/NeosisLM/.env.ui): UI testbed and model gateway credentials (`API_BASE_URL`, `TAVILY_API_KEY`, etc.).

---

## 6. How to Run & Verify

1. **Start Infrastructure Services**:
   ```powershell
   docker compose up -d
   ```
2. **Start FastAPI Backend**:
   ```powershell
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
3. **Start ARQ Background Worker**:
   ```powershell
   python -m arq app.workers.settings.WorkerSettings
   ```
4. **Launch Streamlit Testbed**:
   ```powershell
   streamlit run streamlit_app.py
   ```

---

## 7. Suggested Skills for Next Agent
When continuing work on this codebase, invoke the following skills depending on the task:
* **`code-review`**: For verifying that upcoming PRs or feature branches adhere to Chapter 4 API contracts and standards.
* **`systematic-debugging`**: If investigating any asynchronous ARQ worker exceptions or SSE connection drops.
* **`safe-refactor`**: When refactoring or deepening interfaces in `app/integrations/` or `app/workers/`.
* **`graphify`**: Run `graphify update .` to keep the knowledge graph synchronized after code changes.
