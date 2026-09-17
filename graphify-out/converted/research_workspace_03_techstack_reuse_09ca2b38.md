<!-- converted from research_workspace_03_techstack_reuse.xlsx -->

## Sheet: Index
| 03 — Technology Stack & Reuse |  |  |  |
| --- | --- | --- | --- |
| Sheet | Purpose | Source Coverage | Notes |
| Tech Stack & Migration | Initial/free-tier technologies and future scale-up paths. | 18 technology categories | Includes abstraction boundaries and migration triggers. |
| Build vs Reuse | Explicit build/adapt/reuse decisions. | 20 components | Separates commodity infrastructure from product-specific IP. |
## Sheet: Tech Stack & Migration
| Category | Initial / Free Tier | Why Initial | Scale-Up | Migration Trigger | Abstraction Boundary |
| --- | --- | --- | --- | --- | --- |
| Web | Next.js + React + TypeScript | Mature, reusable UI ecosystem | Managed/edge deployment as needed | Traffic/latency | HTTP/API contract |
| Backend | FastAPI + Python | Agent ecosystem + typed APIs | Service decomposition | Team/traffic growth | Domain service interfaces |
| Relational DB | PostgreSQL via Supabase or equivalent | Canonical source of truth; pgvector available | Managed Postgres cluster/read replicas | Connection/storage/throughput | Repository layer |
| Vector | pgvector | Avoid extra service early | Qdrant/dedicated vector DB | Recall/latency/index size | VectorStore |
| Graph | Neo4j Aura Free/local | Proper graph semantics | Managed Neo4j cluster | Graph size/query load | GraphStore |
| Cache/Queue | Redis | Simple cache + queue primitives | Managed Redis / broker | Queue volume/HA needs | CacheProvider + QueueProvider |
| Object storage | Supabase Storage/S3-compatible | Simple and portable | S3/R2/GCS | Storage/cost/egress | ObjectStore |
| Agent orchestration | LangGraph | Explicit state/checkpoint model | Durable workflow platform | Run volume/availability | Workflow interface |
| Notebook/RAG | Open Notebook | Avoid rebuilding ingestion/chat/source management | Custom specialized services | Upstream divergence or scale | Notebook adapter |
| Research | STORM/GPT Researcher patterns | Reuse research decomposition ideas | Custom research workers | Latency/cost/control needs | ResearchAgent interface |
| Parsing | Docling | Strong multimodal/document parsing baseline | Specialized parsing/OCR services | Format coverage/volume | Parser interface |
| LLM gateway | LiteLLM | Provider abstraction and routing | Dedicated model gateway | Provider count/traffic | LLMProvider |
| Evaluation | LangChain/LangSmith | User requested LangChain evals | Dedicated eval platform if needed | Eval scale/enterprise controls | Evaluator interface |
| Observability | OpenTelemetry | Vendor-neutral instrumentation | Managed backend | Scale/retention | Telemetry interface |
| Browser | Playwright | Reliable open-source browser automation | Browser fleet/service | Concurrency/anti-bot | BrowserTool |
| Math | SymPy + Python | Deterministic local calculations | Sandbox compute service | Compute limits | ComputeTool |
| Execution sandbox | Docker/container isolation | Simple initial containment | gVisor/Firecracker/K8s jobs | Security/concurrency | ExecutionService |
## Sheet: Build vs Reuse
| Component | Do We Build? | Reuse/Reference | Expected Custom Work |
| --- | --- | --- | --- |
| Notebook/RAG UI backend | No, adapt | Open Notebook | Fork/integrate ingestion, sources, chat with shared state contract |
| Deep research loop | No from scratch | STORM, GPT Researcher, Open Deep Research patterns | Implement custom graph nodes, evidence policies, state integration |
| Agent orchestration | No from scratch | LangGraph | Define workflows, state schema, reducers, policies |
| Document parsing | No from scratch | Docling | Adapter + post-processing |
| Browser automation | No from scratch | Playwright | Tool wrapper, sandbox, source policy |
| Math engine | No from scratch | SymPy | Sandbox wrapper + provenance |
| LLM provider abstraction | No from scratch | LiteLLM | Routing policy, model registry |
| Evals | No from scratch | LangChain/LangSmith | Datasets, custom graders, research rubrics |
| Telemetry | No from scratch | OpenTelemetry | Instrumentation + dashboards |
| Cache | No from scratch | Redis | Key policy + cache invalidation |
| Primary relational DB | Use managed open source | PostgreSQL/Supabase | Domain schema, migrations, RLS |
| Graph storage | Use managed open source | Neo4j | Ontology, projections, integrity checks |
| Memory fabric | Yes | Build product-specific | 6 logical memories + router + compaction + provenance |
| State engine | Yes + LangGraph | LangGraph | 8 state domains + reducers + transitions |
| Internal KG | Yes, product-specific | Neo4j storage | Ontology + projections + lifecycle |
| Research Output KG | Yes, product-specific | Neo4j storage | Curation rules + visible ontology + segmentation |
| Git-like research versioning | Yes | Git concepts | Commit/change-set model over research workspace |
| Provenance model | Yes | Pydantic/Postgres/graph | Grounded vs derived model; claim/evidence links |
| Mode toggle/shared context | Yes | Custom | Same workspace/state, different execution policies |
| Prompt/memory routing | Yes | Custom | Selective memory retrieval, token budgets, compaction |