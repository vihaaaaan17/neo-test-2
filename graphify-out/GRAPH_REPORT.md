# Graph Report - NeosisLM  (2026-09-29)

## Corpus Check
- 116 files · ~54,060 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1265 nodes · 3229 edges · 69 communities (65 shown, 3 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 264 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e677c3f0`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- repositories/block.py
- chat/service.py
- OpenNotebookGroundEngine
- ResearchRepository
- ResearchMetricsService
- .handle_quota_violation
- utils.py
- WorkingMemoryState
- Configuration
- EpisodicMemory
- state.py
- ScratchpadRepository
- chat/context.py
- main.py
- OpenNotebookClient
- ChatEvent
- deep_researcher.py
- BaseRetriever
- OpenDeepResearchEngine
- derivation.py
- get_all_tools
- ConversationRepository
- database.py
- ResearchRun
- promotions.py
- ResearchModeOrchestrator
- ValueError
- routes/chat.py
- ResearchLifecycleService
- GraphStore
- ResearchNormalizationService
- Source
- WorkspaceRepository
- QuotaService
- FastAPI
- GroundModeOrchestrator
- is_token_limit_exceeded
- create_research_run
- ask_ground_mode
- workspaces.py
- telemetry.py
- settings.py
- ProvenanceRef
- UsageTracker
- research/service.py
- get_quota_status
- get_notes_from_tool_calls
- core/config.py
- integrations/__init__.py
- ChatService
- upload_file_to_workspace
- Request
- stream_job_events
- CircuitBreaker
- .__init__
- GPTResearcherRetriever
- research/budget.py
- MemoryRouterService
- ResearchSourceResult
- TurnCreate
- Any
- ObjectStoreProtocol
- streamlit_app.py
- tasks.py
- ResearchEvidence
- .retrieve
- rate_limit.py
- schemas/source.py

## God Nodes (most connected - your core abstractions)
1. `ResearchRepository` - 72 edges
2. `WorkspaceRepository` - 49 edges
3. `ConversationRepository` - 42 edges
4. `ChatService` - 42 edges
5. `ResearchRun` - 36 edges
6. `ConversationTurn` - 30 edges
7. `OpenNotebookClient` - 29 edges
8. `ResearchArtifact` - 29 edges
9. `Source` - 26 edges
10. `Workspace` - 26 edges

## Surprising Connections (you probably didn't know these)
- `run_ground_mode()` --uses--> `GroundModeOrchestrator`  [INFERRED]
  streamlit_app.py → app/orchestration/ground_mode.py
- `run_agent()` --uses--> `ResearchContext`  [INFERRED]
  streamlit_app.py → app/orchestration/research_mode.py
- `run_agent()` --uses--> `ResearchModeOrchestrator`  [INFERRED]
  streamlit_app.py → app/orchestration/research_mode.py
- `create_db_workspace()` --calls--> `WorkspaceRepository`  [EXTRACTED]
  streamlit_app.py → app/repositories/workspace.py
- `run_ground_mode()` --uses--> `HybridRetrievalService`  [INFERRED]
  streamlit_app.py → app/services/hybrid_retrieval.py

## Import Cycles
- None detected.

## Communities (69 total, 3 thin omitted)

### Community 0 - "repositories/block.py"
Cohesion: 0.25
Nodes (6): UUID, DocumentBlockCreate, DocumentBlockResponse, BaseModel, Any, Takes the raw dictionary output from Docling and converts it into…

### Community 1 - "chat/service.py"
Cohesion: 0.10
Nodes (19): BaseModel, ResearchRunResponse, Submits a turn and returns an async generator streaming its events via SSE.…, Any, UUID, Research Admission Controller to enforce quotas and rate limits before…, Admits a new research run after checking quotas and rate limits., Returns the current queue status. (+11 more)

### Community 2 - "OpenNotebookGroundEngine"
Cohesion: 0.12
Nodes (22): map_canonical_sources_to_upstream(), map_citations(), AsyncSession, UUID, Map upstream Open Notebook source IDs back to canonical Neosis source_ids.…, Map canonical Neosis source_ids (UUIDs) to upstream Open Notebook source IDs…, OpenNotebookGroundEngine, Any (+14 more)

### Community 3 - "ResearchRepository"
Cohesion: 0.18
Nodes (7): ResearchArtifact, UUID, Unified repository for all Research Fabric models. Enforces workspace_id…, Internal helper to ensure a given run_id belongs to the workspace_id. Raises an…, Persists usage metrics to the database as a periodic checkpoint., Records a usage entry for a research run., ResearchRepository

### Community 4 - "ResearchMetricsService"
Cohesion: 0.13
Nodes (15): get_workspace_metrics(), AsyncSession, get, UUID, Get observability metrics for a workspace., Any, datetime, UUID (+7 more)

### Community 5 - ".handle_quota_violation"
Cohesion: 0.17
Nodes (8): UUID, Enforces the user concurrency quota. Returns ACCEPTED or QUOTA_EXCEEDED., Enforces the workspace concurrency quota. Returns ACCEPTED or QUOTA_EXCEEDED., Enforces the global concurrency limit. Returns ACCEPTED or QUOTA_EXCEEDED., Handles quota violations by providing details about the current quotas. Returns…, Count active research runs for a given owner., Count active research runs for a given workspace., Count all active research runs globally.

### Community 6 - "utils.py"
Cohesion: 0.10
Nodes (29): fetch_tokens(), get_mcp_access_token(), get_tavily_api_key(), get_tokens(), load_mcp_tools(), Any, BaseTool, InjectedToolArg (+21 more)

### Community 7 - "WorkingMemoryState"
Cohesion: 0.20
Nodes (10): TypedDict, WorkingMemoryState, EpisodicMemoryService, UUID, llm_gateway: an async callable that takes a string prompt and returns a string…, Dispatch compression to the background queue., Call LLM with concurrency limits and retries., compress_episodic_job() (+2 more)

### Community 8 - "Configuration"
Cohesion: 0.15
Nodes (26): Config, Configuration, RunnableConfig, Create a Configuration instance from a RunnableConfig., Pydantic configuration., Main configuration class for the Deep Research agent., clarify_with_user(), compress_research() (+18 more)

### Community 9 - "EpisodicMemory"
Cohesion: 0.22
Nodes (9): EpisodicMemory, Base, EpisodicRepository, AsyncSession, UUID, Used by the background worker to detect duplicate compress_episodic_job calls., EpisodicMemoryCreate, EpisodicMemoryResponse (+1 more)

### Community 10 - "state.py"
Cohesion: 0.12
Nodes (21): AgentInputState, AgentState, ClarifyWithUser, ConductResearch, override_reducer(), BaseModel, Graph state definitions and data structures for the Deep Research agent., Call this tool to conduct research on a specific topic. (+13 more)

### Community 11 - "ScratchpadRepository"
Cohesion: 0.13
Nodes (26): create_scratchpad_entry(), get_scratchpad_entry(), list_scratchpad_entries(), AsyncSession, get, patch, post, UUID (+18 more)

### Community 12 - "chat/context.py"
Cohesion: 0.05
Nodes (53): KnowledgeMemory, Base, KnowledgeRepository, AsyncSession, UUID, KnowledgeMemoryCreate, KnowledgeMemoryResponse, Provenance (+45 more)

### Community 13 - "main.py"
Cohesion: 0.16
Nodes (15): CircuitState, Enum, get_open_notebook_base_url(), get_open_notebook_timeout(), is_open_notebook_enabled(), Get the default HTTP timeout for Open Notebook requests., Check if the Open Notebook Ground Engine is enabled., Get the base URL for the Open Notebook API. (+7 more)

### Community 14 - "OpenNotebookClient"
Cohesion: 0.14
Nodes (17): OpenNotebookClient, Any, Check health endpoint of Open Notebook. Returns the parsed JSON response.…, Streams the ask response, yielding standardized SSE events., Executes a chat message. Returns the final answer text and the updated…, Streams chat events and incremental tokens for a conversation session. Yields…, HTTP client for communicating with the Open Notebook API. Establishes the…, with_error_translation() (+9 more)

### Community 15 - "ChatEvent"
Cohesion: 0.11
Nodes (19): ChatEvent, GroundConversation, Base, Durable event record for real-time turn execution streaming and reconnect…, ChatEventRepository, ChatEventService, format_sse_event(), Any (+11 more)

### Community 16 - "deep_researcher.py"
Cohesion: 0.13
Nodes (17): execute_tool_safely(), Main LangGraph implementation for the Deep Research agent., Safely execute a tool with error handling., Execute tools called by the researcher, including search tools and strategic…, researcher_tools(), System prompts and prompt templates for the Deep Research agent., TypedDict, State for the supervisor that manages research tasks. (+9 more)

### Community 17 - "BaseRetriever"
Cohesion: 0.28
Nodes (8): ABC, BaseRetriever, ResearchRetrievalPolicy, Register a retriever instance under a name., List all registered retriever names., Central registry for managing and invoking retrievers (web, academic, mcp,…, RetrieverRegistry, WebRetriever

### Community 18 - "OpenDeepResearchEngine"
Cohesion: 0.05
Nodes (38): BudgetEnforcingCallbackHandler, Exception, Raised when an execution exceeds its allocated budget., Intercepts LLM results to track usage and enforce budgets., Track token usage after an LLM call completes., ResearchBudgetExceeded, Any, UUID (+30 more)

### Community 19 - "derivation.py"
Cohesion: 0.10
Nodes (23): DocumentBlock, Base, DerivationService, AsyncSession, Normalizes candidate outputs and enforces fail-closed multi-tenant provenance…, ArithmeticVerificationError, DeterministicArithmeticVerifier, _pct_change() (+15 more)

### Community 20 - "get_all_tools"
Cohesion: 0.14
Nodes (16): MCPConfig, BaseModel, Enum, Configuration management for the Open Deep Research system., Enumeration of available search API providers., Configuration for Model Context Protocol (MCP) servers., SearchAPI, get_all_tools() (+8 more)

### Community 21 - "ConversationRepository"
Cohesion: 0.14
Nodes (14): Conversation, ConversationTurn, Canonical conversational container within a Neosis workspace. Mode-agnostic:…, Canonical turn record representing a single prompt-response interaction within…, ConversationRepository, Any, AsyncSession, datetime (+6 more)

### Community 22 - "database.py"
Cohesion: 0.15
Nodes (15): get_embed_gateway(), get_llm_gateway(), mock_embed_call(), mock_llm_call(), get_hybrid_retrieval_service(), get_db(), get_ground_engine(), get_hybrid_retrieval_service() (+7 more)

### Community 23 - "ResearchRun"
Cohesion: 0.53
Nodes (6): Base, ResearchEvent, ResearchReport, ResearchRun, ResearchTask, ResearchUsage

### Community 24 - "promotions.py"
Cohesion: 0.07
Nodes (50): accept_promotion(), get_promotion(), _get_promotion_service(), list_promotions(), AsyncSession, get, post, Redis (+42 more)

### Community 25 - "ResearchModeOrchestrator"
Cohesion: 0.27
Nodes (7): BaseModel, deprecated, TypedDict, UUID, ResearchContext, ResearchModeOrchestrator, ResearchState

### Community 26 - "ValueError"
Cohesion: 0.15
Nodes (9): AsyncSession, UUID, WorkspaceExportService, S3ObjectStore, export_workspace_job(), Background job: Executes the workspace export using WorkspaceExportService and…, field_validator, model_validator (+1 more)

### Community 27 - "routes/chat.py"
Cohesion: 0.16
Nodes (30): cancel_turn(), create_conversation(), get_conversation(), get_conversation_repository(), get_turn(), get_workspace_repository(), list_conversations(), list_turn_events() (+22 more)

### Community 28 - "ResearchLifecycleService"
Cohesion: 0.21
Nodes (9): InvalidTransitionError, Any, datetime, Exception, UUID, Transition a ResearchTask to a new status. Emits a ResearchEvent., Acts as the sole authority for state transitions of ResearchRun and…, Transition a ResearchRun to a new status. Emits a ResearchEvent. (+1 more)

### Community 29 - "GraphStore"
Cohesion: 0.25
Nodes (3): GraphStore, Any, Abstract base class for our operational Knowledge Graph. This hides the…

### Community 30 - "ResearchNormalizationService"
Cohesion: 0.15
Nodes (12): GPTResearcherInput, BaseModel, neosis_web_search(), InjectedToolArg, RunnableConfig, tool, Fetch search results, immediately persist them to Neosis DB, and return…, Normalizes a URL by parsing it, lowercasing the scheme and netloc, and sorting… (+4 more)

### Community 31 - "Source"
Cohesion: 0.14
Nodes (13): Base, Source, SourceSnapshot, AsyncSession, UUID, SourceRepository, Any, AsyncSession (+5 more)

### Community 32 - "WorkspaceRepository"
Cohesion: 0.25
Nodes (7): Base, Workspace, WorkspaceCommit, AsyncSession, UUID, Atomically rolls back the workspace to a target commit under a row lock (FOR…, WorkspaceRepository

### Community 33 - "QuotaService"
Cohesion: 0.21
Nodes (8): get_quota_service(), AsyncSession, UUID, QuotaService, Check if user has exceeded their workspace limit., Check if workspace has exceeded its source count limit., Check if workspace has exceeded its total storage limit., Check if workspace has exceeded its knowledge memory limit.

### Community 34 - "FastAPI"
Cohesion: 0.21
Nodes (12): get_arq_redis(), Request, Dependency to get the arq Redis pool. We lazily initialize the pool and attach…, get_current_user(), UUID, get_rate_limit_status(), get, Redis (+4 more)

### Community 35 - "GroundModeOrchestrator"
Cohesion: 0.20
Nodes (8): GroundModeOrchestrator, GroundModeState, Any, deprecated, TypedDict, UUID, Deprecated: Use OpenNotebookGroundEngine instead. This orchestrator handles the…, MemoryItem

### Community 36 - "is_token_limit_exceeded"
Cohesion: 0.27
Nodes (10): _check_anthropic_token_limit(), _check_gemini_token_limit(), _check_openai_token_limit(), is_token_limit_exceeded(), McpError, Exception, Determine if an exception indicates a token/context limit was exceeded. Args:…, Check if exception indicates OpenAI token limit exceeded. (+2 more)

### Community 37 - "create_research_run"
Cohesion: 0.24
Nodes (11): create_research_run(), get_queue_status(), Any, AsyncSession, get, post, Redis, Response (+3 more)

### Community 38 - "ask_ground_mode"
Cohesion: 0.19
Nodes (11): get_chat_service(), ArqRedis, ask_ground_mode(), ask_ground_mode_stream(), AskRequest, AskResponse, BaseModel, GroundEngineProtocol (+3 more)

### Community 39 - "workspaces.py"
Cohesion: 0.13
Nodes (33): chat_ground_mode(), create_workspace(), create_workspace_commit(), get_knowledge_repository(), get_projection_status(), get_quota(), get_research_repository(), get_source_repository() (+25 more)

### Community 40 - "telemetry.py"
Cohesion: 0.28
Nodes (7): Sanitizes sensitive tokens, passwords, and API keys from log strings., Logging filter that intercepts log records and redacts any credentials, bearer…, Sets up OpenTelemetry and attaches secret sanitization to the logging root., sanitize_log_message(), SecretSanitizingFilter, setup_telemetry(), LogRecord

### Community 41 - "settings.py"
Cohesion: 0.13
Nodes (14): get_worker_pool_status(), Any, get, Get the current status of worker pools and queues., arq WorkerSettings — defines the worker process configuration. Run the worker…, Returns the configuration for a specific queue., Runs once when the worker process starts. Populate shared resources., Runs once when the worker process shuts down. (+6 more)

### Community 42 - "ProvenanceRef"
Cohesion: 0.31
Nodes (6): ProvenanceRef, Any, UUID, Validates provenance references, runs deterministic verification if derivations…, Builds a typed ProvenanceBundle from a list of ProvenanceRef items and optional…, Strictly validates that every reference in the provenance bundle exists and…

### Community 43 - "UsageTracker"
Cohesion: 0.20
Nodes (3): UsageTracker, MCPRetriever, Any

### Community 44 - "research/service.py"
Cohesion: 0.27
Nodes (12): GraphRepository, UUID, Projects an OutputGraph into Neo4j. Nodes get labels: OutputNode, plus their…, OutputGraph, OutputGraphEdge, OutputGraphNode, ProvenanceBundle, BaseModel (+4 more)

### Community 45 - "get_quota_status"
Cohesion: 0.33
Nodes (6): get_quota_status(), AsyncSession, get, Redis, UUID, Get the current quota status for the user and workspace.

### Community 46 - "get_notes_from_tool_calls"
Cohesion: 0.40
Nodes (5): get_notes_from_tool_calls(), Extract notes from tool call messages., Truncate message history by removing up to the last AI message. This is useful…, remove_up_to_last_ai_message(), MessageLikeRepresentation

### Community 47 - "core/config.py"
Cohesion: 0.18
Nodes (11): Settings, Validates infrastructure, checkpointer, and security invariants during…, validate_production_startup(), Shared HTTP client for Open Notebook integration., get_checkpointer(), process_memory(), Any, Validates checkpointer configuration on startup. In production, durable… (+3 more)

### Community 49 - "ChatService"
Cohesion: 0.11
Nodes (15): OpenNotebookConversationBinding, Dual in-process and Redis Pub/Sub event broker. Provides sub/pub abstraction…, TurnEventBroker, ChatService, UUID, Unified SSE generator — supports reconnect replay via Last-Event-ID. Protocol:…, Coordinates turn submission, mode dispatching (Ground vs Research),…, Executes Ground turn in background with independent DB session. Delegates… (+7 more)

### Community 50 - "upload_file_to_workspace"
Cohesion: 0.25
Nodes (8): delete_workspace(), get_memory_router(), ArqRedis, Request, upload_file_to_workspace(), delete, limit, UploadFile

### Community 52 - "Request"
Cohesion: 0.33
Nodes (5): limit_upload_size(), Request, set_neosis_run_id(), UploadSizeLimitMiddleware, BaseHTTPMiddleware

### Community 53 - "stream_job_events"
Cohesion: 0.40
Nodes (5): ArqRedis, get, Request, Streams Server-Sent Events (SSE) from the Redis Pub/Sub channel for a given job., stream_job_events()

### Community 56 - "GPTResearcherRetriever"
Cohesion: 0.18
Nodes (8): GPTResearcherTool, Any, BaseTool, RunnableConfig, Use the tool asynchronously., GPTResearcherRetriever, Any, Creates a mock LLM provider for GPTResearcher that uses Neosis's llm_gateway.…

### Community 57 - "research/budget.py"
Cohesion: 0.20
Nodes (6): Any, UUID, Research-specific budget policy to enforce cost and usage limits., Check if the budget for a research run has been exceeded. Returns True if the…, Returns the current budget status., ResearchBudgetPolicy

### Community 58 - "MemoryRouterService"
Cohesion: 0.22
Nodes (5): Any, ContextBundle, BaseModel, MemoryRouterService, Lightweight heuristic context builder for MemoryItem bundles. Preserved for…

### Community 59 - "ResearchSourceResult"
Cohesion: 0.29
Nodes (5): AcademicRetriever, Any, Execute retrieval for a given query and return normalized ResearchSourceResult…, ResearchSourceResult, Any

### Community 60 - "TurnCreate"
Cohesion: 0.32
Nodes (5): TurnCreate, Any, Executes a Ground mode turn against Open Notebook with 1-time transparent 409…, Admits research run, links to turn, enqueues ARQ job, and returns running turn…, Submits and executes a conversation turn synchronously (or 202 for research).…

### Community 61 - "Any"
Cohesion: 0.29
Nodes (4): Any, Returns the current user concurrency status., Returns the current workspace concurrency status., Returns the current global concurrency status.

### Community 62 - "ObjectStoreProtocol"
Cohesion: 0.15
Nodes (9): DocumentParser, Any, Downloads a document from Object Storage and parses it using docling. Returns a…, get_object_store(), ObjectStoreProtocol, Protocol, Request, UUID (+1 more)

### Community 63 - "streamlit_app.py"
Cohesion: 0.16
Nodes (9): Neo4jAdapter, Executes a search query and returns the results formatted as markdown., WebSearchTool, AsyncDriver, create_db_workspace(), get_litellm_gateway(), project_graph_to_neo4j(), run_agent() (+1 more)

### Community 64 - "tasks.py"
Cohesion: 0.19
Nodes (12): BlockRepository, AsyncSession, Validates and sanitizes structured scratchpad content. Strictly prohibits raw…, sanitize_scratchpad_content(), ChunkingService, _get_source_and_snapshot(), parse_and_chunk_job(), AsyncSession (+4 more)

### Community 65 - "ResearchEvidence"
Cohesion: 0.36
Nodes (5): ResearchEvidence, Any, Creates multiple evidence records in batches with fingerprint deduplication., Retrieves evidence records by their fingerprints., Performs a bulk insert of evidence records.

### Community 66 - ".retrieve"
Cohesion: 0.40
Nodes (3): Any, Get a registered retriever by name., Execute retrieval using the specified retriever or policy defaults, enforcing…

### Community 67 - "rate_limit.py"
Cohesion: 0.50
Nodes (3): get_rate_limit_key(), Request, Rate limit by user ID if authenticated, else fallback to IP.

### Community 68 - "schemas/source.py"
Cohesion: 0.67
Nodes (3): BaseModel, SourceResponse, SourceSnapshotResponse

## Knowledge Gaps
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ResearchRepository` connect `ResearchRepository` to `chat/service.py`, `ResearchMetricsService`, `chat/context.py`, `ChatEvent`, `OpenDeepResearchEngine`, `derivation.py`, `ResearchRun`, `promotions.py`, `ResearchLifecycleService`, `ResearchNormalizationService`, `WorkspaceRepository`, `FastAPI`, `create_research_run`, `workspaces.py`, `research/service.py`, `get_quota_status`, `.__init__`, `GPTResearcherRetriever`, `research/budget.py`, `tasks.py`, `ResearchEvidence`?**
  _High betweenness centrality (0.209) - this node is a cross-community bridge._
- **Why does `neosis_web_search()` connect `ResearchNormalizationService` to `ResearchRepository`, `get_all_tools`, `utils.py`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Why does `ConversationRepository` connect `ConversationRepository` to `tasks.py`, `chat/service.py`, `create_research_run`, `ask_ground_mode`, `workspaces.py`, `ScratchpadRepository`, `ChatEvent`, `ChatService`, `derivation.py`, `routes/chat.py`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `ResearchRepository` (e.g. with `ResearchArtifact` and `ResearchEvent`) actually correct?**
  _`ResearchRepository` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `WorkspaceRepository` (e.g. with `DeletionTombstone` and `OpenNotebookWorkspaceBinding`) actually correct?**
  _`WorkspaceRepository` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `ConversationRepository` (e.g. with `ChatEvent` and `Conversation`) actually correct?**
  _`ConversationRepository` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `ChatService` (e.g. with `cancel_turn()` and `get_turn()`) actually correct?**
  _`ChatService` has 22 INFERRED edges - model-reasoned connections that need verification._