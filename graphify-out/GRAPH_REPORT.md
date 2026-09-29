# Graph Report - NeosisLM  (2026-09-29)

## Corpus Check
- 116 files · ~50,808 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1238 nodes · 3121 edges · 64 communities (57 shown, 6 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 233 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `061519f9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- tasks.py
- ProviderRateLimiter
- OpenNotebookGroundEngine
- ResearchRepository
- ObjectStoreProtocol
- ResearchQuotaService
- utils.py
- EpisodicMemory
- Configuration
- models/__init__.py
- state.py
- routes/scratchpad.py
- chat/context.py
- OpenNotebookClient
- WorkingMemoryState
- ChatEventRepository
- deep_researcher.py
- ResearchSourceResult
- run_research_agent_job
- derivation.py
- get_all_tools
- ConversationRepository
- promotions.py
- ResearchNormalizationService
- core/config.py
- GroundModeOrchestrator
- streamlit_app.py
- routes/chat.py
- ResearchModeOrchestrator
- ResearchMetricsService
- Source
- get_rate_limit_status
- WorkspaceRepository
- repositories/block.py
- chat/service.py
- ground/factory.py
- is_token_limit_exceeded
- UsageTracker
- start_research
- workspaces.py
- telemetry.py
- worker.py
- schemas/promotion.py
- Neo4jAdapter
- research/service.py
- GPTResearcherTool
- get_notes_from_tool_calls
- research/budget.py
- integrations/__init__.py
- ChatService
- UUID
- GPTResearcherRetriever
- stream_job_events
- ._execute_ground_turn
- AcademicRetriever
- upload_file_to_workspace
- schemas/source.py
- .__init__
- .__init__
- .admit_research_run
- .list_retrievers
- S3ObjectStore
- .retrieve

## God Nodes (most connected - your core abstractions)
1. `ResearchRepository` - 71 edges
2. `WorkspaceRepository` - 48 edges
3. `ChatService` - 43 edges
4. `ConversationRepository` - 40 edges
5. `ResearchRun` - 33 edges
6. `OpenNotebookClient` - 29 edges
7. `ResearchArtifact` - 29 edges
8. `ConversationTurn` - 28 edges
9. `Source` - 25 edges
10. `ResearchQuotaService` - 25 edges

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

## Communities (64 total, 6 thin omitted)

### Community 0 - "tasks.py"
Cohesion: 0.11
Nodes (25): BlockRepository, AsyncSession, Validates and sanitizes structured scratchpad content. Strictly prohibits raw…, sanitize_scratchpad_content(), ChunkingService, delete_open_notebook_source_job(), delete_open_notebook_workspace_job(), _get_source_and_snapshot() (+17 more)

### Community 1 - "ProviderRateLimiter"
Cohesion: 0.12
Nodes (13): Admits research run, links to turn, enqueues ARQ job, and returns running turn…, Any, Research Admission Controller to enforce quotas and rate limits before…, Returns the current queue status., ResearchAdmissionController, ProviderRateLimiter, Any, Redis (+5 more)

### Community 2 - "OpenNotebookGroundEngine"
Cohesion: 0.12
Nodes (21): map_citations(), AsyncSession, UUID, Map upstream Open Notebook source IDs back to canonical Neosis source_ids.…, OpenNotebookGroundEngine, Any, AsyncSession, UUID (+13 more)

### Community 3 - "ResearchRepository"
Cohesion: 0.14
Nodes (11): ResearchArtifact, Any, UUID, Creates multiple evidence records in batches with fingerprint deduplication., Retrieves evidence records by their fingerprints., Performs a bulk insert of evidence records., Unified repository for all Research Fabric models. Enforces workspace_id…, Internal helper to ensure a given run_id belongs to the workspace_id. Raises an… (+3 more)

### Community 4 - "ObjectStoreProtocol"
Cohesion: 0.18
Nodes (6): DocumentParser, Any, Downloads a document from Object Storage and parses it using docling. Returns a…, ObjectStoreProtocol, Protocol, UUID

### Community 5 - "ResearchQuotaService"
Cohesion: 0.07
Nodes (31): get_quota_status(), AsyncSession, get, Redis, UUID, Get the current quota status for the user and workspace., create_research_run(), get_queue_status() (+23 more)

### Community 6 - "utils.py"
Cohesion: 0.10
Nodes (29): fetch_tokens(), get_mcp_access_token(), get_tavily_api_key(), get_tokens(), load_mcp_tools(), Any, BaseTool, InjectedToolArg (+21 more)

### Community 7 - "EpisodicMemory"
Cohesion: 0.18
Nodes (10): EpisodicMemory, Base, EpisodicRepository, AsyncSession, UUID, Used by the background worker to detect duplicate compress_episodic_job calls., EpisodicMemoryCreate, EpisodicMemoryResponse (+2 more)

### Community 8 - "Configuration"
Cohesion: 0.15
Nodes (26): Config, Configuration, RunnableConfig, Create a Configuration instance from a RunnableConfig., Pydantic configuration., Main configuration class for the Deep Research agent., clarify_with_user(), compress_research() (+18 more)

### Community 9 - "models/__init__.py"
Cohesion: 0.16
Nodes (19): Base, ResearchEvent, ResearchEvidence, ResearchReport, ResearchRun, ResearchTask, ResearchUsage, InvalidTransitionError (+11 more)

### Community 10 - "state.py"
Cohesion: 0.12
Nodes (21): AgentInputState, AgentState, ClarifyWithUser, ConductResearch, override_reducer(), BaseModel, Graph state definitions and data structures for the Deep Research agent., Call this tool to conduct research on a specific topic. (+13 more)

### Community 11 - "routes/scratchpad.py"
Cohesion: 0.13
Nodes (24): create_scratchpad_entry(), get_scratchpad_entry(), list_scratchpad_entries(), AsyncSession, get, patch, post, UUID (+16 more)

### Community 12 - "chat/context.py"
Cohesion: 0.06
Nodes (51): KnowledgeMemory, Base, KnowledgeRepository, AsyncSession, UUID, KnowledgeMemoryCreate, KnowledgeMemoryResponse, Provenance (+43 more)

### Community 13 - "OpenNotebookClient"
Cohesion: 0.08
Nodes (26): Validates infrastructure, checkpointer, and security invariants during…, validate_production_startup(), CircuitBreaker, CircuitState, OpenNotebookClient, Any, Enum, Check health endpoint of Open Notebook. Returns the parsed JSON response.… (+18 more)

### Community 14 - "WorkingMemoryState"
Cohesion: 0.24
Nodes (9): TypedDict, WorkingMemoryState, EpisodicMemoryService, UUID, Dispatch compression to the background queue., Call LLM with concurrency limits and retries., compress_episodic_job(), Background job: summarise working memory state into an episodic memory record.… (+1 more)

### Community 15 - "ChatEventRepository"
Cohesion: 0.13
Nodes (17): ChatEvent, GroundConversation, Base, Durable event record for real-time turn execution streaming and reconnect…, ChatEventRepository, ChatEventService, format_sse_event(), Any (+9 more)

### Community 16 - "deep_researcher.py"
Cohesion: 0.13
Nodes (17): execute_tool_safely(), Main LangGraph implementation for the Deep Research agent., Safely execute a tool with error handling., Execute tools called by the researcher, including search tools and strategic…, researcher_tools(), System prompts and prompt templates for the Deep Research agent., TypedDict, State for the supervisor that manages research tasks. (+9 more)

### Community 17 - "ResearchSourceResult"
Cohesion: 0.21
Nodes (12): ABC, BaseRetriever, Execute retrieval for a given query and return normalized ResearchSourceResult…, ResearchRetrievalPolicy, ResearchSourceResult, MCPRetriever, Any, Register a retriever instance under a name. (+4 more)

### Community 18 - "run_research_agent_job"
Cohesion: 0.06
Nodes (37): BudgetEnforcingCallbackHandler, Intercepts LLM results to track usage and enforce budgets., Track token usage after an LLM call completes., Any, UUID, Stream execution events from the research engine. Args: run_id: The canonical…, Trigger cooperative cancellation of the running execution., Abstract interface for all research engines in Neosis. (+29 more)

### Community 19 - "derivation.py"
Cohesion: 0.07
Nodes (32): DocumentBlock, Base, ProvenanceRef, CrossWorkspaceBoundaryError, DerivationService, Any, AsyncSession, Exception (+24 more)

### Community 20 - "get_all_tools"
Cohesion: 0.14
Nodes (16): MCPConfig, BaseModel, Enum, Configuration management for the Open Deep Research system., Enumeration of available search API providers., Configuration for Model Context Protocol (MCP) servers., SearchAPI, get_all_tools() (+8 more)

### Community 21 - "ConversationRepository"
Cohesion: 0.19
Nodes (10): Conversation, ConversationTurn, Canonical conversational container within a Neosis workspace. Mode-agnostic:…, Canonical turn record representing a single prompt-response interaction within…, ConversationRepository, Any, AsyncSession, datetime (+2 more)

### Community 22 - "promotions.py"
Cohesion: 0.11
Nodes (29): accept_promotion(), get_promotion(), _get_promotion_service(), list_promotions(), AsyncSession, get, post, Redis (+21 more)

### Community 23 - "ResearchNormalizationService"
Cohesion: 0.15
Nodes (12): GPTResearcherInput, BaseModel, neosis_web_search(), InjectedToolArg, RunnableConfig, tool, Fetch search results, immediately persist them to Neosis DB, and return…, Normalizes a URL by parsing it, lowercasing the scheme and netloc, and sorting… (+4 more)

### Community 24 - "core/config.py"
Cohesion: 0.14
Nodes (14): Settings, Shared HTTP client for Open Notebook integration., get_checkpointer(), process_memory(), Any, Validates checkpointer configuration on startup. In production, durable…, Returns the checkpointer instance appropriate for the current environment., validate_checkpointer() (+6 more)

### Community 25 - "GroundModeOrchestrator"
Cohesion: 0.13
Nodes (12): GroundModeOrchestrator, GroundModeState, Any, deprecated, TypedDict, UUID, Deprecated: Use OpenNotebookGroundEngine instead. This orchestrator handles the…, ContextBundle (+4 more)

### Community 26 - "streamlit_app.py"
Cohesion: 0.24
Nodes (7): Executes a search query and returns the results formatted as markdown., WebSearchTool, create_db_workspace(), get_litellm_gateway(), project_graph_to_neo4j(), run_agent(), run_ground_mode()

### Community 27 - "routes/chat.py"
Cohesion: 0.15
Nodes (33): cancel_turn(), create_conversation(), get_chat_service(), get_conversation(), get_conversation_repository(), get_turn(), get_workspace_repository(), list_conversations() (+25 more)

### Community 28 - "ResearchModeOrchestrator"
Cohesion: 0.21
Nodes (8): Any, BaseModel, deprecated, TypedDict, UUID, ResearchContext, ResearchModeOrchestrator, ResearchState

### Community 29 - "ResearchMetricsService"
Cohesion: 0.12
Nodes (15): get_workspace_metrics(), AsyncSession, get, UUID, Get observability metrics for a workspace., Any, datetime, UUID (+7 more)

### Community 30 - "Source"
Cohesion: 0.12
Nodes (16): Base, Source, SourceSnapshot, AsyncSession, UUID, SourceRepository, UUID, WorkspaceExportService (+8 more)

### Community 31 - "get_rate_limit_status"
Cohesion: 0.40
Nodes (5): get_rate_limit_status(), get, Redis, UUID, Get the current rate limit status for the user.

### Community 32 - "WorkspaceRepository"
Cohesion: 0.24
Nodes (7): Base, Workspace, WorkspaceCommit, AsyncSession, UUID, Atomically rolls back the workspace to a target commit under a row lock (FOR…, WorkspaceRepository

### Community 33 - "repositories/block.py"
Cohesion: 0.25
Nodes (6): UUID, DocumentBlockCreate, DocumentBlockResponse, BaseModel, Any, Takes the raw dictionary output from Docling and converts it into…

### Community 34 - "chat/service.py"
Cohesion: 0.14
Nodes (18): get_arq_redis(), Request, Dependency to get the arq Redis pool. We lazily initialize the pool and attach…, get_current_user(), UUID, get_rate_limit_key(), Request, Rate limit by user ID if authenticated, else fallback to IP. (+10 more)

### Community 35 - "ground/factory.py"
Cohesion: 0.13
Nodes (16): get_embed_gateway(), get_llm_gateway(), mock_embed_call(), mock_llm_call(), get_hybrid_retrieval_service(), get_ground_engine(), get_hybrid_retrieval_service(), Any (+8 more)

### Community 36 - "is_token_limit_exceeded"
Cohesion: 0.27
Nodes (10): _check_anthropic_token_limit(), _check_gemini_token_limit(), _check_openai_token_limit(), is_token_limit_exceeded(), McpError, Exception, Determine if an exception indicates a token/context limit was exceeded. Args:…, Check if exception indicates OpenAI token limit exceeded. (+2 more)

### Community 37 - "UsageTracker"
Cohesion: 0.21
Nodes (4): Exception, Raised when an execution exceeds its allocated budget., ResearchBudgetExceeded, UsageTracker

### Community 38 - "start_research"
Cohesion: 0.14
Nodes (23): ask_ground_mode(), ask_ground_mode_stream(), chat_ground_mode(), create_workspace_commit(), get_knowledge_repository(), get_memory_router(), get_quota(), get_research_repository() (+15 more)

### Community 39 - "workspaces.py"
Cohesion: 0.25
Nodes (13): create_workspace(), patch, rollback_workspace(), update_workspace(), FileUploadResponse, BaseModel, BaseModel, ResearchRequest (+5 more)

### Community 40 - "telemetry.py"
Cohesion: 0.28
Nodes (7): Sanitizes sensitive tokens, passwords, and API keys from log strings., Logging filter that intercepts log records and redacts any credentials, bearer…, Sets up OpenTelemetry and attaches secret sanitization to the logging root., sanitize_log_message(), SecretSanitizingFilter, setup_telemetry(), LogRecord

### Community 41 - "worker.py"
Cohesion: 0.25
Nodes (7): get_worker_pool_status(), Any, get, Get the current status of worker pools and queues., Returns the configuration for a specific queue., arq worker settings class. Discovered by: python -m arq…, WorkerSettings

### Community 42 - "schemas/promotion.py"
Cohesion: 0.17
Nodes (14): ClaimCandidatePayload, DerivationExpression, FindingCandidatePayload, GraphCandidatePayload, HypothesisCandidatePayload, MemoryCandidatePayload, PromotionCandidateResponse, PromotionReviewRequest (+6 more)

### Community 43 - "Neo4jAdapter"
Cohesion: 0.17
Nodes (5): GraphStore, Neo4jAdapter, Any, Abstract base class for our operational Knowledge Graph. This hides the…, AsyncDriver

### Community 44 - "research/service.py"
Cohesion: 0.27
Nodes (12): GraphRepository, UUID, Projects an OutputGraph into Neo4j. Nodes get labels: OutputNode, plus their…, OutputGraph, OutputGraphEdge, OutputGraphNode, ProvenanceBundle, BaseModel (+4 more)

### Community 45 - "GPTResearcherTool"
Cohesion: 0.29
Nodes (5): GPTResearcherTool, Any, BaseTool, RunnableConfig, Use the tool asynchronously.

### Community 46 - "get_notes_from_tool_calls"
Cohesion: 0.40
Nodes (5): get_notes_from_tool_calls(), Extract notes from tool call messages., Truncate message history by removing up to the last AI message. This is useful…, remove_up_to_last_ai_message(), MessageLikeRepresentation

### Community 47 - "research/budget.py"
Cohesion: 0.22
Nodes (6): Any, UUID, Research-specific budget policy to enforce cost and usage limits., Check if the budget for a research run has been exceeded. Returns True if the…, Returns the current budget status., ResearchBudgetPolicy

### Community 49 - "ChatService"
Cohesion: 0.12
Nodes (15): Dual in-process and Redis Pub/Sub event broker. Provides sub/pub abstraction…, TurnEventBroker, ChatService, UUID, Submits a turn and returns an async generator streaming its events via SSE.…, Yields standard SSE formatted events: event: <type>\ndata: <json_payload>\n\n…, Executes Ground turn in background with independent DB session. Delegates…, Coordinates turn submission, mode dispatching (Ground vs Research),… (+7 more)

### Community 50 - "UUID"
Cohesion: 0.36
Nodes (8): delete_workspace(), get_projection_status(), get_source_status(), get_workspace(), get_workspace_output_graph(), get, UUID, delete

### Community 52 - "GPTResearcherRetriever"
Cohesion: 0.47
Nodes (3): GPTResearcherRetriever, Any, Creates a mock LLM provider for GPTResearcher that uses Neosis's llm_gateway.…

### Community 53 - "stream_job_events"
Cohesion: 0.40
Nodes (5): ArqRedis, get, Request, Streams Server-Sent Events (SSE) from the Redis Pub/Sub channel for a given job., stream_job_events()

### Community 54 - "._execute_ground_turn"
Cohesion: 0.40
Nodes (3): Any, Executes a Ground mode turn against Open Notebook with 1-time transparent 409…, Submits and executes a conversation turn synchronously (or 202 for research).…

### Community 56 - "upload_file_to_workspace"
Cohesion: 0.50
Nodes (4): Request, upload_file_to_workspace(), limit, UploadFile

### Community 57 - "schemas/source.py"
Cohesion: 0.67
Nodes (3): BaseModel, SourceResponse, SourceSnapshotResponse

### Community 62 - "S3ObjectStore"
Cohesion: 0.18
Nodes (7): AsyncSession, get_object_store(), Request, Dependency to provide shared S3ObjectStore from app state., S3ObjectStore, export_workspace_job(), Background job: Executes the workspace export using WorkspaceExportService and…

### Community 63 - ".retrieve"
Cohesion: 0.40
Nodes (3): Any, Get a registered retriever by name., Execute retrieval using the specified retriever or policy defaults, enforcing…

## Knowledge Gaps
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ResearchRepository` connect `ResearchRepository` to `tasks.py`, `ProviderRateLimiter`, `chat/service.py`, `ResearchQuotaService`, `start_research`, `workspaces.py`, `models/__init__.py`, `research/service.py`, `GPTResearcherTool`, `chat/context.py`, `research/budget.py`, `run_research_agent_job`, `derivation.py`, `promotions.py`, `ResearchNormalizationService`, `.__init__`, `.__init__`, `ResearchMetricsService`?**
  _High betweenness centrality (0.249) - this node is a cross-community bridge._
- **Why does `neosis_web_search()` connect `ResearchNormalizationService` to `ResearchRepository`, `get_all_tools`, `utils.py`?**
  _High betweenness centrality (0.138) - this node is a cross-community bridge._
- **Why does `ResearchRun` connect `models/__init__.py` to `tasks.py`, `ProviderRateLimiter`, `chat/service.py`, `ResearchRepository`, `ResearchQuotaService`, `start_research`, `workspaces.py`, `chat/context.py`, `research/service.py`, `ChatService`, `run_research_agent_job`, `derivation.py`, `promotions.py`, `.admit_research_run`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `ResearchRepository` (e.g. with `ResearchArtifact` and `ResearchEvent`) actually correct?**
  _`ResearchRepository` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `WorkspaceRepository` (e.g. with `DeletionTombstone` and `OpenNotebookWorkspaceBinding`) actually correct?**
  _`WorkspaceRepository` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `ChatService` (e.g. with `cancel_turn()` and `get_turn()`) actually correct?**
  _`ChatService` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `ConversationRepository` (e.g. with `ChatEvent` and `Conversation`) actually correct?**
  _`ConversationRepository` has 3 INFERRED edges - model-reasoned connections that need verification._