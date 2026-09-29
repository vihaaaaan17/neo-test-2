# Graph Report - NeosisLM  (2026-09-29)

## Corpus Check
- 116 files · ~53,127 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1261 nodes · 3188 edges · 58 communities (54 shown, 3 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 242 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `55f85537`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- tasks.py
- ProviderRateLimiter
- OpenNotebookGroundEngine
- ResearchRepository
- ResearchMetricsService
- .handle_quota_violation
- tavily_search
- WorkingMemoryState
- Configuration
- research/promotion.py
- state.py
- routes/scratchpad.py
- chat/context.py
- main.py
- OpenNotebookClient
- ChatEvent
- deep_researcher.py
- UsageTracker
- OpenDeepResearchEngine
- verification.py
- get_all_tools
- ConversationRepository
- promotions.py
- chat/service.py
- ResearchArtifact
- streamlit_app.py
- export.py
- routes/chat.py
- run_research_agent_job
- Neo4jAdapter
- PromotionError
- Source
- WorkspaceRepository
- schemas/promotion.py
- FastAPI
- GroundModeOrchestrator
- utils.py
- create_research_run
- workspaces.py
- schemas/workspace.py
- telemetry.py
- settings.py
- ProvenanceRef
- configuration.py
- research/service.py
- get_quota_status
- get_notes_from_tool_calls
- load_mcp_tools
- integrations/__init__.py
- ChatService
- UUID
- get_chat_service
- stream_job_events
- CircuitBreaker
- .__init__
- schemas/source.py
- ObjectStoreProtocol

## God Nodes (most connected - your core abstractions)
1. `ResearchRepository` - 72 edges
2. `WorkspaceRepository` - 48 edges
3. `ConversationRepository` - 42 edges
4. `ChatService` - 42 edges
5. `ResearchRun` - 32 edges
6. `ConversationTurn` - 30 edges
7. `OpenNotebookClient` - 29 edges
8. `ResearchArtifact` - 29 edges
9. `Source` - 26 edges
10. `ResearchQuotaService` - 25 edges

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

## Communities (58 total, 3 thin omitted)

### Community 0 - "tasks.py"
Cohesion: 0.14
Nodes (16): BlockRepository, AsyncSession, UUID, DocumentBlockCreate, DocumentBlockResponse, BaseModel, ChunkingService, Any (+8 more)

### Community 1 - "ProviderRateLimiter"
Cohesion: 0.10
Nodes (15): Submits a turn and returns an async generator streaming its events via SSE.…, Any, UUID, Research Admission Controller to enforce quotas and rate limits before…, Admits a new research run after checking quotas and rate limits., Returns the current queue status., ResearchAdmissionController, ProviderRateLimiter (+7 more)

### Community 2 - "OpenNotebookGroundEngine"
Cohesion: 0.12
Nodes (23): map_canonical_sources_to_upstream(), map_citations(), AsyncSession, UUID, Map upstream Open Notebook source IDs back to canonical Neosis source_ids.…, Map canonical Neosis source_ids (UUIDs) to upstream Open Notebook source IDs…, OpenNotebookGroundEngine, Any (+15 more)

### Community 3 - "ResearchRepository"
Cohesion: 0.13
Nodes (12): ResearchEvidence, ResearchUsage, Any, UUID, Creates multiple evidence records in batches with fingerprint deduplication., Retrieves evidence records by their fingerprints., Performs a bulk insert of evidence records., Unified repository for all Research Fabric models. Enforces workspace_id… (+4 more)

### Community 4 - "ResearchMetricsService"
Cohesion: 0.13
Nodes (15): get_workspace_metrics(), AsyncSession, get, UUID, Get observability metrics for a workspace., Any, datetime, UUID (+7 more)

### Community 5 - ".handle_quota_violation"
Cohesion: 0.11
Nodes (12): Any, UUID, Returns the current user concurrency status., Returns the current workspace concurrency status., Returns the current global concurrency status., Enforces the user concurrency quota. Returns ACCEPTED or QUOTA_EXCEEDED., Enforces the workspace concurrency quota. Returns ACCEPTED or QUOTA_EXCEEDED., Enforces the global concurrency limit. Returns ACCEPTED or QUOTA_EXCEEDED. (+4 more)

### Community 6 - "tavily_search"
Cohesion: 0.13
Nodes (20): fetch_tokens(), get_mcp_access_token(), get_tavily_api_key(), get_tokens(), Any, InjectedToolArg, RunnableConfig, Execute multiple Tavily search queries asynchronously. Args: search_queries:… (+12 more)

### Community 7 - "WorkingMemoryState"
Cohesion: 0.09
Nodes (25): EpisodicMemory, Base, EpisodicRepository, AsyncSession, UUID, Used by the background worker to detect duplicate compress_episodic_job calls., EpisodicMemoryCreate, EpisodicMemoryResponse (+17 more)

### Community 8 - "Configuration"
Cohesion: 0.15
Nodes (26): Config, Configuration, RunnableConfig, Create a Configuration instance from a RunnableConfig., Pydantic configuration., Main configuration class for the Deep Research agent., clarify_with_user(), compress_research() (+18 more)

### Community 9 - "research/promotion.py"
Cohesion: 0.16
Nodes (14): KnowledgeMemory, Base, KnowledgeRepository, AsyncSession, UUID, KnowledgeMemoryCreate, KnowledgeMemoryResponse, Provenance (+6 more)

### Community 10 - "state.py"
Cohesion: 0.12
Nodes (21): AgentInputState, AgentState, ClarifyWithUser, ConductResearch, override_reducer(), BaseModel, Graph state definitions and data structures for the Deep Research agent., Call this tool to conduct research on a specific topic. (+13 more)

### Community 11 - "routes/scratchpad.py"
Cohesion: 0.13
Nodes (24): create_scratchpad_entry(), get_scratchpad_entry(), list_scratchpad_entries(), AsyncSession, get, patch, post, UUID (+16 more)

### Community 12 - "chat/context.py"
Cohesion: 0.08
Nodes (38): build_ground_context(), build_research_context(), _ContextCandidate, ContextItemManifest, estimate_tokens(), EvictedItemManifest, GroundContext, Any (+30 more)

### Community 13 - "main.py"
Cohesion: 0.09
Nodes (25): Settings, Validates infrastructure, checkpointer, and security invariants during…, validate_production_startup(), CircuitState, Enum, get_open_notebook_base_url(), get_open_notebook_timeout(), is_open_notebook_enabled() (+17 more)

### Community 14 - "OpenNotebookClient"
Cohesion: 0.25
Nodes (8): OpenNotebookClient, Any, Check health endpoint of Open Notebook. Returns the parsed JSON response.…, Streams the ask response, yielding standardized SSE events., Executes a chat message. Returns the final answer text and the updated…, Streams chat events and incremental tokens for a conversation session. Yields…, HTTP client for communicating with the Open Notebook API. Establishes the…, with_error_translation()

### Community 15 - "ChatEvent"
Cohesion: 0.11
Nodes (20): ChatEvent, GroundConversation, Base, Durable event record for real-time turn execution streaming and reconnect…, datetime, ChatEventRepository, ChatEventService, format_sse_event() (+12 more)

### Community 16 - "deep_researcher.py"
Cohesion: 0.15
Nodes (15): execute_tool_safely(), Main LangGraph implementation for the Deep Research agent., Safely execute a tool with error handling., Execute tools called by the researcher, including search tools and strategic…, researcher_tools(), System prompts and prompt templates for the Deep Research agent., TypedDict, State for the supervisor that manages research tasks. (+7 more)

### Community 17 - "UsageTracker"
Cohesion: 0.05
Nodes (40): ABC, UsageTracker, GPTResearcherInput, GPTResearcherTool, Any, BaseModel, BaseTool, RunnableConfig (+32 more)

### Community 18 - "OpenDeepResearchEngine"
Cohesion: 0.05
Nodes (38): BudgetEnforcingCallbackHandler, Exception, Raised when an execution exceeds its allocated budget., Intercepts LLM results to track usage and enforce budgets., Track token usage after an LLM call completes., ResearchBudgetExceeded, Any, UUID (+30 more)

### Community 19 - "verification.py"
Cohesion: 0.16
Nodes (16): ArithmeticVerificationError, DeterministicArithmeticVerifier, _pct_change(), Any, BaseModel, Exception, Raised when an expression violates safety rules, resource limits, or arithmetic…, Evaluates an arithmetic expression and compares the computed value against an… (+8 more)

### Community 20 - "get_all_tools"
Cohesion: 0.15
Nodes (14): neosis_web_search(), InjectedToolArg, RunnableConfig, tool, Fetch search results, immediately persist them to Neosis DB, and return…, get_all_tools(), get_config_value(), get_search_tool() (+6 more)

### Community 21 - "ConversationRepository"
Cohesion: 0.15
Nodes (13): Conversation, ConversationTurn, Canonical conversational container within a Neosis workspace. Mode-agnostic:…, Canonical turn record representing a single prompt-response interaction within…, ConversationRepository, Any, AsyncSession, UUID (+5 more)

### Community 22 - "promotions.py"
Cohesion: 0.28
Nodes (15): accept_promotion(), get_promotion(), _get_promotion_service(), list_promotions(), AsyncSession, get, post, Redis (+7 more)

### Community 23 - "chat/service.py"
Cohesion: 0.26
Nodes (10): get_db(), Base, ResearchEvent, ResearchReport, ResearchRun, ResearchTask, BaseModel, ResearchRunResponse (+2 more)

### Community 24 - "ResearchArtifact"
Cohesion: 0.19
Nodes (14): ResearchArtifact, InvalidLifecycleTransitionError, PromotionService, Any, UUID, Retrieves a candidate artifact within the workspace boundary. When…, Atomically accepts a candidate artifact: 1. Verifies workspace access and…, Durably rejects a candidate artifact: - Sets promotion_status = 'rejected' -… (+6 more)

### Community 25 - "streamlit_app.py"
Cohesion: 0.13
Nodes (15): Any, BaseModel, deprecated, TypedDict, UUID, ResearchContext, ResearchModeOrchestrator, ResearchState (+7 more)

### Community 26 - "export.py"
Cohesion: 0.19
Nodes (8): DocumentBlock, Base, AsyncSession, UUID, WorkspaceExportService, S3ObjectStore, export_workspace_job(), Background job: Executes the workspace export using WorkspaceExportService and…

### Community 27 - "routes/chat.py"
Cohesion: 0.16
Nodes (29): cancel_turn(), create_conversation(), get_conversation(), get_turn(), list_conversations(), list_turn_events(), list_turns(), get (+21 more)

### Community 28 - "run_research_agent_job"
Cohesion: 0.18
Nodes (11): InvalidTransitionError, Any, datetime, Exception, UUID, Transition a ResearchTask to a new status. Emits a ResearchEvent., Acts as the sole authority for state transitions of ResearchRun and…, Transition a ResearchRun to a new status. Emits a ResearchEvent. (+3 more)

### Community 29 - "Neo4jAdapter"
Cohesion: 0.17
Nodes (5): GraphStore, Neo4jAdapter, Any, Abstract base class for our operational Knowledge Graph. This hides the…, AsyncDriver

### Community 30 - "PromotionError"
Cohesion: 0.13
Nodes (13): CandidateNotFoundError, InvalidCandidateTypeError, InvalidPayloadError, PromotionError, AsyncSession, Exception, Redis, Base exception for candidate promotion operations. (+5 more)

### Community 31 - "Source"
Cohesion: 0.09
Nodes (22): Base, Source, SourceSnapshot, AsyncSession, UUID, SourceRepository, ArqRedis, get_quota_service() (+14 more)

### Community 32 - "WorkspaceRepository"
Cohesion: 0.21
Nodes (10): patch, update_workspace(), Base, Workspace, WorkspaceCommit, AsyncSession, UUID, Atomically rolls back the workspace to a target commit under a row lock (FOR… (+2 more)

### Community 33 - "schemas/promotion.py"
Cohesion: 0.27
Nodes (10): ClaimCandidatePayload, DerivationExpression, FindingCandidatePayload, GraphCandidatePayload, HypothesisCandidatePayload, MemoryCandidatePayload, PromotionCandidateResponse, PromotionReviewRequest (+2 more)

### Community 34 - "FastAPI"
Cohesion: 0.14
Nodes (15): get_arq_redis(), Request, Dependency to get the arq Redis pool. We lazily initialize the pool and attach…, get_current_user(), UUID, get_rate_limit_key(), Request, Rate limit by user ID if authenticated, else fallback to IP. (+7 more)

### Community 35 - "GroundModeOrchestrator"
Cohesion: 0.07
Nodes (28): get_embed_gateway(), get_llm_gateway(), mock_embed_call(), mock_llm_call(), get_hybrid_retrieval_service(), GroundModeOrchestrator, GroundModeState, Any (+20 more)

### Community 36 - "utils.py"
Cohesion: 0.18
Nodes (15): _check_anthropic_token_limit(), _check_gemini_token_limit(), _check_openai_token_limit(), get_model_token_limit(), is_token_limit_exceeded(), McpError, Exception, Utility functions and helpers for the Deep Research agent. (+7 more)

### Community 37 - "create_research_run"
Cohesion: 0.24
Nodes (11): create_research_run(), get_queue_status(), Any, AsyncSession, get, post, Redis, Response (+3 more)

### Community 38 - "workspaces.py"
Cohesion: 0.15
Nodes (26): ask_ground_mode(), ask_ground_mode_stream(), chat_ground_mode(), create_workspace_commit(), get_knowledge_repository(), get_memory_router(), get_quota(), get_research_repository() (+18 more)

### Community 39 - "schemas/workspace.py"
Cohesion: 0.39
Nodes (7): create_workspace(), BaseModel, ResearchRequest, RollbackRequest, WorkspaceCommitResponse, WorkspaceCreate, WorkspaceResponse

### Community 40 - "telemetry.py"
Cohesion: 0.28
Nodes (7): Sanitizes sensitive tokens, passwords, and API keys from log strings., Logging filter that intercepts log records and redacts any credentials, bearer…, Sets up OpenTelemetry and attaches secret sanitization to the logging root., sanitize_log_message(), SecretSanitizingFilter, setup_telemetry(), LogRecord

### Community 41 - "settings.py"
Cohesion: 0.09
Nodes (25): get_worker_pool_status(), Any, get, Get the current status of worker pools and queues., arq WorkerSettings — defines the worker process configuration. Run the worker…, Returns the configuration for a specific queue., Runs once when the worker process shuts down., arq worker settings class. Discovered by: python -m arq… (+17 more)

### Community 42 - "ProvenanceRef"
Cohesion: 0.31
Nodes (6): ProvenanceRef, Any, UUID, Validates provenance references, runs deterministic verification if derivations…, Builds a typed ProvenanceBundle from a list of ProvenanceRef items and optional…, Strictly validates that every reference in the provenance bundle exists and…

### Community 43 - "configuration.py"
Cohesion: 0.29
Nodes (7): MCPConfig, BaseModel, Enum, Configuration management for the Open Deep Research system., Enumeration of available search API providers., Configuration for Model Context Protocol (MCP) servers., SearchAPI

### Community 44 - "research/service.py"
Cohesion: 0.21
Nodes (15): GraphRepository, UUID, Projects an OutputGraph into Neo4j. Nodes get labels: OutputNode, plus their…, OutputGraph, OutputGraphEdge, OutputGraphNode, ProvenanceBundle, BaseModel (+7 more)

### Community 45 - "get_quota_status"
Cohesion: 0.33
Nodes (6): get_quota_status(), AsyncSession, get, Redis, UUID, Get the current quota status for the user and workspace.

### Community 46 - "get_notes_from_tool_calls"
Cohesion: 0.40
Nodes (5): get_notes_from_tool_calls(), Extract notes from tool call messages., Truncate message history by removing up to the last AI message. This is useful…, remove_up_to_last_ai_message(), MessageLikeRepresentation

### Community 47 - "load_mcp_tools"
Cohesion: 0.33
Nodes (6): load_mcp_tools(), BaseTool, Wrap MCP tool with comprehensive authentication and error handling. Args: tool:…, Load and configure MCP (Model Context Protocol) tools with authentication.…, wrap_mcp_authenticate_tool(), StructuredTool

### Community 49 - "ChatService"
Cohesion: 0.09
Nodes (18): Dual in-process and Redis Pub/Sub event broker. Provides sub/pub abstraction…, TurnEventBroker, ChatService, Any, UUID, Unified SSE generator — supports reconnect replay via Last-Event-ID. Protocol:…, Coordinates turn submission, mode dispatching (Ground vs Research),…, Executes Ground turn in background with independent DB session. Delegates… (+10 more)

### Community 50 - "UUID"
Cohesion: 0.21
Nodes (12): delete_workspace(), get_projection_status(), get_source_status(), get_workspace(), get_workspace_output_graph(), get, Request, UUID (+4 more)

### Community 52 - "get_chat_service"
Cohesion: 0.40
Nodes (5): get_chat_service(), get_conversation_repository(), get_workspace_repository(), ArqRedis, AsyncSession

### Community 53 - "stream_job_events"
Cohesion: 0.40
Nodes (5): ArqRedis, get, Request, Streams Server-Sent Events (SSE) from the Redis Pub/Sub channel for a given job., stream_job_events()

### Community 57 - "schemas/source.py"
Cohesion: 0.67
Nodes (3): BaseModel, SourceResponse, SourceSnapshotResponse

### Community 62 - "ObjectStoreProtocol"
Cohesion: 0.15
Nodes (9): DocumentParser, Any, Downloads a document from Object Storage and parses it using docling. Returns a…, get_object_store(), ObjectStoreProtocol, Protocol, Request, UUID (+1 more)

## Knowledge Gaps
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ResearchRepository` connect `ResearchRepository` to `tasks.py`, `ProviderRateLimiter`, `ResearchMetricsService`, `research/promotion.py`, `ChatEvent`, `UsageTracker`, `OpenDeepResearchEngine`, `get_all_tools`, `promotions.py`, `chat/service.py`, `ResearchArtifact`, `run_research_agent_job`, `PromotionError`, `WorkspaceRepository`, `create_research_run`, `workspaces.py`, `research/service.py`, `get_quota_status`, `.__init__`?**
  _High betweenness centrality (0.245) - this node is a cross-community bridge._
- **Why does `neosis_web_search()` connect `get_all_tools` to `UsageTracker`, `ResearchRepository`, `utils.py`, `chat/service.py`?**
  _High betweenness centrality (0.140) - this node is a cross-community bridge._
- **Why does `ConversationRepository` connect `ConversationRepository` to `tasks.py`, `create_research_run`, `workspaces.py`, `routes/scratchpad.py`, `ChatEvent`, `ChatService`, `get_chat_service`, `chat/service.py`, `routes/chat.py`, `run_research_agent_job`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `ResearchRepository` (e.g. with `ResearchArtifact` and `ResearchEvent`) actually correct?**
  _`ResearchRepository` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `WorkspaceRepository` (e.g. with `DeletionTombstone` and `OpenNotebookWorkspaceBinding`) actually correct?**
  _`WorkspaceRepository` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `ConversationRepository` (e.g. with `ChatEvent` and `Conversation`) actually correct?**
  _`ConversationRepository` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `ChatService` (e.g. with `cancel_turn()` and `get_turn()`) actually correct?**
  _`ChatService` has 22 INFERRED edges - model-reasoned connections that need verification._