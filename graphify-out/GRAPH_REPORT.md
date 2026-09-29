# Graph Report - NeosisLM  (2026-09-29)

## Corpus Check
- 116 files · ~51,953 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1250 nodes · 3148 edges · 54 communities (50 shown, 3 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 234 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ea7abe72`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- tasks.py
- ProviderRateLimiter
- OpenNotebookGroundEngine
- ResearchRepository
- .parse_document
- ResearchQuotaService
- utils.py
- EpisodicMemory
- Configuration
- research/promotion.py
- state.py
- routes/scratchpad.py
- chat/context.py
- OpenNotebookClient
- WorkingMemoryState
- chat/service.py
- deep_researcher.py
- BaseRetriever
- OpenDeepResearchEngine
- Source
- get_all_tools
- ConversationRepository
- promotions.py
- ResearchNormalizationService
- core/config.py
- streamlit_app.py
- policy.py
- routes/chat.py
- MemoryRouter
- .stream_turn_events
- .__init__
- QuotaService
- Workspace
- repositories/block.py
- routes/research.py
- ground/factory.py
- is_token_limit_exceeded
- UsageTracker
- workspaces.py
- schemas/workspace.py
- settings.py
- research/service.py
- GPTResearcherRetriever
- get_notes_from_tool_calls
- research/budget.py
- integrations/__init__.py
- ChatService
- WorkspaceRepository
- TurnCreate
- ResearchSourceResult
- schemas/source.py
- S3ObjectStore
- .retrieve

## God Nodes (most connected - your core abstractions)
1. `ResearchRepository` - 71 edges
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

## Communities (54 total, 3 thin omitted)

### Community 0 - "tasks.py"
Cohesion: 0.11
Nodes (24): BlockRepository, AsyncSession, ChunkingService, DocumentParser, delete_open_notebook_source_job(), delete_open_notebook_workspace_job(), _get_source_and_snapshot(), parse_and_chunk_job() (+16 more)

### Community 1 - "ProviderRateLimiter"
Cohesion: 0.08
Nodes (18): ArqRedis, AsyncSession, Submits a turn and returns an async generator streaming its events via SSE.…, Admits research run, links to turn, enqueues ARQ job, and returns running turn…, Any, UUID, Research Admission Controller to enforce quotas and rate limits before…, Admits a new research run after checking quotas and rate limits. (+10 more)

### Community 2 - "OpenNotebookGroundEngine"
Cohesion: 0.12
Nodes (23): map_canonical_sources_to_upstream(), map_citations(), AsyncSession, UUID, Map upstream Open Notebook source IDs back to canonical Neosis source_ids.…, Map canonical Neosis source_ids (UUIDs) to upstream Open Notebook source IDs…, OpenNotebookGroundEngine, Any (+15 more)

### Community 3 - "ResearchRepository"
Cohesion: 0.06
Nodes (44): Base, ResearchArtifact, ResearchEvent, ResearchEvidence, ResearchReport, ResearchRun, ResearchTask, ResearchUsage (+36 more)

### Community 5 - "ResearchQuotaService"
Cohesion: 0.12
Nodes (14): Any, UUID, Service to manage research quotas for users, workspaces, and globally., Returns the current user concurrency status., Returns the current workspace concurrency status., Returns the current global concurrency status., Enforces the user concurrency quota. Returns ACCEPTED or QUOTA_EXCEEDED., Enforces the workspace concurrency quota. Returns ACCEPTED or QUOTA_EXCEEDED. (+6 more)

### Community 6 - "utils.py"
Cohesion: 0.10
Nodes (29): fetch_tokens(), get_mcp_access_token(), get_tavily_api_key(), get_tokens(), load_mcp_tools(), Any, BaseTool, InjectedToolArg (+21 more)

### Community 7 - "EpisodicMemory"
Cohesion: 0.23
Nodes (9): EpisodicMemory, Base, EpisodicRepository, AsyncSession, UUID, Used by the background worker to detect duplicate compress_episodic_job calls., EpisodicMemoryCreate, EpisodicMemoryResponse (+1 more)

### Community 8 - "Configuration"
Cohesion: 0.15
Nodes (26): Config, Configuration, RunnableConfig, Create a Configuration instance from a RunnableConfig., Pydantic configuration., Main configuration class for the Deep Research agent., clarify_with_user(), compress_research() (+18 more)

### Community 9 - "research/promotion.py"
Cohesion: 0.21
Nodes (10): KnowledgeMemory, Base, KnowledgeRepository, AsyncSession, UUID, KnowledgeMemoryCreate, KnowledgeMemoryResponse, Provenance (+2 more)

### Community 10 - "state.py"
Cohesion: 0.12
Nodes (21): AgentInputState, AgentState, ClarifyWithUser, ConductResearch, override_reducer(), BaseModel, Graph state definitions and data structures for the Deep Research agent., Call this tool to conduct research on a specific topic. (+13 more)

### Community 11 - "routes/scratchpad.py"
Cohesion: 0.13
Nodes (24): create_scratchpad_entry(), get_scratchpad_entry(), list_scratchpad_entries(), AsyncSession, get, patch, post, UUID (+16 more)

### Community 12 - "chat/context.py"
Cohesion: 0.18
Nodes (20): build_ground_context(), build_research_context(), _ContextCandidate, ContextItemManifest, estimate_tokens(), EvictedItemManifest, GroundContext, Any (+12 more)

### Community 13 - "OpenNotebookClient"
Cohesion: 0.06
Nodes (36): Sanitizes sensitive tokens, passwords, and API keys from log strings., Logging filter that intercepts log records and redacts any credentials, bearer…, Sets up OpenTelemetry and attaches secret sanitization to the logging root., sanitize_log_message(), SecretSanitizingFilter, setup_telemetry(), CircuitBreaker, CircuitState (+28 more)

### Community 14 - "WorkingMemoryState"
Cohesion: 0.18
Nodes (11): TypedDict, WorkingMemoryState, EpisodicMemoryService, UUID, llm_gateway: an async callable that takes a string prompt and returns a string…, Dispatch compression to the background queue., Call LLM with concurrency limits and retries., process_memory() (+3 more)

### Community 15 - "chat/service.py"
Cohesion: 0.11
Nodes (21): ChatEvent, GroundConversation, Base, Durable event record for real-time turn execution streaming and reconnect…, ChatEventRepository, ChatEventService, format_sse_event(), Any (+13 more)

### Community 16 - "deep_researcher.py"
Cohesion: 0.13
Nodes (17): execute_tool_safely(), Main LangGraph implementation for the Deep Research agent., Safely execute a tool with error handling., Execute tools called by the researcher, including search tools and strategic…, researcher_tools(), System prompts and prompt templates for the Deep Research agent., TypedDict, State for the supervisor that manages research tasks. (+9 more)

### Community 17 - "BaseRetriever"
Cohesion: 0.28
Nodes (8): ABC, BaseRetriever, ResearchRetrievalPolicy, Register a retriever instance under a name., List all registered retriever names., Central registry for managing and invoking retrievers (web, academic, mcp,…, RetrieverRegistry, WebRetriever

### Community 18 - "OpenDeepResearchEngine"
Cohesion: 0.05
Nodes (38): BudgetEnforcingCallbackHandler, Exception, Raised when an execution exceeds its allocated budget., Intercepts LLM results to track usage and enforce budgets., Track token usage after an LLM call completes., ResearchBudgetExceeded, Any, UUID (+30 more)

### Community 19 - "Source"
Cohesion: 0.07
Nodes (36): DocumentBlock, Base, Base, Source, SourceSnapshot, UUID, ProvenanceRef, UUID (+28 more)

### Community 20 - "get_all_tools"
Cohesion: 0.14
Nodes (16): MCPConfig, BaseModel, Enum, Configuration management for the Open Deep Research system., Enumeration of available search API providers., Configuration for Model Context Protocol (MCP) servers., SearchAPI, get_all_tools() (+8 more)

### Community 21 - "ConversationRepository"
Cohesion: 0.14
Nodes (14): Conversation, ConversationTurn, Canonical conversational container within a Neosis workspace. Mode-agnostic:…, Canonical turn record representing a single prompt-response interaction within…, ConversationRepository, Any, AsyncSession, datetime (+6 more)

### Community 22 - "promotions.py"
Cohesion: 0.09
Nodes (39): accept_promotion(), get_promotion(), _get_promotion_service(), list_promotions(), AsyncSession, get, post, Redis (+31 more)

### Community 23 - "ResearchNormalizationService"
Cohesion: 0.15
Nodes (12): GPTResearcherInput, BaseModel, neosis_web_search(), InjectedToolArg, RunnableConfig, tool, Fetch search results, immediately persist them to Neosis DB, and return…, Normalizes a URL by parsing it, lowercasing the scheme and netloc, and sorting… (+4 more)

### Community 24 - "core/config.py"
Cohesion: 0.15
Nodes (12): Settings, Validates infrastructure, checkpointer, and security invariants during…, validate_production_startup(), Shared HTTP client for Open Notebook integration., get_checkpointer(), Any, Validates checkpointer configuration on startup. In production, durable…, Returns the checkpointer instance appropriate for the current environment. (+4 more)

### Community 25 - "streamlit_app.py"
Cohesion: 0.05
Nodes (32): GroundModeOrchestrator, GroundModeState, Any, deprecated, TypedDict, UUID, Deprecated: Use OpenNotebookGroundEngine instead. This orchestrator handles the…, Any (+24 more)

### Community 26 - "policy.py"
Cohesion: 0.23
Nodes (11): filter_by_policy(), GroundContextPolicy, is_allowed_for_ground(), is_allowed_for_research(), MemoryItemType, Any, Enum, str (+3 more)

### Community 27 - "routes/chat.py"
Cohesion: 0.16
Nodes (30): cancel_turn(), create_conversation(), get_conversation(), get_conversation_repository(), get_turn(), get_workspace_repository(), list_conversations(), list_turn_events() (+22 more)

### Community 28 - "MemoryRouter"
Cohesion: 0.16
Nodes (12): get_memory_router(), MemoryRouter, Any, AsyncSession, UUID, Central memory and context router. Cleanly separates write routing, policy…, Intercepts memory pushes, enforcing policy boundaries before persisting. Ground…, Routes Ground context assembly through policy-governed GroundContextPolicy. (+4 more)

### Community 29 - ".stream_turn_events"
Cohesion: 0.38
Nodes (4): Dual in-process and Redis Pub/Sub event broker. Provides sub/pub abstraction…, TurnEventBroker, Unified SSE generator — supports reconnect replay via Last-Event-ID. Protocol:…, Queue

### Community 31 - "QuotaService"
Cohesion: 0.17
Nodes (9): ArqRedis, get_quota_service(), AsyncSession, UUID, QuotaService, Check if user has exceeded their workspace limit., Check if workspace has exceeded its source count limit., Check if workspace has exceeded its total storage limit. (+1 more)

### Community 32 - "Workspace"
Cohesion: 0.23
Nodes (5): Base, Workspace, WorkspaceCommit, UUID, Atomically rolls back the workspace to a target commit under a row lock (FOR…

### Community 33 - "repositories/block.py"
Cohesion: 0.25
Nodes (6): UUID, DocumentBlockCreate, DocumentBlockResponse, BaseModel, Any, Takes the raw dictionary output from Docling and converts it into…

### Community 34 - "routes/research.py"
Cohesion: 0.06
Nodes (45): get_arq_redis(), Request, Dependency to get the arq Redis pool. We lazily initialize the pool and attach…, get_current_user(), UUID, get_rate_limit_key(), Request, Rate limit by user ID if authenticated, else fallback to IP. (+37 more)

### Community 35 - "ground/factory.py"
Cohesion: 0.11
Nodes (20): get_embed_gateway(), get_llm_gateway(), mock_embed_call(), mock_llm_call(), get_chat_service(), ArqRedis, get_hybrid_retrieval_service(), get_ground_engine() (+12 more)

### Community 36 - "is_token_limit_exceeded"
Cohesion: 0.27
Nodes (10): _check_anthropic_token_limit(), _check_gemini_token_limit(), _check_openai_token_limit(), is_token_limit_exceeded(), McpError, Exception, Determine if an exception indicates a token/context limit was exceeded. Args:…, Check if exception indicates OpenAI token limit exceeded. (+2 more)

### Community 37 - "UsageTracker"
Cohesion: 0.20
Nodes (3): UsageTracker, MCPRetriever, Any

### Community 38 - "workspaces.py"
Cohesion: 0.15
Nodes (19): ask_ground_mode(), chat_ground_mode(), get_knowledge_repository(), get_quota(), get_research_repository(), get_source_repository(), get_workspace_repository(), AsyncSession (+11 more)

### Community 39 - "schemas/workspace.py"
Cohesion: 0.43
Nodes (7): BaseModel, ResearchRequest, RollbackRequest, WorkspaceCommitResponse, WorkspaceCreate, WorkspaceResponse, WorkspaceUpdate

### Community 41 - "settings.py"
Cohesion: 0.15
Nodes (12): get_worker_pool_status(), Any, get, Get the current status of worker pools and queues., arq WorkerSettings — defines the worker process configuration. Run the worker…, Returns the configuration for a specific queue., Runs once when the worker process shuts down., arq worker settings class. Discovered by: python -m arq… (+4 more)

### Community 44 - "research/service.py"
Cohesion: 0.27
Nodes (12): GraphRepository, UUID, Projects an OutputGraph into Neo4j. Nodes get labels: OutputNode, plus their…, OutputGraph, OutputGraphEdge, OutputGraphNode, ProvenanceBundle, BaseModel (+4 more)

### Community 45 - "GPTResearcherRetriever"
Cohesion: 0.18
Nodes (8): GPTResearcherTool, Any, BaseTool, RunnableConfig, Use the tool asynchronously., GPTResearcherRetriever, Any, Creates a mock LLM provider for GPTResearcher that uses Neosis's llm_gateway.…

### Community 46 - "get_notes_from_tool_calls"
Cohesion: 0.40
Nodes (5): get_notes_from_tool_calls(), Extract notes from tool call messages., Truncate message history by removing up to the last AI message. This is useful…, remove_up_to_last_ai_message(), MessageLikeRepresentation

### Community 47 - "research/budget.py"
Cohesion: 0.20
Nodes (6): Any, UUID, Research-specific budget policy to enforce cost and usage limits., Check if the budget for a research run has been exceeded. Returns True if the…, Returns the current budget status., ResearchBudgetPolicy

### Community 49 - "ChatService"
Cohesion: 0.15
Nodes (10): ChatService, UUID, Coordinates turn submission, mode dispatching (Ground vs Research),…, Executes Ground turn in background with independent DB session. Delegates…, Deprecated in Chapter 4 Ticket 02. ARQ background worker is the sole…, Creates a new Open Notebook chat session and updates the binding for the…, Retrieves a single turn with tenant access validation., Lists turns in a conversation ordered by sequence. (+2 more)

### Community 50 - "WorkspaceRepository"
Cohesion: 0.17
Nodes (23): ask_ground_mode_stream(), create_workspace(), create_workspace_commit(), delete_workspace(), get_projection_status(), get_source_status(), get_workspace(), get_workspace_output_graph() (+15 more)

### Community 54 - "TurnCreate"
Cohesion: 0.25
Nodes (5): TurnCreate, Any, Executes a Ground mode turn against Open Notebook with 1-time transparent 409…, Submits and executes a conversation turn synchronously (or 202 for research).…, field_validator

### Community 55 - "ResearchSourceResult"
Cohesion: 0.29
Nodes (5): AcademicRetriever, Any, Execute retrieval for a given query and return normalized ResearchSourceResult…, ResearchSourceResult, Any

### Community 57 - "schemas/source.py"
Cohesion: 0.67
Nodes (3): BaseModel, SourceResponse, SourceSnapshotResponse

### Community 62 - "S3ObjectStore"
Cohesion: 0.14
Nodes (8): AsyncSession, get_object_store(), ObjectStoreProtocol, Protocol, Request, UUID, Dependency to provide shared S3ObjectStore from app state., S3ObjectStore

### Community 63 - ".retrieve"
Cohesion: 0.40
Nodes (3): Any, Get a registered retriever by name., Execute retrieval using the specified retriever or policy defaults, enforcing…

## Knowledge Gaps
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ResearchRepository` connect `ResearchRepository` to `tasks.py`, `ProviderRateLimiter`, `routes/research.py`, `ResearchQuotaService`, `workspaces.py`, `research/promotion.py`, `research/service.py`, `GPTResearcherRetriever`, `chat/service.py`, `research/budget.py`, `OpenDeepResearchEngine`, `WorkspaceRepository`, `promotions.py`, `ResearchNormalizationService`, `MemoryRouter`, `.__init__`?**
  _High betweenness centrality (0.249) - this node is a cross-community bridge._
- **Why does `neosis_web_search()` connect `ResearchNormalizationService` to `ResearchRepository`, `get_all_tools`, `utils.py`?**
  _High betweenness centrality (0.138) - this node is a cross-community bridge._
- **Why does `ConversationRepository` connect `ConversationRepository` to `tasks.py`, `ProviderRateLimiter`, `routes/research.py`, `ground/factory.py`, `workspaces.py`, `routes/scratchpad.py`, `chat/service.py`, `ChatService`, `WorkspaceRepository`, `routes/chat.py`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `ResearchRepository` (e.g. with `ResearchArtifact` and `ResearchEvent`) actually correct?**
  _`ResearchRepository` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `WorkspaceRepository` (e.g. with `DeletionTombstone` and `OpenNotebookWorkspaceBinding`) actually correct?**
  _`WorkspaceRepository` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `ConversationRepository` (e.g. with `ChatEvent` and `Conversation`) actually correct?**
  _`ConversationRepository` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `ChatService` (e.g. with `cancel_turn()` and `get_turn()`) actually correct?**
  _`ChatService` has 22 INFERRED edges - model-reasoned connections that need verification._