# Graph Report - NeosisLM  (2026-09-29)

## Corpus Check
- 116 files · ~50,702 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1237 nodes · 3113 edges · 58 communities (55 shown, 2 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 232 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `061519f9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- tasks.py
- chat/service.py
- OpenNotebookGroundEngine
- ResearchRepository
- ObjectStoreProtocol
- ResearchQuotaService
- utils.py
- EpisodicMemory
- Configuration
- core/config.py
- state.py
- routes/scratchpad.py
- chat/context.py
- OpenNotebookClient
- WorkingMemoryState
- main.py
- deep_researcher.py
- BaseRetriever
- OpenDeepResearchEngine
- verification.py
- get_all_tools
- ConversationRepository
- .accept_candidate
- ResearchNormalizationService
- settings.py
- GroundModeOrchestrator
- streamlit_app.py
- WorkspaceRepository
- ResearchModeOrchestrator
- MemoryRouterService
- Source
- auth.py
- derivation.py
- repositories/block.py
- FastAPI
- ground/factory.py
- is_token_limit_exceeded
- UsageTracker
- workspaces.py
- database.py
- telemetry.py
- promotions.py
- schemas/promotion.py
- GraphStore
- research/service.py
- GPTResearcherRetriever
- get_notes_from_tool_calls
- research/budget.py
- integrations/__init__.py
- ChatEventRepository
- CircuitBreaker
- DerivationService
- ResearchSourceResult
- schemas/source.py
- create_research_run
- export.py
- .retrieve

## God Nodes (most connected - your core abstractions)
1. `ResearchRepository` - 71 edges
2. `WorkspaceRepository` - 47 edges
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
- `run_ground_mode()` --uses--> `HybridRetrievalService`  [INFERRED]
  streamlit_app.py → app/services/hybrid_retrieval.py
- `project_graph_to_neo4j()` --calls--> `GraphRepository`  [EXTRACTED]
  streamlit_app.py → app/repositories/graph.py

## Import Cycles
- None detected.

## Communities (58 total, 2 thin omitted)

### Community 0 - "tasks.py"
Cohesion: 0.12
Nodes (23): BlockRepository, AsyncSession, ChunkingService, delete_open_notebook_source_job(), delete_open_notebook_workspace_job(), _get_source_and_snapshot(), parse_and_chunk_job(), process_deletion_tombstone_job() (+15 more)

### Community 1 - "chat/service.py"
Cohesion: 0.09
Nodes (24): TurnCreate, BaseModel, ResearchRunResponse, ChatService, Any, Submits a turn and returns an async generator streaming its events via SSE.…, Coordinates turn submission, mode dispatching (Ground vs Research),…, Executes a Ground mode turn against Open Notebook with 1-time transparent 409… (+16 more)

### Community 2 - "OpenNotebookGroundEngine"
Cohesion: 0.12
Nodes (21): map_citations(), AsyncSession, UUID, Map upstream Open Notebook source IDs back to canonical Neosis source_ids.…, OpenNotebookGroundEngine, Any, AsyncSession, UUID (+13 more)

### Community 3 - "ResearchRepository"
Cohesion: 0.06
Nodes (46): get_workspace_metrics(), AsyncSession, get, UUID, Get observability metrics for a workspace., Base, ResearchArtifact, ResearchEvent (+38 more)

### Community 4 - "ObjectStoreProtocol"
Cohesion: 0.15
Nodes (9): DocumentParser, Any, Downloads a document from Object Storage and parses it using docling. Returns a…, get_object_store(), ObjectStoreProtocol, Protocol, Request, UUID (+1 more)

### Community 5 - "ResearchQuotaService"
Cohesion: 0.13
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

### Community 9 - "core/config.py"
Cohesion: 0.25
Nodes (5): Settings, Validates infrastructure, checkpointer, and security invariants during…, validate_production_startup(), Shared HTTP client for Open Notebook integration., BaseSettings

### Community 10 - "state.py"
Cohesion: 0.12
Nodes (21): AgentInputState, AgentState, ClarifyWithUser, ConductResearch, override_reducer(), BaseModel, Graph state definitions and data structures for the Deep Research agent., Call this tool to conduct research on a specific topic. (+13 more)

### Community 11 - "routes/scratchpad.py"
Cohesion: 0.13
Nodes (24): create_scratchpad_entry(), get_scratchpad_entry(), list_scratchpad_entries(), AsyncSession, get, patch, post, UUID (+16 more)

### Community 12 - "chat/context.py"
Cohesion: 0.08
Nodes (38): build_ground_context(), build_research_context(), _ContextCandidate, ContextItemManifest, estimate_tokens(), EvictedItemManifest, GroundContext, Any (+30 more)

### Community 13 - "OpenNotebookClient"
Cohesion: 0.25
Nodes (8): OpenNotebookClient, Any, Check health endpoint of Open Notebook. Returns the parsed JSON response.…, Streams the ask response, yielding standardized SSE events., Executes a chat message. Returns the final answer text and the updated…, Streams chat events and incremental tokens for a conversation session. Yields…, HTTP client for communicating with the Open Notebook API. Establishes the…, with_error_translation()

### Community 14 - "WorkingMemoryState"
Cohesion: 0.18
Nodes (11): TypedDict, WorkingMemoryState, EpisodicMemoryService, UUID, llm_gateway: an async callable that takes a string prompt and returns a string…, Dispatch compression to the background queue., Call LLM with concurrency limits and retries., process_memory() (+3 more)

### Community 15 - "main.py"
Cohesion: 0.12
Nodes (20): CircuitState, Enum, get_open_notebook_base_url(), get_open_notebook_timeout(), is_open_notebook_enabled(), Get the default HTTP timeout for Open Notebook requests., Check if the Open Notebook Ground Engine is enabled., Get the base URL for the Open Notebook API. (+12 more)

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
Cohesion: 0.16
Nodes (14): ChatEvent, Conversation, ConversationTurn, GroundConversation, Base, Durable event record for real-time turn execution streaming and reconnect…, Canonical conversational container within a Neosis workspace. Mode-agnostic:…, Canonical turn record representing a single prompt-response interaction within… (+6 more)

### Community 22 - ".accept_candidate"
Cohesion: 0.12
Nodes (16): CandidateNotFoundError, InvalidLifecycleTransitionError, PromotionError, Any, Exception, UUID, Atomically accepts a candidate artifact: 1. Verifies workspace access and…, Durably rejects a candidate artifact: - Sets promotion_status = 'rejected' -… (+8 more)

### Community 23 - "ResearchNormalizationService"
Cohesion: 0.15
Nodes (12): GPTResearcherInput, BaseModel, neosis_web_search(), InjectedToolArg, RunnableConfig, tool, Fetch search results, immediately persist them to Neosis DB, and return…, Normalizes a URL by parsing it, lowercasing the scheme and netloc, and sorting… (+4 more)

### Community 24 - "settings.py"
Cohesion: 0.12
Nodes (17): get_worker_pool_status(), Any, get, Get the current status of worker pools and queues., get_checkpointer(), Any, Validates checkpointer configuration on startup. In production, durable…, Returns the checkpointer instance appropriate for the current environment. (+9 more)

### Community 25 - "GroundModeOrchestrator"
Cohesion: 0.20
Nodes (8): GroundModeOrchestrator, GroundModeState, Any, deprecated, TypedDict, UUID, Deprecated: Use OpenNotebookGroundEngine instead. This orchestrator handles the…, MemoryItem

### Community 26 - "streamlit_app.py"
Cohesion: 0.17
Nodes (8): Neo4jAdapter, Executes a search query and returns the results formatted as markdown., WebSearchTool, AsyncDriver, get_litellm_gateway(), project_graph_to_neo4j(), run_agent(), run_ground_mode()

### Community 27 - "WorkspaceRepository"
Cohesion: 0.09
Nodes (40): cancel_turn(), create_conversation(), get_chat_service(), get_conversation(), get_conversation_repository(), get_turn(), get_workspace_repository(), list_conversations() (+32 more)

### Community 28 - "ResearchModeOrchestrator"
Cohesion: 0.27
Nodes (7): BaseModel, deprecated, TypedDict, UUID, ResearchContext, ResearchModeOrchestrator, ResearchState

### Community 29 - "MemoryRouterService"
Cohesion: 0.22
Nodes (5): Any, ContextBundle, BaseModel, MemoryRouterService, Lightweight heuristic context builder for MemoryItem bundles. Preserved for…

### Community 30 - "Source"
Cohesion: 0.09
Nodes (22): Base, Source, SourceSnapshot, AsyncSession, UUID, SourceRepository, ArqRedis, get_quota_service() (+14 more)

### Community 31 - "auth.py"
Cohesion: 0.27
Nodes (8): get_current_user(), UUID, get_rate_limit_status(), get, Redis, UUID, Get the current rate limit status for the user., HTTPAuthorizationCredentials

### Community 32 - "derivation.py"
Cohesion: 0.21
Nodes (10): KnowledgeMemory, Base, KnowledgeRepository, AsyncSession, UUID, KnowledgeMemoryCreate, KnowledgeMemoryResponse, Provenance (+2 more)

### Community 33 - "repositories/block.py"
Cohesion: 0.25
Nodes (6): UUID, DocumentBlockCreate, DocumentBlockResponse, BaseModel, Any, Takes the raw dictionary output from Docling and converts it into…

### Community 34 - "FastAPI"
Cohesion: 0.15
Nodes (12): get_arq_redis(), Request, Dependency to get the arq Redis pool. We lazily initialize the pool and attach…, get_rate_limit_key(), Request, Rate limit by user ID if authenticated, else fallback to IP., ArqRedis, get (+4 more)

### Community 35 - "ground/factory.py"
Cohesion: 0.13
Nodes (16): get_embed_gateway(), get_llm_gateway(), mock_embed_call(), mock_llm_call(), get_hybrid_retrieval_service(), get_ground_engine(), get_hybrid_retrieval_service(), Any (+8 more)

### Community 36 - "is_token_limit_exceeded"
Cohesion: 0.27
Nodes (10): _check_anthropic_token_limit(), _check_gemini_token_limit(), _check_openai_token_limit(), is_token_limit_exceeded(), McpError, Exception, Determine if an exception indicates a token/context limit was exceeded. Args:…, Check if exception indicates OpenAI token limit exceeded. (+2 more)

### Community 37 - "UsageTracker"
Cohesion: 0.20
Nodes (3): UsageTracker, MCPRetriever, Any

### Community 38 - "workspaces.py"
Cohesion: 0.09
Nodes (47): ask_ground_mode(), ask_ground_mode_stream(), chat_ground_mode(), create_workspace(), create_workspace_commit(), delete_workspace(), get_knowledge_repository(), get_memory_router() (+39 more)

### Community 39 - "database.py"
Cohesion: 0.28
Nodes (7): get_quota_status(), AsyncSession, get, Redis, UUID, Get the current quota status for the user and workspace., get_db()

### Community 40 - "telemetry.py"
Cohesion: 0.28
Nodes (7): Sanitizes sensitive tokens, passwords, and API keys from log strings., Logging filter that intercepts log records and redacts any credentials, bearer…, Sets up OpenTelemetry and attaches secret sanitization to the logging root., sanitize_log_message(), SecretSanitizingFilter, setup_telemetry(), LogRecord

### Community 41 - "promotions.py"
Cohesion: 0.27
Nodes (17): accept_promotion(), get_promotion(), _get_promotion_service(), list_promotions(), AsyncSession, get, post, Redis (+9 more)

### Community 42 - "schemas/promotion.py"
Cohesion: 0.36
Nodes (9): ClaimCandidatePayload, DerivationExpression, FindingCandidatePayload, GraphCandidatePayload, HypothesisCandidatePayload, MemoryCandidatePayload, PromotionCandidateResponse, PromotionReviewRequest (+1 more)

### Community 43 - "GraphStore"
Cohesion: 0.25
Nodes (3): GraphStore, Any, Abstract base class for our operational Knowledge Graph. This hides the…

### Community 44 - "research/service.py"
Cohesion: 0.21
Nodes (16): GraphRepository, UUID, Projects an OutputGraph into Neo4j. Nodes get labels: OutputNode, plus their…, OutputGraph, OutputGraphEdge, OutputGraphNode, ProvenanceBundle, BaseModel (+8 more)

### Community 45 - "GPTResearcherRetriever"
Cohesion: 0.18
Nodes (8): GPTResearcherTool, Any, BaseTool, RunnableConfig, Use the tool asynchronously., GPTResearcherRetriever, Any, Creates a mock LLM provider for GPTResearcher that uses Neosis's llm_gateway.…

### Community 46 - "get_notes_from_tool_calls"
Cohesion: 0.40
Nodes (5): get_notes_from_tool_calls(), Extract notes from tool call messages., Truncate message history by removing up to the last AI message. This is useful…, remove_up_to_last_ai_message(), MessageLikeRepresentation

### Community 47 - "research/budget.py"
Cohesion: 0.20
Nodes (6): Any, UUID, Research-specific budget policy to enforce cost and usage limits., Check if the budget for a research run has been exceeded. Returns True if the…, Returns the current budget status., ResearchBudgetPolicy

### Community 49 - "ChatEventRepository"
Cohesion: 0.06
Nodes (27): ChatEventRepository, ChatEventService, format_sse_event(), Any, AsyncSession, UUID, Dual in-process and Redis Pub/Sub event broker. Provides sub/pub abstraction…, Service coordinating event recording into PostgreSQL and broadcast across local… (+19 more)

### Community 53 - "DerivationService"
Cohesion: 0.17
Nodes (11): ProvenanceRef, DerivationService, Any, AsyncSession, UUID, Validates provenance references, runs deterministic verification if derivations…, Normalizes candidate outputs and enforces fail-closed multi-tenant provenance…, Builds a typed ProvenanceBundle from a list of ProvenanceRef items and optional… (+3 more)

### Community 55 - "ResearchSourceResult"
Cohesion: 0.29
Nodes (5): AcademicRetriever, Any, Execute retrieval for a given query and return normalized ResearchSourceResult…, ResearchSourceResult, Any

### Community 57 - "schemas/source.py"
Cohesion: 0.67
Nodes (3): BaseModel, SourceResponse, SourceSnapshotResponse

### Community 61 - "create_research_run"
Cohesion: 0.24
Nodes (11): create_research_run(), get_queue_status(), Any, AsyncSession, get, post, Redis, Response (+3 more)

### Community 62 - "export.py"
Cohesion: 0.19
Nodes (8): DocumentBlock, Base, AsyncSession, UUID, WorkspaceExportService, S3ObjectStore, export_workspace_job(), Background job: Executes the workspace export using WorkspaceExportService and…

### Community 63 - ".retrieve"
Cohesion: 0.40
Nodes (3): Any, Get a registered retriever by name., Execute retrieval using the specified retriever or policy defaults, enforcing…

## Knowledge Gaps
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ResearchRepository` connect `ResearchRepository` to `derivation.py`, `chat/service.py`, `tasks.py`, `workspaces.py`, `database.py`, `promotions.py`, `research/service.py`, `GPTResearcherRetriever`, `research/budget.py`, `ChatEventRepository`, `OpenDeepResearchEngine`, `DerivationService`, `ResearchNormalizationService`, `create_research_run`?**
  _High betweenness centrality (0.246) - this node is a cross-community bridge._
- **Why does `neosis_web_search()` connect `ResearchNormalizationService` to `ResearchRepository`, `get_all_tools`, `utils.py`?**
  _High betweenness centrality (0.144) - this node is a cross-community bridge._
- **Why does `ResearchRun` connect `ResearchRepository` to `derivation.py`, `chat/service.py`, `tasks.py`, `ResearchQuotaService`, `workspaces.py`, `promotions.py`, `chat/context.py`, `research/service.py`, `OpenDeepResearchEngine`, `DerivationService`, `Source`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `ResearchRepository` (e.g. with `ResearchArtifact` and `ResearchEvent`) actually correct?**
  _`ResearchRepository` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `WorkspaceRepository` (e.g. with `DeletionTombstone` and `OpenNotebookWorkspaceBinding`) actually correct?**
  _`WorkspaceRepository` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `ChatService` (e.g. with `cancel_turn()` and `get_turn()`) actually correct?**
  _`ChatService` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `ConversationRepository` (e.g. with `ChatEvent` and `Conversation`) actually correct?**
  _`ConversationRepository` has 3 INFERRED edges - model-reasoned connections that need verification._