# Graph Report - NeosisLM  (2026-09-24)

## Corpus Check
- 101 files · ~36,604 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 977 nodes · 2338 edges · 61 communities (55 shown, 5 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 176 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `061519f9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- streamlit_app.py
- Source
- OpenNotebookWorkspaceBinding
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
- research/service.py
- create_research_run
- OpenNotebookClient
- deep_researcher.py
- BaseRetriever
- ResearchEngine
- ResearchNormalizationService
- get_all_tools
- ConversationRepository
- EpisodicMemory
- ResearchMetricsService
- settings.py
- repositories/research.py
- chat/service.py
- routes/chat.py
- FastAPI
- WorkspaceRepository
- start_research
- main.py
- UsageTracker
- KnowledgeMemory
- ResearchLifecycleService
- .retrieve
- is_token_limit_exceeded
- research/budget.py
- GPTResearcherRetriever
- database.py
- GroundModeOrchestrator
- DocumentBlock
- Neo4jAdapter
- ResearchSourceResult
- ResearchProvenanceService
- schemas/source.py
- get_notes_from_tool_calls
- .__init__
- integrations/__init__.py
- export.py
- upload_file_to_workspace
- ResearchEvidence
- .check_rate_limit_status
- get_chat_service
- core/config.py
- get_workspace_metrics
- CircuitBreaker
- health_check
- .get_queue_status
- .__init__

## God Nodes (most connected - your core abstractions)
1. `ResearchRepository` - 62 edges
2. `WorkspaceRepository` - 40 edges
3. `OpenNotebookClient` - 29 edges
4. `ConversationRepository` - 26 edges
5. `ResearchQuotaService` - 25 edges
6. `ChatService` - 24 edges
7. `ResearchRun` - 22 edges
8. `UsageTracker` - 21 edges
9. `Source` - 20 edges
10. `ResearchNormalizationService` - 20 edges

## Surprising Connections (you probably didn't know these)
- `run_ground_mode()` --uses--> `GroundModeOrchestrator`  [INFERRED]
  streamlit_app.py → app/orchestration/ground_mode.py
- `create_db_workspace()` --calls--> `WorkspaceRepository`  [EXTRACTED]
  streamlit_app.py → app/repositories/workspace.py
- `run_ground_mode()` --uses--> `HybridRetrievalService`  [INFERRED]
  streamlit_app.py → app/services/hybrid_retrieval.py
- `run_agent()` --uses--> `ResearchContext`  [INFERRED]
  streamlit_app.py → app/orchestration/research_mode.py
- `run_agent()` --uses--> `ResearchModeOrchestrator`  [INFERRED]
  streamlit_app.py → app/orchestration/research_mode.py

## Import Cycles
- None detected.

## Communities (61 total, 5 thin omitted)

### Community 0 - "streamlit_app.py"
Cohesion: 0.13
Nodes (15): Any, BaseModel, deprecated, TypedDict, UUID, ResearchContext, ResearchModeOrchestrator, ResearchState (+7 more)

### Community 1 - "Source"
Cohesion: 0.15
Nodes (14): Base, Source, SourceSnapshot, AsyncSession, UUID, SourceRepository, get_quota_service(), AsyncSession (+6 more)

### Community 2 - "OpenNotebookWorkspaceBinding"
Cohesion: 0.16
Nodes (14): map_citations(), AsyncSession, UUID, Map upstream Open Notebook source IDs back to canonical Neosis source_ids.…, DeletionTombstone, OpenNotebookSourceBinding, OpenNotebookWorkspaceBinding, Base (+6 more)

### Community 3 - "ResearchRepository"
Cohesion: 0.20
Nodes (7): ResearchUsage, UUID, Unified repository for all Research Fabric models. Enforces workspace_id…, Persists usage metrics to the database as a periodic checkpoint., Records a usage entry for a research run., Internal helper to ensure a given run_id belongs to the workspace_id. Raises an…, ResearchRepository

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
Cohesion: 0.18
Nodes (11): TypedDict, WorkingMemoryState, EpisodicMemoryService, UUID, llm_gateway: an async callable that takes a string prompt and returns a string…, Dispatch compression to the background queue., Call LLM with concurrency limits and retries., process_memory() (+3 more)

### Community 8 - "Configuration"
Cohesion: 0.15
Nodes (26): Config, Configuration, RunnableConfig, Create a Configuration instance from a RunnableConfig., Pydantic configuration., Main configuration class for the Deep Research agent., clarify_with_user(), compress_research() (+18 more)

### Community 9 - "ground/factory.py"
Cohesion: 0.13
Nodes (16): get_embed_gateway(), get_llm_gateway(), mock_embed_call(), mock_llm_call(), get_hybrid_retrieval_service(), get_ground_engine(), get_hybrid_retrieval_service(), Any (+8 more)

### Community 10 - "state.py"
Cohesion: 0.12
Nodes (21): AgentInputState, AgentState, ClarifyWithUser, ConductResearch, override_reducer(), BaseModel, Graph state definitions and data structures for the Deep Research agent., Call this tool to conduct research on a specific topic. (+13 more)

### Community 11 - "workspaces.py"
Cohesion: 0.15
Nodes (26): ask_ground_mode(), ask_ground_mode_stream(), chat_ground_mode(), create_workspace_commit(), get_knowledge_repository(), get_projection_status(), get_quota(), get_research_repository() (+18 more)

### Community 12 - "client.py"
Cohesion: 0.18
Nodes (12): CircuitState, Enum, get_open_notebook_base_url(), get_open_notebook_timeout(), is_open_notebook_enabled(), Get the default HTTP timeout for Open Notebook requests., Check if the Open Notebook Ground Engine is enabled., Get the base URL for the Open Notebook API. (+4 more)

### Community 13 - "research/service.py"
Cohesion: 0.20
Nodes (17): GraphRepository, UUID, Projects an OutputGraph into Neo4j. Nodes get labels: OutputNode, plus their…, OutputGraph, OutputGraphEdge, OutputGraphNode, ProvenanceBundle, BaseModel (+9 more)

### Community 14 - "create_research_run"
Cohesion: 0.23
Nodes (12): create_research_run(), enqueue_research_job(), get_queue_status(), Any, AsyncSession, get, post, Redis (+4 more)

### Community 15 - "OpenNotebookClient"
Cohesion: 0.21
Nodes (9): OpenNotebookClient, Any, Check health endpoint of Open Notebook. Returns the parsed JSON response.…, Streams the ask response, yielding standardized SSE events., Executes a chat message. Returns the final answer text and the updated…, HTTP client for communicating with the Open Notebook API. Establishes the…, with_error_translation(), AsyncSession (+1 more)

### Community 16 - "deep_researcher.py"
Cohesion: 0.13
Nodes (17): execute_tool_safely(), Main LangGraph implementation for the Deep Research agent., Safely execute a tool with error handling., Execute tools called by the researcher, including search tools and strategic…, researcher_tools(), System prompts and prompt templates for the Deep Research agent., TypedDict, State for the supervisor that manages research tasks. (+9 more)

### Community 17 - "BaseRetriever"
Cohesion: 0.28
Nodes (8): ABC, BaseRetriever, ResearchRetrievalPolicy, Register a retriever instance under a name., List all registered retriever names., Central registry for managing and invoking retrievers (web, academic, mcp,…, RetrieverRegistry, WebRetriever

### Community 18 - "ResearchEngine"
Cohesion: 0.06
Nodes (37): BudgetEnforcingCallbackHandler, Exception, Raised when an execution exceeds its allocated budget., Intercepts LLM results to track usage and enforce budgets., Track token usage after an LLM call completes., ResearchBudgetExceeded, Any, UUID (+29 more)

### Community 19 - "ResearchNormalizationService"
Cohesion: 0.15
Nodes (12): GPTResearcherInput, BaseModel, neosis_web_search(), InjectedToolArg, RunnableConfig, tool, Fetch search results, immediately persist them to Neosis DB, and return…, Normalizes a URL by parsing it, lowercasing the scheme and netloc, and sorting… (+4 more)

### Community 20 - "get_all_tools"
Cohesion: 0.14
Nodes (16): MCPConfig, BaseModel, Enum, Configuration management for the Open Deep Research system., Enumeration of available search API providers., Configuration for Model Context Protocol (MCP) servers., SearchAPI, get_all_tools() (+8 more)

### Community 21 - "ConversationRepository"
Cohesion: 0.18
Nodes (13): ChatEvent, Conversation, ConversationTurn, GroundConversation, Base, Canonical conversational container within a Neosis workspace. Mode-agnostic:…, Canonical turn record representing a single prompt-response interaction within…, Durable event record for real-time turn execution streaming and reconnect… (+5 more)

### Community 22 - "EpisodicMemory"
Cohesion: 0.23
Nodes (9): EpisodicMemory, Base, EpisodicRepository, AsyncSession, UUID, Used by the background worker to detect duplicate compress_episodic_job calls., EpisodicMemoryCreate, EpisodicMemoryResponse (+1 more)

### Community 23 - "ResearchMetricsService"
Cohesion: 0.18
Nodes (10): Any, datetime, UUID, Service to emit structured metrics for research observability. Tracks wait…, Emits structured metrics for a research run., Tracks the time-to-first-event (TTFE) for a research run., Tracks the cost of a research run., Tracks failures for a research run. (+2 more)

### Community 24 - "settings.py"
Cohesion: 0.10
Nodes (21): get_worker_pool_status(), Any, get, Get the current status of worker pools and queues., arq WorkerSettings — defines the worker process configuration. Run the worker…, Returns the configuration for a specific queue., Runs once when the worker process starts. Populate shared resources., Runs once when the worker process shuts down. (+13 more)

### Community 25 - "repositories/research.py"
Cohesion: 0.37
Nodes (7): Base, ResearchArtifact, ResearchEvent, ResearchRun, ResearchTask, UUID, Admits a new research run after checking quotas and rate limits.

### Community 26 - "chat/service.py"
Cohesion: 0.11
Nodes (20): OpenNotebookGroundEngine, Facade for interacting with Open Notebook's retrieval and asking APIs., OpenNotebookConversationBinding, ChatService, Any, ArqRedis, AsyncSession, UUID (+12 more)

### Community 27 - "routes/chat.py"
Cohesion: 0.22
Nodes (22): create_conversation(), get_conversation(), get_turn(), list_conversations(), list_turns(), get, patch, post (+14 more)

### Community 28 - "FastAPI"
Cohesion: 0.15
Nodes (14): get_arq_redis(), Request, Dependency to get the arq Redis pool. We lazily initialize the pool and attach…, ArqRedis, get, Request, Streams Server-Sent Events (SSE) from the Redis Pub/Sub channel for a given job., stream_job_events() (+6 more)

### Community 29 - "WorkspaceRepository"
Cohesion: 0.23
Nodes (9): patch, update_workspace(), Base, Workspace, WorkspaceCommit, AsyncSession, UUID, WorkspaceRepository (+1 more)

### Community 30 - "start_research"
Cohesion: 0.29
Nodes (9): create_workspace(), rollback_workspace(), start_research(), BaseModel, ResearchRequest, RollbackRequest, WorkspaceCommitResponse, WorkspaceCreate (+1 more)

### Community 31 - "main.py"
Cohesion: 0.19
Nodes (9): get_rate_limit_key(), Request, Rate limit by user ID if authenticated, else fallback to IP., setup_telemetry(), limit_upload_size(), Request, set_neosis_run_id(), UploadSizeLimitMiddleware (+1 more)

### Community 32 - "UsageTracker"
Cohesion: 0.20
Nodes (3): UsageTracker, MCPRetriever, Any

### Community 33 - "KnowledgeMemory"
Cohesion: 0.16
Nodes (13): KnowledgeMemory, Base, KnowledgeRepository, AsyncSession, UUID, KnowledgeMemoryCreate, KnowledgeMemoryResponse, Provenance (+5 more)

### Community 34 - "ResearchLifecycleService"
Cohesion: 0.21
Nodes (9): InvalidTransitionError, Any, datetime, Exception, UUID, Transition a ResearchTask to a new status. Emits a ResearchEvent., Acts as the sole authority for state transitions of ResearchRun and…, Transition a ResearchRun to a new status. Emits a ResearchEvent. (+1 more)

### Community 35 - ".retrieve"
Cohesion: 0.40
Nodes (3): Any, Get a registered retriever by name., Execute retrieval using the specified retriever or policy defaults, enforcing…

### Community 36 - "is_token_limit_exceeded"
Cohesion: 0.27
Nodes (10): _check_anthropic_token_limit(), _check_gemini_token_limit(), _check_openai_token_limit(), is_token_limit_exceeded(), McpError, Exception, Determine if an exception indicates a token/context limit was exceeded. Args:…, Check if exception indicates OpenAI token limit exceeded. (+2 more)

### Community 37 - "research/budget.py"
Cohesion: 0.20
Nodes (6): Any, UUID, Research-specific budget policy to enforce cost and usage limits., Check if the budget for a research run has been exceeded. Returns True if the…, Returns the current budget status., ResearchBudgetPolicy

### Community 38 - "GPTResearcherRetriever"
Cohesion: 0.18
Nodes (8): GPTResearcherTool, Any, BaseTool, RunnableConfig, Use the tool asynchronously., GPTResearcherRetriever, Any, Creates a mock LLM provider for GPTResearcher that uses Neosis's llm_gateway.…

### Community 39 - "database.py"
Cohesion: 0.22
Nodes (10): get_current_user(), UUID, get_quota_status(), AsyncSession, get, Redis, UUID, Get the current quota status for the user and workspace. (+2 more)

### Community 40 - "GroundModeOrchestrator"
Cohesion: 0.15
Nodes (11): GroundModeOrchestrator, GroundModeState, Any, deprecated, TypedDict, UUID, Deprecated: Use OpenNotebookGroundEngine instead. This orchestrator handles the…, ContextBundle (+3 more)

### Community 41 - "DocumentBlock"
Cohesion: 0.18
Nodes (10): DocumentBlock, Base, BlockRepository, AsyncSession, UUID, DocumentBlockCreate, DocumentBlockResponse, BaseModel (+2 more)

### Community 42 - "Neo4jAdapter"
Cohesion: 0.17
Nodes (5): GraphStore, Neo4jAdapter, Any, Abstract base class for our operational Knowledge Graph. This hides the…, AsyncDriver

### Community 43 - "ResearchSourceResult"
Cohesion: 0.29
Nodes (5): AcademicRetriever, Any, Execute retrieval for a given query and return normalized ResearchSourceResult…, ResearchSourceResult, Any

### Community 44 - "ResearchProvenanceService"
Cohesion: 0.21
Nodes (8): ResearchReport, Any, AsyncSession, UUID, Attempts to resolve an external citation to an existing workspace Source.…, Audits the full provenance chain for a given report_id. Chain: Report ->…, Manages the mapping of external citations/evidence to canonical workspace…, ResearchProvenanceService

### Community 45 - "schemas/source.py"
Cohesion: 0.67
Nodes (3): BaseModel, SourceResponse, SourceSnapshotResponse

### Community 46 - "get_notes_from_tool_calls"
Cohesion: 0.40
Nodes (5): get_notes_from_tool_calls(), Extract notes from tool call messages., Truncate message history by removing up to the last AI message. This is useful…, remove_up_to_last_ai_message(), MessageLikeRepresentation

### Community 49 - "export.py"
Cohesion: 0.23
Nodes (6): AsyncSession, UUID, WorkspaceExportService, S3ObjectStore, export_workspace_job(), Background job: Executes the workspace export using WorkspaceExportService and…

### Community 50 - "upload_file_to_workspace"
Cohesion: 0.25
Nodes (8): delete_workspace(), get_memory_router(), ArqRedis, Request, upload_file_to_workspace(), delete, limit, UploadFile

### Community 52 - "ResearchEvidence"
Cohesion: 0.36
Nodes (5): ResearchEvidence, Any, Creates multiple evidence records in batches with fingerprint deduplication., Retrieves evidence records by their fingerprints., Performs a bulk insert of evidence records.

### Community 53 - ".check_rate_limit_status"
Cohesion: 0.25
Nodes (5): Any, UUID, Enforces rate limits for a given provider type and identifier. Returns True if…, Checks the current rate limit status for a given provider type and identifier.…, Returns the current rate limit configuration.

### Community 54 - "get_chat_service"
Cohesion: 0.40
Nodes (5): get_chat_service(), get_conversation_repository(), get_workspace_repository(), ArqRedis, AsyncSession

### Community 55 - "core/config.py"
Cohesion: 0.40
Nodes (3): Settings, Shared HTTP client for Open Notebook integration., BaseSettings

### Community 56 - "get_workspace_metrics"
Cohesion: 0.40
Nodes (5): get_workspace_metrics(), AsyncSession, get, UUID, Get observability metrics for a workspace.

### Community 58 - "health_check"
Cohesion: 0.67
Nodes (3): health_check(), get, Deep health check verifying Postgres and Neo4j connectivity.

## Knowledge Gaps
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ResearchRepository` connect `ResearchRepository` to `tasks.py`, `ResearchQuotaService`, `workspaces.py`, `research/service.py`, `create_research_run`, `ResearchEngine`, `ResearchNormalizationService`, `ResearchMetricsService`, `repositories/research.py`, `chat/service.py`, `start_research`, `ResearchLifecycleService`, `research/budget.py`, `GPTResearcherRetriever`, `database.py`, `ResearchProvenanceService`, `.__init__`, `ResearchEvidence`, `get_workspace_metrics`?**
  _High betweenness centrality (0.355) - this node is a cross-community bridge._
- **Why does `neosis_web_search()` connect `ResearchNormalizationService` to `ResearchRepository`, `get_all_tools`, `utils.py`?**
  _High betweenness centrality (0.192) - this node is a cross-community bridge._
- **Why does `OpenNotebookClient` connect `OpenNotebookClient` to `OpenNotebookWorkspaceBinding`, `tasks.py`, `workspaces.py`, `client.py`, `settings.py`, `chat/service.py`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `ResearchRepository` (e.g. with `ResearchArtifact` and `ResearchEvent`) actually correct?**
  _`ResearchRepository` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `WorkspaceRepository` (e.g. with `DeletionTombstone` and `OpenNotebookWorkspaceBinding`) actually correct?**
  _`WorkspaceRepository` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `OpenNotebookClient` (e.g. with `chat_ground_mode()` and `OpenNotebookGroundEngine`) actually correct?**
  _`OpenNotebookClient` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `ConversationRepository` (e.g. with `ChatEvent` and `Conversation`) actually correct?**
  _`ConversationRepository` has 3 INFERRED edges - model-reasoned connections that need verification._