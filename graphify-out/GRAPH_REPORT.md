# Graph Report - NeosisLM  (2026-09-29)

## Corpus Check
- 116 files · ~53,793 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1265 nodes · 3224 edges · 68 communities (64 shown, 3 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 262 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `919f9012`
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
- KnowledgeMemoryCreate
- state.py
- ScratchpadRepository
- chat/context.py
- client.py
- OpenNotebookClient
- ChatEvent
- deep_researcher.py
- BaseRetriever
- OpenDeepResearchEngine
- verification.py
- get_all_tools
- ConversationRepository
- database.py
- ResearchRun
- promotions.py
- ResearchModeOrchestrator
- ValueError
- routes/chat.py
- ResearchLifecycleService
- Neo4jAdapter
- ResearchNormalizationService
- Source
- WorkspaceRepository
- QuotaService
- FastAPI
- GroundModeOrchestrator
- is_token_limit_exceeded
- create_research_run
- chat_ground_mode
- workspaces.py
- telemetry.py
- settings.py
- DerivationService
- UsageTracker
- research/service.py
- get_quota_status
- get_notes_from_tool_calls
- core/config.py
- integrations/__init__.py
- ChatService
- UUID
- main.py
- stream_job_events
- CircuitBreaker
- .__init__
- GPTResearcherRetriever
- research/budget.py
- Any
- ResearchSourceResult
- TurnCreate
- Any
- tasks.py
- streamlit_app.py
- _get_source_and_snapshot
- get_rate_limit_status
- .retrieve
- rate_limit.py

## God Nodes (most connected - your core abstractions)
1. `ResearchRepository` - 72 edges
2. `WorkspaceRepository` - 49 edges
3. `ConversationRepository` - 42 edges
4. `ChatService` - 42 edges
5. `ResearchRun` - 34 edges
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

## Communities (68 total, 3 thin omitted)

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
Cohesion: 0.13
Nodes (15): ResearchArtifact, ResearchEvidence, ResearchReport, Any, UUID, Creates multiple evidence records in batches with fingerprint deduplication., Retrieves evidence records by their fingerprints., Performs a bulk insert of evidence records. (+7 more)

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
Cohesion: 0.12
Nodes (17): EpisodicRepository, AsyncSession, UUID, Used by the background worker to detect duplicate compress_episodic_job calls., EpisodicMemoryCreate, EpisodicMemoryResponse, BaseModel, TypedDict (+9 more)

### Community 8 - "Configuration"
Cohesion: 0.15
Nodes (26): Config, Configuration, RunnableConfig, Create a Configuration instance from a RunnableConfig., Pydantic configuration., Main configuration class for the Deep Research agent., clarify_with_user(), compress_research() (+18 more)

### Community 9 - "KnowledgeMemoryCreate"
Cohesion: 0.43
Nodes (5): KnowledgeMemoryCreate, KnowledgeMemoryResponse, Provenance, BaseModel, Finds all ResearchArtifacts for a given run with type='memory_candidate' and…

### Community 10 - "state.py"
Cohesion: 0.12
Nodes (21): AgentInputState, AgentState, ClarifyWithUser, ConductResearch, override_reducer(), BaseModel, Graph state definitions and data structures for the Deep Research agent., Call this tool to conduct research on a specific topic. (+13 more)

### Community 11 - "ScratchpadRepository"
Cohesion: 0.13
Nodes (26): create_scratchpad_entry(), get_scratchpad_entry(), list_scratchpad_entries(), AsyncSession, get, patch, post, UUID (+18 more)

### Community 12 - "chat/context.py"
Cohesion: 0.06
Nodes (44): KnowledgeMemory, Base, KnowledgeRepository, AsyncSession, UUID, build_ground_context(), build_research_context(), _ContextCandidate (+36 more)

### Community 13 - "client.py"
Cohesion: 0.20
Nodes (11): CircuitState, Enum, get_open_notebook_base_url(), get_open_notebook_timeout(), is_open_notebook_enabled(), Get the default HTTP timeout for Open Notebook requests., Check if the Open Notebook Ground Engine is enabled., Get the base URL for the Open Notebook API. (+3 more)

### Community 14 - "OpenNotebookClient"
Cohesion: 0.25
Nodes (8): OpenNotebookClient, Any, Check health endpoint of Open Notebook. Returns the parsed JSON response.…, Streams the ask response, yielding standardized SSE events., Executes a chat message. Returns the final answer text and the updated…, Streams chat events and incremental tokens for a conversation session. Yields…, HTTP client for communicating with the Open Notebook API. Establishes the…, with_error_translation()

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

### Community 19 - "verification.py"
Cohesion: 0.16
Nodes (16): ArithmeticVerificationError, DeterministicArithmeticVerifier, _pct_change(), Any, BaseModel, Exception, Raised when an expression violates safety rules, resource limits, or arithmetic…, Evaluates an arithmetic expression and compares the computed value against an… (+8 more)

### Community 20 - "get_all_tools"
Cohesion: 0.14
Nodes (16): MCPConfig, BaseModel, Enum, Configuration management for the Open Deep Research system., Enumeration of available search API providers., Configuration for Model Context Protocol (MCP) servers., SearchAPI, get_all_tools() (+8 more)

### Community 21 - "ConversationRepository"
Cohesion: 0.14
Nodes (14): Conversation, ConversationTurn, Canonical conversational container within a Neosis workspace. Mode-agnostic:…, Canonical turn record representing a single prompt-response interaction within…, ConversationRepository, Any, AsyncSession, datetime (+6 more)

### Community 22 - "database.py"
Cohesion: 0.12
Nodes (17): get_embed_gateway(), get_llm_gateway(), mock_embed_call(), mock_llm_call(), get_hybrid_retrieval_service(), get_db(), get_ground_engine(), get_hybrid_retrieval_service() (+9 more)

### Community 23 - "ResearchRun"
Cohesion: 0.36
Nodes (7): DocumentBlock, Base, Base, ResearchEvent, ResearchRun, ResearchTask, ResearchUsage

### Community 24 - "promotions.py"
Cohesion: 0.07
Nodes (50): accept_promotion(), get_promotion(), _get_promotion_service(), list_promotions(), AsyncSession, get, post, Redis (+42 more)

### Community 25 - "ResearchModeOrchestrator"
Cohesion: 0.16
Nodes (10): Any, BaseModel, deprecated, TypedDict, UUID, ResearchContext, ResearchModeOrchestrator, ResearchState (+2 more)

### Community 26 - "ValueError"
Cohesion: 0.13
Nodes (10): EpisodicMemory, Base, AsyncSession, UUID, WorkspaceExportService, UUID, S3ObjectStore, field_validator (+2 more)

### Community 27 - "routes/chat.py"
Cohesion: 0.16
Nodes (30): cancel_turn(), create_conversation(), get_conversation(), get_conversation_repository(), get_turn(), get_workspace_repository(), list_conversations(), list_turn_events() (+22 more)

### Community 28 - "ResearchLifecycleService"
Cohesion: 0.21
Nodes (9): InvalidTransitionError, Any, datetime, Exception, UUID, Transition a ResearchTask to a new status. Emits a ResearchEvent., Acts as the sole authority for state transitions of ResearchRun and…, Transition a ResearchRun to a new status. Emits a ResearchEvent. (+1 more)

### Community 29 - "Neo4jAdapter"
Cohesion: 0.17
Nodes (5): GraphStore, Neo4jAdapter, Any, Abstract base class for our operational Knowledge Graph. This hides the…, AsyncDriver

### Community 30 - "ResearchNormalizationService"
Cohesion: 0.15
Nodes (12): GPTResearcherInput, BaseModel, neosis_web_search(), InjectedToolArg, RunnableConfig, tool, Fetch search results, immediately persist them to Neosis DB, and return…, Normalizes a URL by parsing it, lowercasing the scheme and netloc, and sorting… (+4 more)

### Community 31 - "Source"
Cohesion: 0.16
Nodes (13): Base, Source, SourceSnapshot, AsyncSession, UUID, SourceRepository, Any, AsyncSession (+5 more)

### Community 32 - "WorkspaceRepository"
Cohesion: 0.22
Nodes (9): get_chat_service(), ArqRedis, Base, Workspace, WorkspaceCommit, AsyncSession, UUID, Atomically rolls back the workspace to a target commit under a row lock (FOR… (+1 more)

### Community 33 - "QuotaService"
Cohesion: 0.17
Nodes (10): get_memory_router(), get_quota(), get_quota_service(), AsyncSession, UUID, QuotaService, Check if user has exceeded their workspace limit., Check if workspace has exceeded its source count limit. (+2 more)

### Community 34 - "FastAPI"
Cohesion: 0.33
Nodes (7): get_arq_redis(), Request, Dependency to get the arq Redis pool. We lazily initialize the pool and attach…, get_current_user(), UUID, FastAPI, HTTPAuthorizationCredentials

### Community 35 - "GroundModeOrchestrator"
Cohesion: 0.14
Nodes (12): GroundModeOrchestrator, GroundModeState, Any, deprecated, TypedDict, UUID, Deprecated: Use OpenNotebookGroundEngine instead. This orchestrator handles the…, ContextBundle (+4 more)

### Community 36 - "is_token_limit_exceeded"
Cohesion: 0.27
Nodes (10): _check_anthropic_token_limit(), _check_gemini_token_limit(), _check_openai_token_limit(), is_token_limit_exceeded(), McpError, Exception, Determine if an exception indicates a token/context limit was exceeded. Args:…, Check if exception indicates OpenAI token limit exceeded. (+2 more)

### Community 37 - "create_research_run"
Cohesion: 0.24
Nodes (11): create_research_run(), get_queue_status(), Any, AsyncSession, get, post, Redis, Response (+3 more)

### Community 38 - "chat_ground_mode"
Cohesion: 0.15
Nodes (22): ask_ground_mode(), ask_ground_mode_stream(), chat_ground_mode(), create_workspace_commit(), get_knowledge_repository(), get_research_repository(), get_source_repository(), get_workspace_repository() (+14 more)

### Community 39 - "workspaces.py"
Cohesion: 0.20
Nodes (15): create_workspace(), patch, update_workspace(), FileUploadResponse, BaseModel, BaseModel, SourceResponse, SourceSnapshotResponse (+7 more)

### Community 40 - "telemetry.py"
Cohesion: 0.28
Nodes (7): Sanitizes sensitive tokens, passwords, and API keys from log strings., Logging filter that intercepts log records and redacts any credentials, bearer…, Sets up OpenTelemetry and attaches secret sanitization to the logging root., sanitize_log_message(), SecretSanitizingFilter, setup_telemetry(), LogRecord

### Community 41 - "settings.py"
Cohesion: 0.15
Nodes (12): get_worker_pool_status(), Any, get, Get the current status of worker pools and queues., arq WorkerSettings — defines the worker process configuration. Run the worker…, Returns the configuration for a specific queue., Runs once when the worker process starts. Populate shared resources., Runs once when the worker process shuts down. (+4 more)

### Community 42 - "DerivationService"
Cohesion: 0.24
Nodes (7): DerivationService, Any, AsyncSession, UUID, Validates provenance references, runs deterministic verification if derivations…, Normalizes candidate outputs and enforces fail-closed multi-tenant provenance…, Strictly validates that every reference in the provenance bundle exists and…

### Community 43 - "UsageTracker"
Cohesion: 0.20
Nodes (3): UsageTracker, MCPRetriever, Any

### Community 44 - "research/service.py"
Cohesion: 0.18
Nodes (18): GraphRepository, UUID, Projects an OutputGraph into Neo4j. Nodes get labels: OutputNode, plus their…, OutputGraph, OutputGraphEdge, OutputGraphNode, ProvenanceBundle, ProvenanceRef (+10 more)

### Community 45 - "get_quota_status"
Cohesion: 0.33
Nodes (6): get_quota_status(), AsyncSession, get, Redis, UUID, Get the current quota status for the user and workspace.

### Community 46 - "get_notes_from_tool_calls"
Cohesion: 0.40
Nodes (5): get_notes_from_tool_calls(), Extract notes from tool call messages., Truncate message history by removing up to the last AI message. This is useful…, remove_up_to_last_ai_message(), MessageLikeRepresentation

### Community 47 - "core/config.py"
Cohesion: 0.21
Nodes (9): Settings, Shared HTTP client for Open Notebook integration., get_checkpointer(), process_memory(), Any, Validates checkpointer configuration on startup. In production, durable…, Returns the checkpointer instance appropriate for the current environment., validate_checkpointer() (+1 more)

### Community 49 - "ChatService"
Cohesion: 0.11
Nodes (15): OpenNotebookConversationBinding, Dual in-process and Redis Pub/Sub event broker. Provides sub/pub abstraction…, TurnEventBroker, ChatService, UUID, Unified SSE generator — supports reconnect replay via Last-Event-ID. Protocol:…, Coordinates turn submission, mode dispatching (Ground vs Research),…, Executes Ground turn in background with independent DB session. Delegates… (+7 more)

### Community 50 - "UUID"
Cohesion: 0.21
Nodes (12): delete_workspace(), get_projection_status(), get_source_status(), get_workspace(), get_workspace_output_graph(), get, Request, UUID (+4 more)

### Community 52 - "main.py"
Cohesion: 0.19
Nodes (11): Validates infrastructure, checkpointer, and security invariants during…, validate_production_startup(), health_check(), lifespan(), limit_upload_size(), get, Request, Deep health check verifying Postgres and Neo4j connectivity. (+3 more)

### Community 53 - "stream_job_events"
Cohesion: 0.40
Nodes (5): ArqRedis, get, Request, Streams Server-Sent Events (SSE) from the Redis Pub/Sub channel for a given job., stream_job_events()

### Community 56 - "GPTResearcherRetriever"
Cohesion: 0.18
Nodes (8): GPTResearcherTool, Any, BaseTool, RunnableConfig, Use the tool asynchronously., GPTResearcherRetriever, Any, Creates a mock LLM provider for GPTResearcher that uses Neosis's llm_gateway.…

### Community 57 - "research/budget.py"
Cohesion: 0.20
Nodes (6): Any, UUID, Research-specific budget policy to enforce cost and usage limits., Check if the budget for a research run has been exceeded. Returns True if the…, Returns the current budget status., ResearchBudgetPolicy

### Community 58 - "Any"
Cohesion: 0.18
Nodes (11): delete_open_notebook_source_job(), delete_open_notebook_workspace_job(), export_workspace_job(), process_deletion_tombstone_job(), Any, Background job: Processes a DeletionTombstone against Open Notebook., Periodic task: Sweeps for pending tombstones and enqueues processing., Compatibility job: deletes open notebook source binding if present. (+3 more)

### Community 59 - "ResearchSourceResult"
Cohesion: 0.29
Nodes (5): AcademicRetriever, Any, Execute retrieval for a given query and return normalized ResearchSourceResult…, ResearchSourceResult, Any

### Community 60 - "TurnCreate"
Cohesion: 0.32
Nodes (5): TurnCreate, Any, Executes a Ground mode turn against Open Notebook with 1-time transparent 409…, Admits research run, links to turn, enqueues ARQ job, and returns running turn…, Submits and executes a conversation turn synchronously (or 202 for research).…

### Community 61 - "Any"
Cohesion: 0.29
Nodes (4): Any, Returns the current user concurrency status., Returns the current workspace concurrency status., Returns the current global concurrency status.

### Community 62 - "tasks.py"
Cohesion: 0.12
Nodes (16): BlockRepository, AsyncSession, Validates and sanitizes structured scratchpad content. Strictly prohibits raw…, sanitize_scratchpad_content(), ChunkingService, DocumentParser, Any, Downloads a document from Object Storage and parses it using docling. Returns a… (+8 more)

### Community 63 - "streamlit_app.py"
Cohesion: 0.43
Nodes (5): create_db_workspace(), get_litellm_gateway(), project_graph_to_neo4j(), run_agent(), run_ground_mode()

### Community 64 - "_get_source_and_snapshot"
Cohesion: 0.33
Nodes (6): _get_source_and_snapshot(), project_to_open_notebook_job(), AsyncSession, UUID, Background job: Projects a new source snapshot to Open Notebook., Load the source + its first snapshot in a single query.

### Community 65 - "get_rate_limit_status"
Cohesion: 0.40
Nodes (5): get_rate_limit_status(), get, Redis, UUID, Get the current rate limit status for the user.

### Community 66 - ".retrieve"
Cohesion: 0.40
Nodes (3): Any, Get a registered retriever by name., Execute retrieval using the specified retriever or policy defaults, enforcing…

### Community 67 - "rate_limit.py"
Cohesion: 0.50
Nodes (3): get_rate_limit_key(), Request, Rate limit by user ID if authenticated, else fallback to IP.

## Knowledge Gaps
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ResearchRepository` connect `ResearchRepository` to `chat/service.py`, `ResearchMetricsService`, `ChatEvent`, `OpenDeepResearchEngine`, `ResearchRun`, `promotions.py`, `ResearchLifecycleService`, `ResearchNormalizationService`, `WorkspaceRepository`, `FastAPI`, `create_research_run`, `chat_ground_mode`, `workspaces.py`, `research/service.py`, `get_quota_status`, `.__init__`, `GPTResearcherRetriever`, `research/budget.py`, `tasks.py`?**
  _High betweenness centrality (0.211) - this node is a cross-community bridge._
- **Why does `neosis_web_search()` connect `ResearchNormalizationService` to `ResearchRepository`, `get_all_tools`, `utils.py`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Why does `ConversationRepository` connect `ConversationRepository` to `WorkspaceRepository`, `chat/service.py`, `ResearchRepository`, `create_research_run`, `chat_ground_mode`, `workspaces.py`, `ScratchpadRepository`, `ChatEvent`, `ChatService`, `routes/chat.py`, `tasks.py`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `ResearchRepository` (e.g. with `ResearchArtifact` and `ResearchEvent`) actually correct?**
  _`ResearchRepository` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `WorkspaceRepository` (e.g. with `DeletionTombstone` and `OpenNotebookWorkspaceBinding`) actually correct?**
  _`WorkspaceRepository` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `ConversationRepository` (e.g. with `ChatEvent` and `Conversation`) actually correct?**
  _`ConversationRepository` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `ChatService` (e.g. with `cancel_turn()` and `get_turn()`) actually correct?**
  _`ChatService` has 22 INFERRED edges - model-reasoned connections that need verification._