# Graph Report - NeosisLM  (2026-09-30)

## Corpus Check
- 119 files · ~58,908 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1317 nodes · 3344 edges · 53 communities (51 shown, 1 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 264 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1f833b04`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ValueError
- ProviderRateLimiter
- OpenNotebookGroundEngine
- ResearchRepository
- tasks.py
- ResearchQuotaService
- utils.py
- WorkingMemoryState
- Configuration
- research/promotion.py
- state.py
- ScratchpadRepository
- chat/context.py
- client.py
- OpenNotebookClient
- .record_and_publish
- deep_researcher.py
- BaseRetriever
- OpenDeepResearchEngine
- derivation.py
- get_all_tools
- ConversationRepository
- ground/factory.py
- policy.py
- promotions.py
- GraphStore
- MemoryRouter
- routes/chat.py
- workspaces.py
- ResearchNormalizationService
- WorkspaceRepository
- QuotaService
- routes/research.py
- ResearchModeOrchestrator
- is_token_limit_exceeded
- create_research_run
- chat_ground_mode
- UUID
- telemetry.py
- UsageTracker
- research/service.py
- get_notes_from_tool_calls
- integrations/__init__.py
- chat/service.py
- stream_job_events
- GPTResearcherRetriever
- research/budget.py
- ResearchSourceResult
- NeosisAPIClient
- export.py
- .retrieve
- schemas/source.py

## God Nodes (most connected - your core abstractions)
1. `ResearchRepository` - 72 edges
2. `WorkspaceRepository` - 48 edges
3. `ConversationRepository` - 42 edges
4. `ChatService` - 42 edges
5. `ResearchRun` - 37 edges
6. `NeosisAPIClient` - 36 edges
7. `ConversationTurn` - 32 edges
8. `OpenNotebookClient` - 29 edges
9. `ResearchArtifact` - 29 edges
10. `Source` - 27 edges

## Surprising Connections (you probably didn't know these)
- `main()` --uses--> `ConversationTurn`  [INFERRED]
  scratch/check_err.py → app/models/conversation.py
- `main()` --uses--> `ChatEvent`  [INFERRED]
  scratch/check_err.py → app/models/conversation.py
- `main()` --uses--> `ResearchEvent`  [INFERRED]
  scratch/check_err.py → app/models/research.py
- `submit_turn()` --uses--> `TurnCreate`  [INFERRED]
  app/api/routes/chat.py → app/schemas/chat.py
- `submit_turn()` --uses--> `ChatService`  [INFERRED]
  app/api/routes/chat.py → app/services/chat/service.py

## Import Cycles
- None detected.

## Communities (53 total, 1 thin omitted)

### Community 0 - "ValueError"
Cohesion: 0.06
Nodes (25): BlockRepository, AsyncSession, UUID, DocumentBlockCreate, DocumentBlockResponse, BaseModel, ChunkingService, Any (+17 more)

### Community 1 - "ProviderRateLimiter"
Cohesion: 0.09
Nodes (19): get_rate_limit_status(), get, Redis, UUID, Get the current rate limit status for the user., Any, UUID, Research Admission Controller to enforce quotas and rate limits before… (+11 more)

### Community 2 - "OpenNotebookGroundEngine"
Cohesion: 0.12
Nodes (23): map_canonical_sources_to_upstream(), map_citations(), AsyncSession, UUID, Map upstream Open Notebook source IDs back to canonical Neosis source_ids.…, Map canonical Neosis source_ids (UUIDs) to upstream Open Notebook source IDs…, OpenNotebookGroundEngine, Any (+15 more)

### Community 3 - "ResearchRepository"
Cohesion: 0.06
Nodes (47): get_workspace_metrics(), AsyncSession, get, UUID, Get observability metrics for a workspace., Base, ResearchArtifact, ResearchEvent (+39 more)

### Community 4 - "tasks.py"
Cohesion: 0.14
Nodes (16): Base, Source, SourceSnapshot, UUID, Any, AsyncSession, UUID, Attempts to resolve an external citation to an existing workspace Source.… (+8 more)

### Community 5 - "ResearchQuotaService"
Cohesion: 0.09
Nodes (20): get_quota_status(), AsyncSession, get, Redis, UUID, Get the current quota status for the user and workspace., Any, UUID (+12 more)

### Community 6 - "utils.py"
Cohesion: 0.10
Nodes (29): fetch_tokens(), get_mcp_access_token(), get_tavily_api_key(), get_tokens(), load_mcp_tools(), Any, BaseTool, InjectedToolArg (+21 more)

### Community 7 - "WorkingMemoryState"
Cohesion: 0.08
Nodes (29): Validates infrastructure, checkpointer, and security invariants during…, validate_production_startup(), EpisodicMemory, Base, EpisodicRepository, AsyncSession, UUID, Used by the background worker to detect duplicate compress_episodic_job calls. (+21 more)

### Community 8 - "Configuration"
Cohesion: 0.15
Nodes (26): Config, Configuration, RunnableConfig, Create a Configuration instance from a RunnableConfig., Pydantic configuration., Main configuration class for the Deep Research agent., clarify_with_user(), compress_research() (+18 more)

### Community 9 - "research/promotion.py"
Cohesion: 0.16
Nodes (14): KnowledgeMemory, Base, KnowledgeRepository, AsyncSession, UUID, KnowledgeMemoryCreate, KnowledgeMemoryResponse, Provenance (+6 more)

### Community 10 - "state.py"
Cohesion: 0.12
Nodes (21): AgentInputState, AgentState, ClarifyWithUser, ConductResearch, override_reducer(), BaseModel, Graph state definitions and data structures for the Deep Research agent., Call this tool to conduct research on a specific topic. (+13 more)

### Community 11 - "ScratchpadRepository"
Cohesion: 0.13
Nodes (26): create_scratchpad_entry(), get_scratchpad_entry(), list_scratchpad_entries(), AsyncSession, get, patch, post, UUID (+18 more)

### Community 12 - "chat/context.py"
Cohesion: 0.18
Nodes (20): build_ground_context(), build_research_context(), _ContextCandidate, ContextItemManifest, estimate_tokens(), EvictedItemManifest, GroundContext, Any (+12 more)

### Community 13 - "client.py"
Cohesion: 0.12
Nodes (13): CircuitBreaker, CircuitState, Enum, get_open_notebook_base_url(), is_open_notebook_enabled(), Check if the Open Notebook Ground Engine is enabled., Get the base URL for the Open Notebook API., check_open_notebook_health() (+5 more)

### Community 14 - "OpenNotebookClient"
Cohesion: 0.08
Nodes (29): get_worker_pool_status(), Any, get, Get the current status of worker pools and queues., OpenNotebookClient, Any, Check health endpoint of Open Notebook. Returns the parsed JSON response.…, Streams the ask response, yielding standardized SSE events. (+21 more)

### Community 15 - ".record_and_publish"
Cohesion: 0.22
Nodes (6): Any, UUID, Fetches all events for a given turn strictly after the specified sequence,…, Atomically records the event in PostgreSQL and broadcasts it to both the in-…, Retrieves historical events for reconnect replay., Atomically allocates the next monotonic sequence number for the turn and…

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
Nodes (25): ProvenanceRef, DerivationService, Any, AsyncSession, UUID, Validates provenance references, runs deterministic verification if derivations…, Normalizes candidate outputs and enforces fail-closed multi-tenant provenance…, Builds a typed ProvenanceBundle from a list of ProvenanceRef items and optional… (+17 more)

### Community 20 - "get_all_tools"
Cohesion: 0.14
Nodes (16): MCPConfig, BaseModel, Enum, Configuration management for the Open Deep Research system., Enumeration of available search API providers., Configuration for Model Context Protocol (MCP) servers., SearchAPI, get_all_tools() (+8 more)

### Community 21 - "ConversationRepository"
Cohesion: 0.13
Nodes (18): ChatEvent, Conversation, ConversationTurn, GroundConversation, Base, Durable event record for real-time turn execution streaming and reconnect…, Canonical conversational container within a Neosis workspace. Mode-agnostic:…, Canonical turn record representing a single prompt-response interaction within… (+10 more)

### Community 22 - "ground/factory.py"
Cohesion: 0.16
Nodes (14): get_embed_gateway(), get_llm_gateway(), mock_embed_call(), mock_llm_call(), get_hybrid_retrieval_service(), get_ground_engine(), get_hybrid_retrieval_service(), Request (+6 more)

### Community 23 - "policy.py"
Cohesion: 0.23
Nodes (11): filter_by_policy(), GroundContextPolicy, is_allowed_for_ground(), is_allowed_for_research(), MemoryItemType, Any, Enum, str (+3 more)

### Community 24 - "promotions.py"
Cohesion: 0.07
Nodes (48): accept_promotion(), get_promotion(), _get_promotion_service(), list_promotions(), AsyncSession, get, post, Redis (+40 more)

### Community 25 - "GraphStore"
Cohesion: 0.17
Nodes (5): GraphStore, Neo4jAdapter, Any, Abstract base class for our operational Knowledge Graph. This hides the…, AsyncDriver

### Community 26 - "MemoryRouter"
Cohesion: 0.15
Nodes (12): MemoryRouter, Any, ArqRedis, AsyncSession, UUID, Central memory and context router. Cleanly separates write routing, policy…, Intercepts memory pushes, enforcing policy boundaries before persisting. Ground…, Routes Ground context assembly through policy-governed GroundContextPolicy. (+4 more)

### Community 27 - "routes/chat.py"
Cohesion: 0.15
Nodes (32): cancel_turn(), create_conversation(), get_chat_service(), get_conversation(), get_conversation_repository(), get_turn(), get_workspace_repository(), list_conversations() (+24 more)

### Community 29 - "workspaces.py"
Cohesion: 0.27
Nodes (12): create_workspace(), patch, update_workspace(), FileUploadResponse, BaseModel, BaseModel, ResearchRequest, RollbackRequest (+4 more)

### Community 30 - "ResearchNormalizationService"
Cohesion: 0.15
Nodes (12): GPTResearcherInput, BaseModel, neosis_web_search(), InjectedToolArg, RunnableConfig, tool, Fetch search results, immediately persist them to Neosis DB, and return…, Normalizes a URL by parsing it, lowercasing the scheme and netloc, and sorting… (+4 more)

### Community 32 - "WorkspaceRepository"
Cohesion: 0.24
Nodes (7): Base, Workspace, WorkspaceCommit, AsyncSession, UUID, Atomically rolls back the workspace to a target commit under a row lock (FOR…, WorkspaceRepository

### Community 33 - "QuotaService"
Cohesion: 0.19
Nodes (9): get_quota(), get_quota_service(), AsyncSession, UUID, QuotaService, Check if user has exceeded their workspace limit., Check if workspace has exceeded its source count limit., Check if workspace has exceeded its total storage limit. (+1 more)

### Community 34 - "routes/research.py"
Cohesion: 0.10
Nodes (24): get_arq_redis(), Request, Dependency to get the arq Redis pool. We lazily initialize the pool and attach…, get_current_user(), UUID, get_rate_limit_key(), Request, Rate limit by user ID if authenticated, else fallback to IP. (+16 more)

### Community 35 - "ResearchModeOrchestrator"
Cohesion: 0.08
Nodes (22): GroundModeOrchestrator, GroundModeState, Any, deprecated, TypedDict, UUID, Deprecated: Use OpenNotebookGroundEngine instead. This orchestrator handles the…, Any (+14 more)

### Community 36 - "is_token_limit_exceeded"
Cohesion: 0.27
Nodes (10): _check_anthropic_token_limit(), _check_gemini_token_limit(), _check_openai_token_limit(), is_token_limit_exceeded(), McpError, Exception, Determine if an exception indicates a token/context limit was exceeded. Args:…, Check if exception indicates OpenAI token limit exceeded. (+2 more)

### Community 37 - "create_research_run"
Cohesion: 0.24
Nodes (11): create_research_run(), get_queue_status(), Any, AsyncSession, get, post, Redis, Response (+3 more)

### Community 38 - "chat_ground_mode"
Cohesion: 0.12
Nodes (25): ask_ground_mode(), ask_ground_mode_stream(), chat_ground_mode(), create_workspace_commit(), get_knowledge_repository(), get_memory_router(), get_research_repository(), get_source_repository() (+17 more)

### Community 39 - "UUID"
Cohesion: 0.16
Nodes (16): delete_workspace(), download_source_file(), get_projection_status(), get_source_status(), get_workspace(), get_workspace_output_graph(), get, Request (+8 more)

### Community 40 - "telemetry.py"
Cohesion: 0.28
Nodes (7): Sanitizes sensitive tokens, passwords, and API keys from log strings., Logging filter that intercepts log records and redacts any credentials, bearer…, Sets up OpenTelemetry and attaches secret sanitization to the logging root., sanitize_log_message(), SecretSanitizingFilter, setup_telemetry(), LogRecord

### Community 43 - "UsageTracker"
Cohesion: 0.20
Nodes (3): UsageTracker, MCPRetriever, Any

### Community 44 - "research/service.py"
Cohesion: 0.27
Nodes (12): GraphRepository, UUID, Projects an OutputGraph into Neo4j. Nodes get labels: OutputNode, plus their…, OutputGraph, OutputGraphEdge, OutputGraphNode, ProvenanceBundle, BaseModel (+4 more)

### Community 46 - "get_notes_from_tool_calls"
Cohesion: 0.40
Nodes (5): get_notes_from_tool_calls(), Extract notes from tool call messages., Truncate message history by removing up to the last AI message. This is useful…, remove_up_to_last_ai_message(), MessageLikeRepresentation

### Community 49 - "chat/service.py"
Cohesion: 0.07
Nodes (29): TurnCreate, ChatEventRepository, ChatEventService, format_sse_event(), AsyncSession, Dual in-process and Redis Pub/Sub event broker. Provides sub/pub abstraction…, Service coordinating event recording into PostgreSQL and broadcast across local…, Formats an event as standard Server-Sent Event (SSE): id: <sequence>\n event:… (+21 more)

### Community 53 - "stream_job_events"
Cohesion: 0.40
Nodes (5): ArqRedis, get, Request, Streams Server-Sent Events (SSE) from the Redis Pub/Sub channel for a given job., stream_job_events()

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

### Community 64 - "export.py"
Cohesion: 0.31
Nodes (6): DocumentBlock, Base, UUID, WorkspaceExportService, export_workspace_job(), Background job: Executes the workspace export using WorkspaceExportService and…

### Community 66 - ".retrieve"
Cohesion: 0.40
Nodes (3): Any, Get a registered retriever by name., Execute retrieval using the specified retriever or policy defaults, enforcing…

### Community 68 - "schemas/source.py"
Cohesion: 0.67
Nodes (3): BaseModel, SourceResponse, SourceSnapshotResponse

## Knowledge Gaps
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ResearchRepository` connect `ResearchRepository` to `WorkspaceRepository`, `ProviderRateLimiter`, `routes/research.py`, `MemoryRouter`, `tasks.py`, `create_research_run`, `ResearchQuotaService`, `chat_ground_mode`, `research/promotion.py`, `research/service.py`, `chat/service.py`, `OpenDeepResearchEngine`, `promotions.py`, `research/budget.py`, `GPTResearcherRetriever`, `workspaces.py`, `ResearchNormalizationService`?**
  _High betweenness centrality (0.190) - this node is a cross-community bridge._
- **Why does `neosis_web_search()` connect `ResearchNormalizationService` to `ResearchRepository`, `get_all_tools`, `utils.py`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Why does `ConversationRepository` connect `ConversationRepository` to `routes/research.py`, `ResearchRepository`, `tasks.py`, `create_research_run`, `chat_ground_mode`, `ScratchpadRepository`, `chat/service.py`, `routes/chat.py`, `workspaces.py`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `ResearchRepository` (e.g. with `ResearchArtifact` and `ResearchEvent`) actually correct?**
  _`ResearchRepository` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `WorkspaceRepository` (e.g. with `DeletionTombstone` and `OpenNotebookWorkspaceBinding`) actually correct?**
  _`WorkspaceRepository` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `ConversationRepository` (e.g. with `ChatEvent` and `Conversation`) actually correct?**
  _`ConversationRepository` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `ChatService` (e.g. with `cancel_turn()` and `get_turn()`) actually correct?**
  _`ChatService` has 22 INFERRED edges - model-reasoned connections that need verification._