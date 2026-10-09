# Graph Report - NeosisLM  (2026-10-07)

## Corpus Check
- 140 files · ~63,797 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1403 nodes · 3213 edges · 100 communities (62 shown, 23 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 198 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d582b854`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- S3ObjectStore
- ProviderRateLimiter
- WorkspaceRepository
- ResearchRepository
- promotions.py
- ResearchQuotaService
- utils.py
- EpisodicMemoryService
- .from_runnable_config
- .accept_candidate
- state.py
- ScratchpadRepository
- chat/context.py
- Request
- OpenNotebookClient
- chat/service.py
- deep_researcher.py
- ResearchSourceResult
- ResearchEngine
- derivation.py
- configuration.py
- ConversationRepository
- OpenNotebookGroundEngine
- research/service.py
- PromotionError
- ResearchModeOrchestrator
- ValueError
- routes/chat.py
- OpenDeepResearchEngine
- EpisodicMemory
- ResearchNormalizationService
- get_workspace_metrics
- WorkingMemoryState
- tasks.py
- worker.py
- ground/factory.py
- is_token_limit_exceeded
- GraphStore
- workspaces.py
- get_all_tools
- telemetry.py
- patch
- Source
- UsageTracker
- Enum
- PromotionService
- ResearchExecutionError
- _get_source_and_snapshot
- integrations/__init__.py
- ChatService
- get_chat_service
- run_live_test.py
- ResearchQuestion
- GPTResearcherRetriever
- ResearchBudgetPolicy
- SearchQuery
- AcademicRetriever
- SearchQuery
- SearchQuery
- ResearchQuestion
- NeosisAPIClient
- research/promotion.py
- RetrieverRegistry
- create_research_run
- get_quota_status
- tavily_search
- stream_job_events
- get_rate_limit_status
- .astream_events
- WebSearchTool
- rate_limit.py
- .astream_events
- .__init__
- .process_docling_output
- ResearchRunResponse
- .admit_research_run
- Settings
- open_notebook/__init__.py
- ArqRedis
- post
- BaseTool
- InjectedToolArg
- tool
- TypedDict
- Protocol

## God Nodes (most connected - your core abstractions)
1. `ResearchRepository` - 65 edges
2. `ChatService` - 41 edges
3. `ConversationRepository` - 40 edges
4. `NeosisAPIClient` - 36 edges
5. `WorkspaceRepository` - 31 edges
6. `ResearchRun` - 30 edges
7. `OpenNotebookClient` - 29 edges
8. `ConversationTurn` - 28 edges
9. `ResearchArtifact` - 25 edges
10. `ScratchpadRepository` - 24 edges

## Surprising Connections (you probably didn't know these)
- `get_workspace_output_graph()` --calls--> `GraphRepository`  [INFERRED]
  app/api/routes/workspaces.py → app/repositories/graph.py
- `upload_file_to_workspace()` --uses--> `ObjectStoreProtocol`  [INFERRED]
  app/api/routes/workspaces.py → app/services/storage.py
- `download_source_file()` --uses--> `ObjectStoreProtocol`  [INFERRED]
  app/api/routes/workspaces.py → app/services/storage.py
- `OpenNotebookGroundEngine` --uses--> `OpenNotebookClient`  [INFERRED]
  app/integrations/open_notebook/ground_engine.py → app/integrations/open_notebook/client.py
- `ChatService` --uses--> `OpenNotebookClient`  [INFERRED]
  app/services/chat/service.py → app/integrations/open_notebook/client.py

## Import Cycles
- None detected.

## Communities (100 total, 23 thin omitted)

### Community 0 - "S3ObjectStore"
Cohesion: 0.13
Nodes (10): DocumentParser, Any, Downloads a document from Object Storage and parses it using docling. Returns a…, get_object_store(), ObjectStoreProtocol, Request, UUID, Dependency to provide shared S3ObjectStore from app state. (+2 more)

### Community 1 - "ProviderRateLimiter"
Cohesion: 0.18
Nodes (8): ProviderRateLimiter, Any, Redis, UUID, Provider rate limiter to enforce rate limits on external providers. Uses Redis…, Enforces rate limits for a given provider type and identifier. Returns True if…, Checks the current rate limit status for a given provider type and identifier.…, Returns the current rate limit configuration.

### Community 2 - "WorkspaceRepository"
Cohesion: 0.08
Nodes (24): DeletionTombstone, OpenNotebookSourceBinding, OpenNotebookWorkspaceBinding, Base, Base, Workspace, WorkspaceCommit, OpenNotebookRepository (+16 more)

### Community 3 - "ResearchRepository"
Cohesion: 0.07
Nodes (39): Base, ResearchArtifact, ResearchEvent, ResearchEvidence, ResearchReport, ResearchRun, ResearchTask, ResearchUsage (+31 more)

### Community 4 - "promotions.py"
Cohesion: 0.27
Nodes (9): get_arq_redis(), Request, Dependency to get the arq Redis pool. We lazily initialize the pool and attach…, get_current_user(), UUID, get_db(), lifespan(), FastAPI (+1 more)

### Community 5 - "ResearchQuotaService"
Cohesion: 0.12
Nodes (14): Any, UUID, Service to manage research quotas for users, workspaces, and globally., Returns the current user concurrency status., Returns the current workspace concurrency status., Returns the current global concurrency status., Enforces the user concurrency quota. Returns ACCEPTED or QUOTA_EXCEEDED., Enforces the workspace concurrency quota. Returns ACCEPTED or QUOTA_EXCEEDED. (+6 more)

### Community 6 - "utils.py"
Cohesion: 0.13
Nodes (23): fetch_tokens(), get_mcp_access_token(), get_tavily_api_key(), get_tokens(), load_mcp_tools(), Any, RunnableConfig, Utility functions and helpers for the Deep Research agent. (+15 more)

### Community 7 - "EpisodicMemoryService"
Cohesion: 0.27
Nodes (6): EpisodicMemoryService, UUID, llm_gateway: an async callable that takes a string prompt and returns a string…, Dispatch compression to the background queue., Call LLM with concurrency limits and retries., retry

### Community 8 - ".from_runnable_config"
Cohesion: 0.15
Nodes (25): AgentState, RunnableConfig, Create a Configuration instance from a RunnableConfig., clarify_with_user(), compress_research(), final_report_generation(), RunnableConfig, Transform user messages into a structured research brief and initialize… (+17 more)

### Community 9 - ".accept_candidate"
Cohesion: 0.12
Nodes (19): ClaimCandidatePayload, DerivationExpression, FindingCandidatePayload, GraphCandidatePayload, HypothesisCandidatePayload, MemoryCandidatePayload, PromotionCandidateResponse, PromotionReviewRequest (+11 more)

### Community 10 - "state.py"
Cohesion: 0.09
Nodes (26): AgentInputState, AgentState, ClarifyWithUser, ConductResearch, override_reducer(), BaseModel, TypedDict, Graph state definitions and data structures for the Deep Research agent. (+18 more)

### Community 11 - "ScratchpadRepository"
Cohesion: 0.13
Nodes (26): create_scratchpad_entry(), get_scratchpad_entry(), list_scratchpad_entries(), AsyncSession, get, patch, post, UUID (+18 more)

### Community 12 - "chat/context.py"
Cohesion: 0.08
Nodes (37): build_ground_context(), build_research_context(), _ContextCandidate, ContextItemManifest, estimate_tokens(), EvictedItemManifest, GroundContext, Any (+29 more)

### Community 13 - "Request"
Cohesion: 0.33
Nodes (5): limit_upload_size(), Request, set_neosis_run_id(), UploadSizeLimitMiddleware, BaseHTTPMiddleware

### Community 14 - "OpenNotebookClient"
Cohesion: 0.07
Nodes (25): CircuitBreaker, CircuitState, OpenNotebookClient, Any, HTTP client for communicating with the Open Notebook API. Establishes the…, Check health endpoint of Open Notebook. Returns the parsed JSON response.…, Wraps a shared httpx client so each request uses a longer per-call timeout., Streams the ask response, yielding standardized SSE events. (+17 more)

### Community 15 - "chat/service.py"
Cohesion: 0.09
Nodes (20): ChatEventType, Enum, str, ChatEventRepository, ChatEventService, format_sse_event(), Any, AsyncSession (+12 more)

### Community 16 - "deep_researcher.py"
Cohesion: 0.13
Nodes (17): execute_tool_safely(), Main LangGraph implementation for the Deep Research agent., Safely execute a tool with error handling., Execute tools called by the researcher, including search tools and strategic…, researcher_tools(), System prompts and prompt templates for the Deep Research agent., anthropic_websearch_called(), get_model_token_limit() (+9 more)

### Community 17 - "ResearchSourceResult"
Cohesion: 0.31
Nodes (7): ABC, BaseRetriever, Execute retrieval for a given query and return normalized ResearchSourceResult…, ResearchRetrievalPolicy, ResearchSourceResult, MCPRetriever, Any

### Community 18 - "ResearchEngine"
Cohesion: 0.20
Nodes (10): Trigger cooperative cancellation of the running execution., Abstract interface for all research engines in Neosis., ResearchEngine, Any, Central factory to resolve the correct ResearchEngine based on the run's engine…, ResearchEngineFactory, LegacyResearchEngine, deprecated (+2 more)

### Community 19 - "derivation.py"
Cohesion: 0.09
Nodes (28): ProvenanceRef, CrossWorkspaceBoundaryError, DerivationService, Any, AsyncSession, Exception, UUID, Raised when a provenance reference points across workspace boundaries or does… (+20 more)

### Community 20 - "configuration.py"
Cohesion: 0.20
Nodes (11): Config, Configuration, MCPConfig, BaseModel, Enum, Configuration management for the Open Deep Research system., Enumeration of available search API providers., Configuration for Model Context Protocol (MCP) servers. (+3 more)

### Community 21 - "ConversationRepository"
Cohesion: 0.13
Nodes (18): ChatEvent, Conversation, ConversationTurn, GroundConversation, Base, Durable event record for real-time turn execution streaming and reconnect…, Canonical conversational container within a Neosis workspace. Mode-agnostic:…, Canonical turn record representing a single prompt-response interaction within… (+10 more)

### Community 22 - "OpenNotebookGroundEngine"
Cohesion: 0.19
Nodes (16): list_workspace_upstream_source_ids(), map_canonical_sources_to_upstream(), map_citations(), AsyncSession, UUID, Map upstream Open Notebook source IDs back to canonical Neosis source_ids.…, Map canonical Neosis source_ids (UUIDs) to upstream Open Notebook source IDs…, All projected Open Notebook source IDs belonging to a workspace (used when no… (+8 more)

### Community 23 - "research/service.py"
Cohesion: 0.23
Nodes (14): GraphRepository, UUID, Projects an OutputGraph into Neo4j. Nodes get labels: OutputNode, plus their…, OutputGraph, OutputGraphEdge, OutputGraphNode, ProvenanceBundle, BaseModel (+6 more)

### Community 24 - "PromotionError"
Cohesion: 0.11
Nodes (15): CandidateNotFoundError, InvalidCandidateTypeError, InvalidPayloadError, PromotionError, Any, AsyncSession, Exception, Redis (+7 more)

### Community 25 - "ResearchModeOrchestrator"
Cohesion: 0.27
Nodes (7): BaseModel, deprecated, UUID, ResearchContext, ResearchModeOrchestrator, ResearchState, TypedDict

### Community 26 - "ValueError"
Cohesion: 0.40
Nodes (3): field_validator, model_validator, ValueError

### Community 27 - "routes/chat.py"
Cohesion: 0.18
Nodes (28): cancel_turn(), create_conversation(), get_conversation(), get_turn(), list_conversations(), list_turn_events(), list_turns(), get (+20 more)

### Community 28 - "OpenDeepResearchEngine"
Cohesion: 0.21
Nodes (7): OpenDeepResearchEngine, Any, UUID, Adapter that integrates the Open Deep Research graph into Neosis as a…, Formats a canonical ResearchContext snapshot (as produced by…, Execute the ODR graph and normalize its events. Accepts an optional canonical…, Trigger cooperative cancellation of the running execution.

### Community 29 - "EpisodicMemory"
Cohesion: 0.23
Nodes (9): EpisodicMemory, Base, EpisodicRepository, AsyncSession, UUID, Used by the background worker to detect duplicate compress_episodic_job calls., EpisodicMemoryCreate, EpisodicMemoryResponse (+1 more)

### Community 30 - "ResearchNormalizationService"
Cohesion: 0.14
Nodes (12): neosis_web_search(), InjectedToolArg, RunnableConfig, tool, Fetch search results, immediately persist them to Neosis DB, and return…, Normalizes a URL by parsing it, lowercasing the scheme and netloc, and sorting…, Generates a SHA-256 fingerprint from the normalized URL and text content. Used…, Normalizes evidence and computes a deduplicating SHA-256 fingerprint. (+4 more)

### Community 31 - "get_workspace_metrics"
Cohesion: 0.40
Nodes (5): get_workspace_metrics(), AsyncSession, get, UUID, Get observability metrics for a workspace.

### Community 32 - "WorkingMemoryState"
Cohesion: 0.19
Nodes (12): Validates infrastructure, checkpointer, and security invariants during…, validate_production_startup(), TypedDict, WorkingMemoryState, get_checkpointer(), process_memory(), Any, Validates checkpointer configuration on startup. In production, durable… (+4 more)

### Community 33 - "tasks.py"
Cohesion: 0.12
Nodes (26): ChunkingService, arq WorkerSettings — defines the worker process configuration. Run the worker…, Runs once when the worker process shuts down., shutdown(), compress_episodic_job(), delete_open_notebook_source_job(), delete_open_notebook_workspace_job(), export_workspace_job() (+18 more)

### Community 34 - "worker.py"
Cohesion: 0.25
Nodes (7): get_worker_pool_status(), Any, get, Get the current status of worker pools and queues., Returns the configuration for a specific queue., arq worker settings class. Discovered by: python -m arq…, WorkerSettings

### Community 35 - "ground/factory.py"
Cohesion: 0.07
Nodes (33): embed_call(), get_embed_gateway(), get_llm_gateway(), llm_call(), Resolve (api_key, base_url, model) for the OpenAI-compatible gateway., Real OpenAI-compatible chat completion., Real OpenAI-compatible embedding, sized to the pgvector column., _resolve_llm_credentials() (+25 more)

### Community 36 - "is_token_limit_exceeded"
Cohesion: 0.27
Nodes (10): _check_anthropic_token_limit(), _check_gemini_token_limit(), _check_openai_token_limit(), is_token_limit_exceeded(), McpError, Exception, Determine if an exception indicates a token/context limit was exceeded. Args:…, Check if exception indicates OpenAI token limit exceeded. (+2 more)

### Community 37 - "GraphStore"
Cohesion: 0.17
Nodes (5): GraphStore, Neo4jAdapter, Any, Abstract base class for our operational Knowledge Graph. This hides the…, AsyncDriver

### Community 38 - "workspaces.py"
Cohesion: 0.08
Nodes (56): ask_ground_mode(), ask_ground_mode_stream(), chat_ground_mode(), create_workspace(), create_workspace_commit(), delete_workspace(), download_source_file(), get_hybrid_retrieval_service() (+48 more)

### Community 39 - "get_all_tools"
Cohesion: 0.24
Nodes (10): get_all_tools(), get_config_value(), get_search_tool(), Tool for strategic reflection on research progress and decision-making. Use…, Configure and return search tools based on the specified API provider. Args:…, Assemble complete toolkit including research, search, and MCP tools. Args:…, Extract value from configuration, handling enums and None values., think_tool() (+2 more)

### Community 40 - "telemetry.py"
Cohesion: 0.28
Nodes (7): Sanitizes sensitive tokens, passwords, and API keys from log strings., Logging filter that intercepts log records and redacts any credentials, bearer…, Sets up OpenTelemetry and attaches secret sanitization to the logging root., sanitize_log_message(), SecretSanitizingFilter, setup_telemetry(), LogRecord

### Community 42 - "Source"
Cohesion: 0.06
Nodes (33): DocumentBlock, Base, Base, Source, SourceSnapshot, BlockRepository, AsyncSession, UUID (+25 more)

### Community 43 - "UsageTracker"
Cohesion: 0.13
Nodes (9): BudgetEnforcingCallbackHandler, Exception, Raised when an execution exceeds its allocated budget., Intercepts LLM results to track usage and enforce budgets., Track token usage after an LLM call completes., ResearchBudgetExceeded, UsageTracker, AsyncCallbackHandler (+1 more)

### Community 45 - "PromotionService"
Cohesion: 0.33
Nodes (13): accept_promotion(), get_promotion(), _get_promotion_service(), list_promotions(), AsyncSession, get, post, Redis (+5 more)

### Community 46 - "ResearchExecutionError"
Cohesion: 0.32
Nodes (7): Exception, Raised when token limits are exceeded., Base class for research execution errors., Raised when an engine cannot be instantiated due to missing dependencies or…, ResearchEngineSetupError, ResearchExecutionError, TokenLimitExceededError

### Community 47 - "_get_source_and_snapshot"
Cohesion: 0.25
Nodes (8): _get_source_and_snapshot(), project_to_open_notebook_job(), AsyncSession, UUID, Background job: Projects a new source snapshot to Open Notebook., Load the source + its first snapshot in a single query., Source, SourceSnapshot

### Community 49 - "ChatService"
Cohesion: 0.08
Nodes (22): OpenNotebookConversationBinding, ChatService, Any, ArqRedis, AsyncSession, UUID, Submits a turn and returns an async generator streaming its events via SSE.…, Coordinates turn submission, mode dispatching (Ground vs Research),… (+14 more)

### Community 50 - "get_chat_service"
Cohesion: 0.40
Nodes (5): get_chat_service(), get_conversation_repository(), get_workspace_repository(), ArqRedis, AsyncSession

### Community 56 - "GPTResearcherRetriever"
Cohesion: 0.16
Nodes (10): GPTResearcherInput, GPTResearcherTool, Any, BaseModel, BaseTool, RunnableConfig, Use the tool asynchronously., GPTResearcherRetriever (+2 more)

### Community 57 - "ResearchBudgetPolicy"
Cohesion: 0.22
Nodes (6): Any, UUID, Research-specific budget policy to enforce cost and usage limits., Check if the budget for a research run has been exceeded. Returns True if the…, Returns the current budget status., ResearchBudgetPolicy

### Community 63 - "NeosisAPIClient"
Cohesion: 0.09
Nodes (19): NeosisLM Streamlit Root Entrypoint Delegates to the active testbed in ui/app.py, APIError, generate_dev_token(), get_client(), init_session_state(), main(), NeosisAPIClient, Any (+11 more)

### Community 64 - "research/promotion.py"
Cohesion: 0.19
Nodes (11): KnowledgeMemory, Base, KnowledgeRepository, AsyncSession, UUID, KnowledgeMemoryCreate, KnowledgeMemoryResponse, Provenance (+3 more)

### Community 66 - "RetrieverRegistry"
Cohesion: 0.18
Nodes (7): Any, Register a retriever instance under a name., Get a registered retriever by name., List all registered retriever names., Execute retrieval using the specified retriever or policy defaults, enforcing…, Central registry for managing and invoking retrievers (web, academic, mcp,…, RetrieverRegistry

### Community 75 - "create_research_run"
Cohesion: 0.24
Nodes (11): create_research_run(), get_queue_status(), Any, AsyncSession, get, post, Redis, Response (+3 more)

### Community 76 - "get_quota_status"
Cohesion: 0.33
Nodes (6): get_quota_status(), AsyncSession, get, Redis, UUID, Get the current quota status for the user and workspace.

### Community 77 - "tavily_search"
Cohesion: 0.33
Nodes (6): Summarize webpage content using AI model with timeout protection. Args: model:…, Fetch and summarize search results from Tavily search API. Args: queries: List…, summarize_webpage(), tavily_search(), BaseChatModel, InjectedToolArg

### Community 78 - "stream_job_events"
Cohesion: 0.40
Nodes (5): ArqRedis, get, Request, Streams Server-Sent Events (SSE) from the Redis Pub/Sub channel for a given job., stream_job_events()

### Community 79 - "get_rate_limit_status"
Cohesion: 0.40
Nodes (5): get_rate_limit_status(), get, Redis, UUID, Get the current rate limit status for the user.

### Community 80 - ".astream_events"
Cohesion: 0.40
Nodes (3): Any, UUID, Stream events from the legacy orchestrator. The legacy orchestrator doesn't…

### Community 85 - "rate_limit.py"
Cohesion: 0.50
Nodes (3): get_rate_limit_key(), Request, Rate limit by user ID if authenticated, else fallback to IP.

### Community 86 - ".astream_events"
Cohesion: 0.50
Nodes (3): Any, UUID, Stream execution events from the research engine. Args: run_id: The canonical…

### Community 88 - ".process_docling_output"
Cohesion: 0.50
Nodes (3): Any, Takes the raw dictionary output from Docling and converts it into…, DocumentBlockCreate

## Knowledge Gaps
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ResearchRepository` connect `ResearchRepository` to `research/promotion.py`, `ProviderRateLimiter`, `WorkspaceRepository`, `promotions.py`, `ResearchQuotaService`, `create_research_run`, `get_quota_status`, `PromotionService`, `chat/service.py`, `ChatService`, `ResearchSourceResult`, `research/service.py`, `PromotionError`, `GPTResearcherRetriever`, `ResearchBudgetPolicy`, `ResearchNormalizationService`, `get_workspace_metrics`?**
  _High betweenness centrality (0.153) - this node is a cross-community bridge._
- **Why does `ResearchQuotaService` connect `ResearchQuotaService` to `ProviderRateLimiter`, `ResearchRepository`, `promotions.py`, `create_research_run`, `get_quota_status`, `chat/service.py`, `ChatService`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Why does `ResearchRun` connect `ResearchRepository` to `research/promotion.py`, `promotions.py`, `ResearchQuotaService`, `Source`, `ScratchpadRepository`, `chat/context.py`, `PromotionService`, `chat/service.py`, `ChatService`, `derivation.py`, `research/service.py`, `.admit_research_run`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `ResearchRepository` (e.g. with `ResearchArtifact` and `ResearchEvent`) actually correct?**
  _`ResearchRepository` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `ChatService` (e.g. with `cancel_turn()` and `get_turn()`) actually correct?**
  _`ChatService` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `ConversationRepository` (e.g. with `ChatEvent` and `Conversation`) actually correct?**
  _`ConversationRepository` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `WorkspaceRepository` (e.g. with `DeletionTombstone` and `OpenNotebookWorkspaceBinding`) actually correct?**
  _`WorkspaceRepository` has 5 INFERRED edges - model-reasoned connections that need verification._