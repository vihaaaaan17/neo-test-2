# Graph Report - NeosisLM  (2026-10-01)

## Corpus Check
- 140 files · ~63,257 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1354 nodes · 3373 edges · 83 communities (61 shown, 8 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 268 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1f833b04`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- export.py
- chat/service.py
- OpenNotebookGroundEngine
- ResearchRepository
- FastAPI
- ResearchQuotaService
- utils.py
- WorkingMemoryState
- Configuration
- run_research_agent_job
- state.py
- ScratchpadRepository
- chat/context.py
- main.py
- OpenNotebookClient
- ChatEventRepository
- deep_researcher.py
- BaseRetriever
- OpenDeepResearchEngine
- verification.py
- get_all_tools
- ConversationRepository
- database.py
- derivation.py
- research/promotion.py
- WorkspaceRepository
- ValueError
- routes/chat.py
- DerivationService
- EpisodicRepository
- ResearchNormalizationService
- ResearchMetricsService
- validate_checkpointer
- tasks.py
- settings.py
- ResearchModeOrchestrator
- is_token_limit_exceeded
- GraphStore
- chat_ground_mode
- telemetry.py
- workspaces.py
- DocumentBlock
- UsageTracker
- client.py
- promotions.py
- get_notes_from_tool_calls
- UUID
- integrations/__init__.py
- ChatService
- ask_ground_mode
- run_live_test.py
- ResearchRun
- ResearchQuestion
- GPTResearcherRetriever
- research/budget.py
- SearchQuery
- ResearchSourceResult
- SearchQuery
- SearchQuery
- ResearchQuestion
- NeosisAPIClient
- KnowledgeMemory
- .retrieve
- create_research_run
- ResearchProvenanceService
- ResearchEvidence
- Source
- schemas/source.py
- .__init__

## God Nodes (most connected - your core abstractions)
1. `ResearchRepository` - 72 edges
2. `WorkspaceRepository` - 48 edges
3. `ConversationRepository` - 42 edges
4. `ChatService` - 42 edges
5. `ResearchRun` - 37 edges
6. `NeosisAPIClient` - 36 edges
7. `ConversationTurn` - 32 edges
8. `Workspace` - 30 edges
9. `OpenNotebookClient` - 29 edges
10. `ResearchArtifact` - 29 edges

## Surprising Connections (you probably didn't know these)
- `main()` --uses--> `Workspace`  [INFERRED]
  scratch/list_workspaces.py → app/models/workspace.py
- `main()` --uses--> `Conversation`  [INFERRED]
  scratch/get_workspaces_db.py → app/models/conversation.py
- `main()` --uses--> `ConversationTurn`  [INFERRED]
  scratch/check_err.py → app/models/conversation.py
- `main()` --uses--> `ChatEvent`  [INFERRED]
  scratch/check_err.py → app/models/conversation.py
- `main()` --uses--> `Workspace`  [INFERRED]
  scratch/get_workspaces_db.py → app/models/workspace.py

## Import Cycles
- None detected.

## Communities (83 total, 8 thin omitted)

### Community 0 - "export.py"
Cohesion: 0.12
Nodes (14): EpisodicMemory, Base, AsyncSession, UUID, WorkspaceExportService, get_object_store(), ObjectStoreProtocol, Protocol (+6 more)

### Community 1 - "chat/service.py"
Cohesion: 0.11
Nodes (16): BaseModel, ResearchRunResponse, Any, UUID, Research Admission Controller to enforce quotas and rate limits before…, Admits a new research run after checking quotas and rate limits., Returns the current queue status., ResearchAdmissionController (+8 more)

### Community 2 - "OpenNotebookGroundEngine"
Cohesion: 0.12
Nodes (22): map_canonical_sources_to_upstream(), map_citations(), AsyncSession, UUID, Map upstream Open Notebook source IDs back to canonical Neosis source_ids.…, Map canonical Neosis source_ids (UUIDs) to upstream Open Notebook source IDs…, OpenNotebookGroundEngine, Any (+14 more)

### Community 3 - "ResearchRepository"
Cohesion: 0.18
Nodes (7): ResearchArtifact, UUID, Unified repository for all Research Fabric models. Enforces workspace_id…, Internal helper to ensure a given run_id belongs to the workspace_id. Raises an…, Persists usage metrics to the database as a periodic checkpoint., Records a usage entry for a research run., ResearchRepository

### Community 4 - "FastAPI"
Cohesion: 0.09
Nodes (26): get_arq_redis(), Request, Dependency to get the arq Redis pool. We lazily initialize the pool and attach…, get_current_user(), UUID, get_rate_limit_key(), Request, Rate limit by user ID if authenticated, else fallback to IP. (+18 more)

### Community 5 - "ResearchQuotaService"
Cohesion: 0.12
Nodes (14): Any, UUID, Service to manage research quotas for users, workspaces, and globally., Returns the current user concurrency status., Returns the current workspace concurrency status., Returns the current global concurrency status., Enforces the user concurrency quota. Returns ACCEPTED or QUOTA_EXCEEDED., Enforces the workspace concurrency quota. Returns ACCEPTED or QUOTA_EXCEEDED. (+6 more)

### Community 6 - "utils.py"
Cohesion: 0.10
Nodes (29): fetch_tokens(), get_mcp_access_token(), get_tavily_api_key(), get_tokens(), load_mcp_tools(), Any, BaseTool, InjectedToolArg (+21 more)

### Community 7 - "WorkingMemoryState"
Cohesion: 0.21
Nodes (10): TypedDict, WorkingMemoryState, EpisodicMemoryService, UUID, llm_gateway: an async callable that takes a string prompt and returns a string…, Dispatch compression to the background queue., Call LLM with concurrency limits and retries., compress_episodic_job() (+2 more)

### Community 8 - "Configuration"
Cohesion: 0.15
Nodes (26): Config, Configuration, RunnableConfig, Create a Configuration instance from a RunnableConfig., Pydantic configuration., Main configuration class for the Deep Research agent., clarify_with_user(), compress_research() (+18 more)

### Community 9 - "run_research_agent_job"
Cohesion: 0.40
Nodes (4): Acts as the sole authority for state transitions of ResearchRun and…, ResearchLifecycleService, Background job: Runs the ResearchEngine and streams events to Redis., run_research_agent_job()

### Community 10 - "state.py"
Cohesion: 0.12
Nodes (21): AgentInputState, AgentState, ClarifyWithUser, ConductResearch, override_reducer(), BaseModel, Graph state definitions and data structures for the Deep Research agent., Call this tool to conduct research on a specific topic. (+13 more)

### Community 11 - "ScratchpadRepository"
Cohesion: 0.13
Nodes (26): create_scratchpad_entry(), get_scratchpad_entry(), list_scratchpad_entries(), AsyncSession, get, patch, post, UUID (+18 more)

### Community 12 - "chat/context.py"
Cohesion: 0.08
Nodes (36): build_ground_context(), build_research_context(), _ContextCandidate, ContextItemManifest, estimate_tokens(), EvictedItemManifest, GroundContext, Any (+28 more)

### Community 13 - "main.py"
Cohesion: 0.12
Nodes (18): Settings, get_open_notebook_timeout(), is_open_notebook_enabled(), Get the default HTTP timeout for Open Notebook requests., Check if the Open Notebook Ground Engine is enabled., check_open_notebook_health(), Check if the Open Notebook Ground Engine is reachable and healthy. Returns:…, Shared HTTP client for Open Notebook integration. (+10 more)

### Community 14 - "OpenNotebookClient"
Cohesion: 0.25
Nodes (8): OpenNotebookClient, Any, Check health endpoint of Open Notebook. Returns the parsed JSON response.…, Streams the ask response, yielding standardized SSE events., Executes a chat message. Returns the final answer text and the updated…, Streams chat events and incremental tokens for a conversation session. Yields…, HTTP client for communicating with the Open Notebook API. Establishes the…, with_error_translation()

### Community 15 - "ChatEventRepository"
Cohesion: 0.10
Nodes (18): ChatEventRepository, ChatEventService, format_sse_event(), Any, AsyncSession, UUID, Fetches all events for a given turn strictly after the specified sequence,…, Dual in-process and Redis Pub/Sub event broker. Provides sub/pub abstraction… (+10 more)

### Community 16 - "deep_researcher.py"
Cohesion: 0.13
Nodes (17): execute_tool_safely(), Main LangGraph implementation for the Deep Research agent., Safely execute a tool with error handling., Execute tools called by the researcher, including search tools and strategic…, researcher_tools(), System prompts and prompt templates for the Deep Research agent., TypedDict, State for the supervisor that manages research tasks. (+9 more)

### Community 17 - "BaseRetriever"
Cohesion: 0.28
Nodes (8): ABC, BaseRetriever, ResearchRetrievalPolicy, Register a retriever instance under a name., List all registered retriever names., Central registry for managing and invoking retrievers (web, academic, mcp,…, RetrieverRegistry, WebRetriever

### Community 18 - "OpenDeepResearchEngine"
Cohesion: 0.05
Nodes (38): BudgetEnforcingCallbackHandler, Exception, Raised when an execution exceeds its allocated budget., Intercepts LLM results to track usage and enforce budgets., Track token usage after an LLM call completes., ResearchBudgetExceeded, Any, UUID (+30 more)

### Community 19 - "verification.py"
Cohesion: 0.16
Nodes (16): ArithmeticVerificationError, DeterministicArithmeticVerifier, _pct_change(), Any, BaseModel, Exception, Raised when an expression violates safety rules, resource limits, or arithmetic…, Evaluates an arithmetic expression and compares the computed value against an… (+8 more)

### Community 20 - "get_all_tools"
Cohesion: 0.14
Nodes (16): MCPConfig, BaseModel, Enum, Configuration management for the Open Deep Research system., Enumeration of available search API providers., Configuration for Model Context Protocol (MCP) servers., SearchAPI, get_all_tools() (+8 more)

### Community 21 - "ConversationRepository"
Cohesion: 0.13
Nodes (18): ChatEvent, Conversation, ConversationTurn, GroundConversation, Base, Durable event record for real-time turn execution streaming and reconnect…, Canonical conversational container within a Neosis workspace. Mode-agnostic:…, Canonical turn record representing a single prompt-response interaction within… (+10 more)

### Community 22 - "database.py"
Cohesion: 0.12
Nodes (17): get_embed_gateway(), get_llm_gateway(), mock_embed_call(), mock_llm_call(), get_hybrid_retrieval_service(), get_db(), get_ground_engine(), get_hybrid_retrieval_service() (+9 more)

### Community 23 - "derivation.py"
Cohesion: 0.19
Nodes (16): GraphRepository, UUID, Projects an OutputGraph into Neo4j. Nodes get labels: OutputNode, plus their…, OutputGraph, OutputGraphEdge, OutputGraphNode, ProvenanceBundle, ProvenanceRef (+8 more)

### Community 24 - "research/promotion.py"
Cohesion: 0.09
Nodes (28): GraphCandidatePayload, MemoryCandidatePayload, CandidateNotFoundError, InvalidCandidateTypeError, InvalidLifecycleTransitionError, InvalidPayloadError, PromotionError, PromotionService (+20 more)

### Community 25 - "WorkspaceRepository"
Cohesion: 0.25
Nodes (7): Base, Workspace, WorkspaceCommit, AsyncSession, UUID, Atomically rolls back the workspace to a target commit under a row lock (FOR…, WorkspaceRepository

### Community 26 - "ValueError"
Cohesion: 0.15
Nodes (10): InvalidTransitionError, Any, datetime, Exception, UUID, Transition a ResearchTask to a new status. Emits a ResearchEvent., Transition a ResearchRun to a new status. Emits a ResearchEvent., field_validator (+2 more)

### Community 27 - "routes/chat.py"
Cohesion: 0.16
Nodes (30): cancel_turn(), create_conversation(), get_conversation(), get_conversation_repository(), get_turn(), get_workspace_repository(), list_conversations(), list_turn_events() (+22 more)

### Community 28 - "DerivationService"
Cohesion: 0.18
Nodes (10): CrossWorkspaceBoundaryError, DerivationService, Any, AsyncSession, Exception, UUID, Raised when a provenance reference points across workspace boundaries or does…, Validates provenance references, runs deterministic verification if derivations… (+2 more)

### Community 29 - "EpisodicRepository"
Cohesion: 0.26
Nodes (7): EpisodicRepository, AsyncSession, UUID, Used by the background worker to detect duplicate compress_episodic_job calls., EpisodicMemoryCreate, EpisodicMemoryResponse, BaseModel

### Community 30 - "ResearchNormalizationService"
Cohesion: 0.15
Nodes (12): GPTResearcherInput, BaseModel, neosis_web_search(), InjectedToolArg, RunnableConfig, tool, Fetch search results, immediately persist them to Neosis DB, and return…, Normalizes a URL by parsing it, lowercasing the scheme and netloc, and sorting… (+4 more)

### Community 31 - "ResearchMetricsService"
Cohesion: 0.13
Nodes (15): get_workspace_metrics(), AsyncSession, get, UUID, Get observability metrics for a workspace., Any, datetime, UUID (+7 more)

### Community 32 - "validate_checkpointer"
Cohesion: 0.21
Nodes (10): Validates infrastructure, checkpointer, and security invariants during…, validate_production_startup(), get_checkpointer(), process_memory(), Any, Validates checkpointer configuration on startup. In production, durable…, Returns the checkpointer instance appropriate for the current environment., validate_checkpointer() (+2 more)

### Community 33 - "tasks.py"
Cohesion: 0.11
Nodes (22): ChunkingService, DocumentParser, Any, Downloads a document from Object Storage and parses it using docling. Returns a…, delete_open_notebook_source_job(), delete_open_notebook_workspace_job(), _get_source_and_snapshot(), parse_and_chunk_job() (+14 more)

### Community 34 - "settings.py"
Cohesion: 0.18
Nodes (10): get_worker_pool_status(), Any, get, Get the current status of worker pools and queues., arq WorkerSettings — defines the worker process configuration. Run the worker…, Returns the configuration for a specific queue., Runs once when the worker process shuts down., arq worker settings class. Discovered by: python -m arq… (+2 more)

### Community 35 - "ResearchModeOrchestrator"
Cohesion: 0.08
Nodes (22): GroundModeOrchestrator, GroundModeState, Any, deprecated, TypedDict, UUID, Deprecated: Use OpenNotebookGroundEngine instead. This orchestrator handles the…, Any (+14 more)

### Community 36 - "is_token_limit_exceeded"
Cohesion: 0.27
Nodes (10): _check_anthropic_token_limit(), _check_gemini_token_limit(), _check_openai_token_limit(), is_token_limit_exceeded(), McpError, Exception, Determine if an exception indicates a token/context limit was exceeded. Args:…, Check if exception indicates OpenAI token limit exceeded. (+2 more)

### Community 37 - "GraphStore"
Cohesion: 0.17
Nodes (5): GraphStore, Neo4jAdapter, Any, Abstract base class for our operational Knowledge Graph. This hides the…, AsyncDriver

### Community 38 - "chat_ground_mode"
Cohesion: 0.15
Nodes (18): chat_ground_mode(), create_workspace_commit(), delete_workspace(), get_knowledge_repository(), get_quota(), get_research_repository(), get_source_repository(), get_workspace_repository() (+10 more)

### Community 40 - "telemetry.py"
Cohesion: 0.28
Nodes (7): Sanitizes sensitive tokens, passwords, and API keys from log strings., Logging filter that intercepts log records and redacts any credentials, bearer…, Sets up OpenTelemetry and attaches secret sanitization to the logging root., sanitize_log_message(), SecretSanitizingFilter, setup_telemetry(), LogRecord

### Community 41 - "workspaces.py"
Cohesion: 0.27
Nodes (12): create_workspace(), patch, update_workspace(), FileUploadResponse, BaseModel, BaseModel, ResearchRequest, RollbackRequest (+4 more)

### Community 42 - "DocumentBlock"
Cohesion: 0.18
Nodes (10): DocumentBlock, Base, BlockRepository, AsyncSession, UUID, DocumentBlockCreate, DocumentBlockResponse, BaseModel (+2 more)

### Community 43 - "UsageTracker"
Cohesion: 0.20
Nodes (3): UsageTracker, MCPRetriever, Any

### Community 44 - "client.py"
Cohesion: 0.18
Nodes (6): CircuitBreaker, CircuitState, Enum, get_open_notebook_base_url(), Get the base URL for the Open Notebook API., AsyncClient

### Community 45 - "promotions.py"
Cohesion: 0.23
Nodes (19): accept_promotion(), get_promotion(), _get_promotion_service(), list_promotions(), AsyncSession, get, post, Redis (+11 more)

### Community 46 - "get_notes_from_tool_calls"
Cohesion: 0.40
Nodes (5): get_notes_from_tool_calls(), Extract notes from tool call messages., Truncate message history by removing up to the last AI message. This is useful…, remove_up_to_last_ai_message(), MessageLikeRepresentation

### Community 47 - "UUID"
Cohesion: 0.19
Nodes (14): download_source_file(), get_projection_status(), get_source_status(), get_workspace(), get_workspace_output_graph(), get, Request, UUID (+6 more)

### Community 49 - "ChatService"
Cohesion: 0.11
Nodes (18): OpenNotebookConversationBinding, TurnCreate, ChatService, Any, UUID, Submits a turn and returns an async generator streaming its events via SSE.…, Unified SSE generator — supports reconnect replay via Last-Event-ID. Protocol:…, Coordinates turn submission, mode dispatching (Ground vs Research),… (+10 more)

### Community 50 - "ask_ground_mode"
Cohesion: 0.19
Nodes (11): get_chat_service(), ArqRedis, ask_ground_mode(), ask_ground_mode_stream(), AskRequest, AskResponse, BaseModel, GroundEngineProtocol (+3 more)

### Community 53 - "ResearchRun"
Cohesion: 0.47
Nodes (7): Base, ResearchEvent, ResearchReport, ResearchRun, ResearchTask, ResearchUsage, main()

### Community 56 - "GPTResearcherRetriever"
Cohesion: 0.18
Nodes (8): GPTResearcherTool, Any, BaseTool, RunnableConfig, Use the tool asynchronously., GPTResearcherRetriever, Any, Creates a mock LLM provider for GPTResearcher that uses Neosis's llm_gateway.…

### Community 57 - "research/budget.py"
Cohesion: 0.20
Nodes (6): Any, UUID, Research-specific budget policy to enforce cost and usage limits., Check if the budget for a research run has been exceeded. Returns True if the…, Returns the current budget status., ResearchBudgetPolicy

### Community 59 - "ResearchSourceResult"
Cohesion: 0.29
Nodes (5): AcademicRetriever, Any, Execute retrieval for a given query and return normalized ResearchSourceResult…, ResearchSourceResult, Any

### Community 63 - "NeosisAPIClient"
Cohesion: 0.09
Nodes (19): NeosisLM Streamlit Root Entrypoint Delegates to the active testbed in ui/app.py, APIError, generate_dev_token(), get_client(), init_session_state(), main(), NeosisAPIClient, Any (+11 more)

### Community 64 - "KnowledgeMemory"
Cohesion: 0.09
Nodes (26): get_memory_router(), KnowledgeMemory, Base, KnowledgeRepository, AsyncSession, UUID, KnowledgeMemoryCreate, KnowledgeMemoryResponse (+18 more)

### Community 66 - ".retrieve"
Cohesion: 0.40
Nodes (3): Any, Get a registered retriever by name., Execute retrieval using the specified retriever or policy defaults, enforcing…

### Community 75 - "create_research_run"
Cohesion: 0.24
Nodes (11): create_research_run(), get_queue_status(), Any, AsyncSession, get, post, Redis, Response (+3 more)

### Community 76 - "ResearchProvenanceService"
Cohesion: 0.22
Nodes (7): Any, AsyncSession, UUID, Attempts to resolve an external citation to an existing workspace Source.…, Audits the full provenance chain for a given report_id. Chain: Report ->…, Manages the mapping of external citations/evidence to canonical workspace…, ResearchProvenanceService

### Community 77 - "ResearchEvidence"
Cohesion: 0.36
Nodes (5): ResearchEvidence, Any, Creates multiple evidence records in batches with fingerprint deduplication., Retrieves evidence records by their fingerprints., Performs a bulk insert of evidence records.

### Community 78 - "Source"
Cohesion: 0.52
Nodes (4): Base, Source, SourceSnapshot, UUID

### Community 79 - "schemas/source.py"
Cohesion: 0.67
Nodes (3): BaseModel, SourceResponse, SourceSnapshotResponse

## Knowledge Gaps
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ResearchRepository` connect `ResearchRepository` to `chat/service.py`, `FastAPI`, `ResearchQuotaService`, `run_research_agent_job`, `ChatEventRepository`, `OpenDeepResearchEngine`, `derivation.py`, `research/promotion.py`, `WorkspaceRepository`, `ResearchNormalizationService`, `ResearchMetricsService`, `tasks.py`, `chat_ground_mode`, `workspaces.py`, `promotions.py`, `ResearchRun`, `GPTResearcherRetriever`, `research/budget.py`, `create_research_run`, `ResearchEvidence`, `.__init__`?**
  _High betweenness centrality (0.187) - this node is a cross-community bridge._
- **Why does `neosis_web_search()` connect `ResearchNormalizationService` to `ResearchRepository`, `get_all_tools`, `utils.py`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Why does `ConversationRepository` connect `ConversationRepository` to `chat/service.py`, `tasks.py`, `chat_ground_mode`, `workspaces.py`, `run_research_agent_job`, `create_research_run`, `ScratchpadRepository`, `ChatEventRepository`, `ChatService`, `ask_ground_mode`, `routes/chat.py`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `ResearchRepository` (e.g. with `ResearchArtifact` and `ResearchEvent`) actually correct?**
  _`ResearchRepository` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `WorkspaceRepository` (e.g. with `DeletionTombstone` and `OpenNotebookWorkspaceBinding`) actually correct?**
  _`WorkspaceRepository` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `ConversationRepository` (e.g. with `ChatEvent` and `Conversation`) actually correct?**
  _`ConversationRepository` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `ChatService` (e.g. with `cancel_turn()` and `get_turn()`) actually correct?**
  _`ChatService` has 22 INFERRED edges - model-reasoned connections that need verification._