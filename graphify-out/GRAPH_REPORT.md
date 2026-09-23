# Graph Report - NeosisLM  (2026-09-23)

## Corpus Check
- 96 files · ~33,790 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 902 nodes · 2083 edges · 53 communities (48 shown, 4 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 156 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `38e13284`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- streamlit_app.py
- Source
- models/__init__.py
- ResearchRepository
- tasks.py
- ResearchQuotaService
- utils.py
- WorkingMemoryState
- Configuration
- ground/factory.py
- state.py
- workspaces.py
- client.py
- service.py
- ProviderRateLimiter
- OpenNotebookClient
- deep_researcher.py
- ResearchSourceResult
- ResearchEngine
- ResearchNormalizationService
- get_all_tools
- DocumentBlock
- EpisodicMemory
- ResearchMetricsService
- settings.py
- repositories/research.py
- WorkerSettings
- create_research_run
- FastAPI
- WorkspaceRepository
- start_research
- main.py
- UsageTracker
- export.py
- ResearchLifecycleService
- RetrieverRegistry
- is_token_limit_exceeded
- ResearchBudgetPolicy
- GPTResearcherTool
- get_quota_status
- GPTResearcherRetriever
- stream_job_events
- CircuitBreaker
- AcademicRetriever
- rate_limit.py
- schemas/source.py
- get_notes_from_tool_calls
- .__init__
- integrations/__init__.py
- database.py
- UUID
- core/config.py

## God Nodes (most connected - your core abstractions)
1. `ResearchRepository` - 60 edges
2. `WorkspaceRepository` - 30 edges
3. `OpenNotebookClient` - 26 edges
4. `ResearchQuotaService` - 23 edges
5. `UsageTracker` - 21 edges
6. `ResearchRun` - 21 edges
7. `Source` - 20 edges
8. `ResearchNormalizationService` - 20 edges
9. `ResearchModeOrchestrator` - 19 edges
10. `QuotaService` - 19 edges

## Surprising Connections (you probably didn't know these)
- `create_db_workspace()` --calls--> `WorkspaceRepository`  [EXTRACTED]
  streamlit_app.py → app/repositories/workspace.py
- `run_ground_mode()` --uses--> `HybridRetrievalService`  [INFERRED]
  streamlit_app.py → app/services/hybrid_retrieval.py
- `run_ground_mode()` --uses--> `GroundModeOrchestrator`  [INFERRED]
  streamlit_app.py → app/orchestration/ground_mode.py
- `run_agent()` --uses--> `ResearchContext`  [INFERRED]
  streamlit_app.py → app/orchestration/research_mode.py
- `run_agent()` --uses--> `ResearchModeOrchestrator`  [INFERRED]
  streamlit_app.py → app/orchestration/research_mode.py

## Import Cycles
- None detected.

## Communities (53 total, 4 thin omitted)

### Community 0 - "streamlit_app.py"
Cohesion: 0.05
Nodes (31): GroundModeOrchestrator, GroundModeState, Any, deprecated, TypedDict, UUID, Deprecated: Use OpenNotebookGroundEngine instead. This orchestrator handles the…, Any (+23 more)

### Community 1 - "Source"
Cohesion: 0.06
Nodes (34): KnowledgeMemory, Base, Base, Source, SourceSnapshot, KnowledgeRepository, AsyncSession, UUID (+26 more)

### Community 2 - "models/__init__.py"
Cohesion: 0.13
Nodes (19): map_citations(), AsyncSession, UUID, Map upstream Open Notebook source IDs back to canonical Neosis source_ids.…, OpenNotebookGroundEngine, AsyncSession, UUID, Facade for interacting with Open Notebook's retrieval and asking APIs. (+11 more)

### Community 3 - "ResearchRepository"
Cohesion: 0.16
Nodes (12): ResearchEvidence, ResearchUsage, Any, UUID, Retrieves evidence records by their fingerprints., Performs a bulk insert of evidence records., Unified repository for all Research Fabric models. Enforces workspace_id…, Persists usage metrics to the database as a periodic checkpoint. (+4 more)

### Community 4 - "tasks.py"
Cohesion: 0.11
Nodes (17): ChunkingService, DocumentParser, Any, Downloads a document from Object Storage and parses it using docling. Returns a…, get_object_store(), ObjectStoreProtocol, Protocol, Request (+9 more)

### Community 5 - "ResearchQuotaService"
Cohesion: 0.12
Nodes (14): Any, UUID, Service to manage research quotas for users, workspaces, and globally., Returns the current user concurrency status., Returns the current workspace concurrency status., Returns the current global concurrency status., Enforces the user concurrency quota. Returns ACCEPTED or QUOTA_EXCEEDED., Enforces the workspace concurrency quota. Returns ACCEPTED or QUOTA_EXCEEDED. (+6 more)

### Community 6 - "utils.py"
Cohesion: 0.10
Nodes (29): fetch_tokens(), get_mcp_access_token(), get_tavily_api_key(), get_tokens(), load_mcp_tools(), Any, BaseTool, InjectedToolArg (+21 more)

### Community 7 - "WorkingMemoryState"
Cohesion: 0.22
Nodes (10): TypedDict, WorkingMemoryState, EpisodicMemoryService, UUID, Dispatch compression to the background queue., Call LLM with concurrency limits and retries., process_memory(), compress_episodic_job() (+2 more)

### Community 8 - "Configuration"
Cohesion: 0.15
Nodes (26): Config, Configuration, RunnableConfig, Create a Configuration instance from a RunnableConfig., Pydantic configuration., Main configuration class for the Deep Research agent., clarify_with_user(), compress_research() (+18 more)

### Community 9 - "ground/factory.py"
Cohesion: 0.12
Nodes (18): get_embed_gateway(), get_llm_gateway(), mock_embed_call(), mock_llm_call(), get_hybrid_retrieval_service(), get_ground_engine(), get_hybrid_retrieval_service(), GroundEngineProtocol (+10 more)

### Community 10 - "state.py"
Cohesion: 0.12
Nodes (21): AgentInputState, AgentState, ClarifyWithUser, ConductResearch, override_reducer(), BaseModel, Graph state definitions and data structures for the Deep Research agent., Call this tool to conduct research on a specific topic. (+13 more)

### Community 11 - "workspaces.py"
Cohesion: 0.16
Nodes (19): ask_ground_mode(), ask_ground_mode_stream(), chat_ground_mode(), get_knowledge_repository(), get_quota(), get_research_repository(), get_source_repository(), get_workspace_repository() (+11 more)

### Community 12 - "client.py"
Cohesion: 0.18
Nodes (12): CircuitState, Enum, get_open_notebook_base_url(), get_open_notebook_timeout(), is_open_notebook_enabled(), Get the default HTTP timeout for Open Notebook requests., Check if the Open Notebook Ground Engine is enabled., Get the base URL for the Open Notebook API. (+4 more)

### Community 13 - "service.py"
Cohesion: 0.23
Nodes (15): GraphRepository, UUID, Projects an OutputGraph into Neo4j. Nodes get labels: OutputNode, plus their…, OutputGraph, OutputGraphEdge, OutputGraphNode, ProvenanceBundle, BaseModel (+7 more)

### Community 14 - "ProviderRateLimiter"
Cohesion: 0.11
Nodes (14): Any, UUID, Research Admission Controller to enforce quotas and rate limits before…, Admits a new research run after checking quotas and rate limits., Returns the current queue status., ResearchAdmissionController, ProviderRateLimiter, Any (+6 more)

### Community 15 - "OpenNotebookClient"
Cohesion: 0.28
Nodes (7): OpenNotebookClient, Any, Check health endpoint of Open Notebook. Returns the parsed JSON response.…, Streams the ask response, yielding standardized SSE events., Executes a chat message. Returns the final answer text and the updated…, HTTP client for communicating with the Open Notebook API. Establishes the…, with_error_translation()

### Community 16 - "deep_researcher.py"
Cohesion: 0.13
Nodes (17): execute_tool_safely(), Main LangGraph implementation for the Deep Research agent., Safely execute a tool with error handling., Execute tools called by the researcher, including search tools and strategic…, researcher_tools(), System prompts and prompt templates for the Deep Research agent., TypedDict, State for the supervisor that manages research tasks. (+9 more)

### Community 17 - "ResearchSourceResult"
Cohesion: 0.32
Nodes (7): ABC, BaseRetriever, Execute retrieval for a given query and return normalized ResearchSourceResult…, ResearchRetrievalPolicy, ResearchSourceResult, MCPRetriever, Any

### Community 18 - "ResearchEngine"
Cohesion: 0.06
Nodes (37): BudgetEnforcingCallbackHandler, Exception, Raised when an execution exceeds its allocated budget., Intercepts LLM results to track usage and enforce budgets., Track token usage after an LLM call completes., ResearchBudgetExceeded, Any, UUID (+29 more)

### Community 19 - "ResearchNormalizationService"
Cohesion: 0.15
Nodes (12): GPTResearcherInput, BaseModel, neosis_web_search(), InjectedToolArg, RunnableConfig, tool, Fetch search results, immediately persist them to Neosis DB, and return…, Normalizes a URL by parsing it, lowercasing the scheme and netloc, and sorting… (+4 more)

### Community 20 - "get_all_tools"
Cohesion: 0.14
Nodes (16): MCPConfig, BaseModel, Enum, Configuration management for the Open Deep Research system., Enumeration of available search API providers., Configuration for Model Context Protocol (MCP) servers., SearchAPI, get_all_tools() (+8 more)

### Community 21 - "DocumentBlock"
Cohesion: 0.18
Nodes (10): DocumentBlock, Base, BlockRepository, AsyncSession, UUID, DocumentBlockCreate, DocumentBlockResponse, BaseModel (+2 more)

### Community 22 - "EpisodicMemory"
Cohesion: 0.18
Nodes (10): EpisodicMemory, Base, EpisodicRepository, AsyncSession, UUID, Used by the background worker to detect duplicate compress_episodic_job calls., EpisodicMemoryCreate, EpisodicMemoryResponse (+2 more)

### Community 23 - "ResearchMetricsService"
Cohesion: 0.18
Nodes (10): Any, datetime, UUID, Service to emit structured metrics for research observability. Tracks wait…, Emits structured metrics for a research run., Tracks the time-to-first-event (TTFE) for a research run., Tracks the cost of a research run., Tracks failures for a research run. (+2 more)

### Community 24 - "settings.py"
Cohesion: 0.15
Nodes (16): arq WorkerSettings — defines the worker process configuration. Run the worker…, Runs once when the worker process starts. Populate shared resources., Runs once when the worker process shuts down., shutdown(), startup(), process_deletion_tombstone_job(), project_output_graph_job(), project_to_open_notebook_job() (+8 more)

### Community 25 - "repositories/research.py"
Cohesion: 0.50
Nodes (6): Base, ResearchArtifact, ResearchEvent, ResearchReport, ResearchRun, ResearchTask

### Community 26 - "WorkerSettings"
Cohesion: 0.22
Nodes (8): get_worker_pool_status(), Any, get, Get the current status of worker pools and queues., Returns the configuration for a specific queue., arq worker settings class. Discovered by: python -m arq…, WorkerSettings, BaseWorkerSettings

### Community 27 - "create_research_run"
Cohesion: 0.23
Nodes (12): create_research_run(), enqueue_research_job(), get_queue_status(), Any, AsyncSession, get, post, Redis (+4 more)

### Community 28 - "FastAPI"
Cohesion: 0.23
Nodes (9): get_arq_redis(), Request, Dependency to get the arq Redis pool. We lazily initialize the pool and attach…, get_rate_limit_status(), get, Redis, UUID, Get the current rate limit status for the user. (+1 more)

### Community 29 - "WorkspaceRepository"
Cohesion: 0.23
Nodes (9): update_workspace(), Base, Workspace, WorkspaceCommit, AsyncSession, UUID, WorkspaceRepository, WorkspaceUpdate (+1 more)

### Community 30 - "start_research"
Cohesion: 0.26
Nodes (11): create_workspace(), create_workspace_commit(), post, rollback_workspace(), start_research(), BaseModel, ResearchRequest, RollbackRequest (+3 more)

### Community 31 - "main.py"
Cohesion: 0.21
Nodes (9): setup_telemetry(), health_check(), limit_upload_size(), get, Request, Deep health check verifying Postgres and Neo4j connectivity., set_neosis_run_id(), UploadSizeLimitMiddleware (+1 more)

### Community 32 - "UsageTracker"
Cohesion: 0.23
Nodes (3): UsageTracker, Any, WebRetriever

### Community 33 - "export.py"
Cohesion: 0.23
Nodes (6): AsyncSession, UUID, WorkspaceExportService, S3ObjectStore, export_workspace_job(), Background job: Executes the workspace export using WorkspaceExportService and…

### Community 34 - "ResearchLifecycleService"
Cohesion: 0.21
Nodes (9): InvalidTransitionError, Any, datetime, Exception, UUID, Transition a ResearchTask to a new status. Emits a ResearchEvent., Acts as the sole authority for state transitions of ResearchRun and…, Transition a ResearchRun to a new status. Emits a ResearchEvent. (+1 more)

### Community 35 - "RetrieverRegistry"
Cohesion: 0.18
Nodes (7): Any, Register a retriever instance under a name., Get a registered retriever by name., List all registered retriever names., Execute retrieval using the specified retriever or policy defaults, enforcing…, Central registry for managing and invoking retrievers (web, academic, mcp,…, RetrieverRegistry

### Community 36 - "is_token_limit_exceeded"
Cohesion: 0.27
Nodes (10): _check_anthropic_token_limit(), _check_gemini_token_limit(), _check_openai_token_limit(), is_token_limit_exceeded(), McpError, Exception, Determine if an exception indicates a token/context limit was exceeded. Args:…, Check if exception indicates OpenAI token limit exceeded. (+2 more)

### Community 37 - "ResearchBudgetPolicy"
Cohesion: 0.22
Nodes (6): Any, UUID, Research-specific budget policy to enforce cost and usage limits., Check if the budget for a research run has been exceeded. Returns True if the…, Returns the current budget status., ResearchBudgetPolicy

### Community 38 - "GPTResearcherTool"
Cohesion: 0.29
Nodes (5): GPTResearcherTool, Any, BaseTool, RunnableConfig, Use the tool asynchronously.

### Community 39 - "get_quota_status"
Cohesion: 0.33
Nodes (6): get_quota_status(), AsyncSession, get, Redis, UUID, Get the current quota status for the user and workspace.

### Community 40 - "GPTResearcherRetriever"
Cohesion: 0.47
Nodes (3): GPTResearcherRetriever, Any, Creates a mock LLM provider for GPTResearcher that uses Neosis's llm_gateway.…

### Community 41 - "stream_job_events"
Cohesion: 0.40
Nodes (5): ArqRedis, get, Request, Streams Server-Sent Events (SSE) from the Redis Pub/Sub channel for a given job., stream_job_events()

### Community 44 - "rate_limit.py"
Cohesion: 0.50
Nodes (3): get_rate_limit_key(), Request, Rate limit by user ID if authenticated, else fallback to IP.

### Community 45 - "schemas/source.py"
Cohesion: 0.67
Nodes (3): BaseModel, SourceResponse, SourceSnapshotResponse

### Community 46 - "get_notes_from_tool_calls"
Cohesion: 0.40
Nodes (5): get_notes_from_tool_calls(), Extract notes from tool call messages., Truncate message history by removing up to the last AI message. This is useful…, remove_up_to_last_ai_message(), MessageLikeRepresentation

### Community 49 - "database.py"
Cohesion: 0.24
Nodes (9): get_current_user(), UUID, get_workspace_metrics(), AsyncSession, get, UUID, Get observability metrics for a workspace., get_db() (+1 more)

### Community 50 - "UUID"
Cohesion: 0.19
Nodes (13): delete_workspace(), get_memory_router(), get_projection_status(), get_source_status(), get_workspace(), ArqRedis, get, Request (+5 more)

### Community 55 - "core/config.py"
Cohesion: 0.40
Nodes (3): Settings, Shared HTTP client for Open Notebook integration., BaseSettings

## Knowledge Gaps
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ResearchRepository` connect `ResearchRepository` to `ResearchLifecycleService`, `tasks.py`, `ResearchBudgetPolicy`, `GPTResearcherTool`, `get_quota_status`, `ResearchQuotaService`, `workspaces.py`, `service.py`, `ProviderRateLimiter`, `.__init__`, `database.py`, `ResearchEngine`, `ResearchNormalizationService`, `ResearchSourceResult`, `ResearchMetricsService`, `repositories/research.py`, `create_research_run`, `start_research`?**
  _High betweenness centrality (0.369) - this node is a cross-community bridge._
- **Why does `neosis_web_search()` connect `ResearchNormalizationService` to `ResearchRepository`, `get_all_tools`, `utils.py`?**
  _High betweenness centrality (0.202) - this node is a cross-community bridge._
- **Why does `OpenNotebookClient` connect `OpenNotebookClient` to `models/__init__.py`, `tasks.py`, `workspaces.py`, `client.py`, `settings.py`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `ResearchRepository` (e.g. with `ResearchArtifact` and `ResearchEvent`) actually correct?**
  _`ResearchRepository` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `WorkspaceRepository` (e.g. with `DeletionTombstone` and `OpenNotebookWorkspaceBinding`) actually correct?**
  _`WorkspaceRepository` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `OpenNotebookClient` (e.g. with `chat_ground_mode()` and `OpenNotebookGroundEngine`) actually correct?**
  _`OpenNotebookClient` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `UsageTracker` (e.g. with `OpenDeepResearchEngine` and `AcademicRetriever`) actually correct?**
  _`UsageTracker` has 9 INFERRED edges - model-reasoned connections that need verification._