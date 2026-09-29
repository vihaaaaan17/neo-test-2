# Graph Report - NeosisLM  (2026-09-28)

## Corpus Check
- 115 files · ~47,244 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1212 nodes · 3018 edges · 61 communities (58 shown, 2 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 219 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `061519f9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- workspaces.py
- ProviderRateLimiter
- models/__init__.py
- ResearchRepository
- ObjectStoreProtocol
- ResearchQuotaService
- utils.py
- WorkingMemoryState
- Configuration
- tasks.py
- state.py
- routes/scratchpad.py
- chat/context.py
- .record_and_publish
- ask_ground_mode
- OpenNotebookClient
- deep_researcher.py
- BaseRetriever
- run_research_agent_job
- verification.py
- get_all_tools
- ConversationRepository
- .accept_candidate
- ResearchNormalizationService
- settings.py
- research/service.py
- chat/service.py
- routes/chat.py
- promotions.py
- WorkspaceRepository
- MemoryRouter
- create_research_run
- KnowledgeMemory
- streamlit_app.py
- routes/research.py
- GroundModeOrchestrator
- is_token_limit_exceeded
- UsageTracker
- repositories/workspace.py
- stream_job_events
- OpenNotebookGroundEngine
- repositories/block.py
- ResearchModeOrchestrator
- derivation.py
- upload_file_to_workspace
- GPTResearcherRetriever
- get_notes_from_tool_calls
- research/budget.py
- integrations/__init__.py
- EpisodicMemory
- UUID
- schemas/promotion.py
- GraphStore
- ResearchSourceResult
- chat_ground_mode
- schemas/source.py
- S3ObjectStore
- get_quota_status
- .retrieve
- .__init__

## God Nodes (most connected - your core abstractions)
1. `ResearchRepository` - 71 edges
2. `WorkspaceRepository` - 47 edges
3. `ChatService` - 40 edges
4. `ConversationRepository` - 37 edges
5. `OpenNotebookClient` - 29 edges
6. `ResearchRun` - 29 edges
7. `ResearchArtifact` - 26 edges
8. `Source` - 25 edges
9. `ResearchQuotaService` - 25 edges
10. `ConversationTurn` - 23 edges

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

## Communities (61 total, 2 thin omitted)

### Community 0 - "workspaces.py"
Cohesion: 0.18
Nodes (13): get_embed_gateway(), get_llm_gateway(), mock_embed_call(), mock_llm_call(), get_hybrid_retrieval_service(), FileUploadResponse, BaseModel, get_hybrid_retrieval_service() (+5 more)

### Community 1 - "ProviderRateLimiter"
Cohesion: 0.10
Nodes (16): Any, Admits research run, links to turn, enqueues ARQ job, and returns running turn…, Any, UUID, Research Admission Controller to enforce quotas and rate limits before…, Admits a new research run after checking quotas and rate limits., Returns the current queue status., ResearchAdmissionController (+8 more)

### Community 2 - "models/__init__.py"
Cohesion: 0.06
Nodes (37): map_citations(), AsyncSession, UUID, Map upstream Open Notebook source IDs back to canonical Neosis source_ids.…, DocumentBlock, Base, DeletionTombstone, OpenNotebookSourceBinding (+29 more)

### Community 3 - "ResearchRepository"
Cohesion: 0.06
Nodes (44): get_workspace_metrics(), AsyncSession, get, UUID, Get observability metrics for a workspace., Base, ResearchArtifact, ResearchEvent (+36 more)

### Community 4 - "ObjectStoreProtocol"
Cohesion: 0.15
Nodes (9): DocumentParser, Any, Downloads a document from Object Storage and parses it using docling. Returns a…, get_object_store(), ObjectStoreProtocol, Protocol, Request, UUID (+1 more)

### Community 5 - "ResearchQuotaService"
Cohesion: 0.13
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

### Community 9 - "tasks.py"
Cohesion: 0.11
Nodes (25): BlockRepository, AsyncSession, ChunkingService, delete_open_notebook_source_job(), delete_open_notebook_workspace_job(), _get_source_and_snapshot(), parse_and_chunk_job(), process_deletion_tombstone_job() (+17 more)

### Community 10 - "state.py"
Cohesion: 0.12
Nodes (21): AgentInputState, AgentState, ClarifyWithUser, ConductResearch, override_reducer(), BaseModel, Graph state definitions and data structures for the Deep Research agent., Call this tool to conduct research on a specific topic. (+13 more)

### Community 11 - "routes/scratchpad.py"
Cohesion: 0.13
Nodes (24): create_scratchpad_entry(), get_scratchpad_entry(), list_scratchpad_entries(), AsyncSession, get, patch, post, UUID (+16 more)

### Community 12 - "chat/context.py"
Cohesion: 0.08
Nodes (38): build_ground_context(), build_research_context(), _ContextCandidate, ContextItemManifest, estimate_tokens(), EvictedItemManifest, GroundContext, Any (+30 more)

### Community 13 - ".record_and_publish"
Cohesion: 0.22
Nodes (6): Any, UUID, Atomically records the event in PostgreSQL and broadcasts it to both the in-…, Retrieves historical events for reconnect replay., Atomically allocates the next monotonic sequence number for the turn and…, Fetches all events for a given turn strictly after the specified sequence,…

### Community 14 - "ask_ground_mode"
Cohesion: 0.16
Nodes (14): ask_ground_mode(), ask_ground_mode_stream(), get_knowledge_repository(), get_quota(), get_research_repository(), get_workspace_repository(), AsyncSession, AskRequest (+6 more)

### Community 15 - "OpenNotebookClient"
Cohesion: 0.05
Nodes (40): get_rate_limit_key(), Request, Rate limit by user ID if authenticated, else fallback to IP., Settings, setup_telemetry(), CircuitBreaker, CircuitState, OpenNotebookClient (+32 more)

### Community 16 - "deep_researcher.py"
Cohesion: 0.13
Nodes (17): execute_tool_safely(), Main LangGraph implementation for the Deep Research agent., Safely execute a tool with error handling., Execute tools called by the researcher, including search tools and strategic…, researcher_tools(), System prompts and prompt templates for the Deep Research agent., TypedDict, State for the supervisor that manages research tasks. (+9 more)

### Community 17 - "BaseRetriever"
Cohesion: 0.28
Nodes (8): ABC, BaseRetriever, ResearchRetrievalPolicy, Register a retriever instance under a name., List all registered retriever names., Central registry for managing and invoking retrievers (web, academic, mcp,…, RetrieverRegistry, WebRetriever

### Community 18 - "run_research_agent_job"
Cohesion: 0.05
Nodes (42): BudgetEnforcingCallbackHandler, Exception, Raised when an execution exceeds its allocated budget., Intercepts LLM results to track usage and enforce budgets., Track token usage after an LLM call completes., ResearchBudgetExceeded, Any, UUID (+34 more)

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
Nodes (16): CandidateNotFoundError, InvalidLifecycleTransitionError, PromotionError, Any, Exception, UUID, Durably rejects a candidate artifact: - Sets promotion_status = 'rejected' -…, Base exception for candidate promotion operations. (+8 more)

### Community 23 - "ResearchNormalizationService"
Cohesion: 0.15
Nodes (12): GPTResearcherInput, BaseModel, neosis_web_search(), InjectedToolArg, RunnableConfig, tool, Fetch search results, immediately persist them to Neosis DB, and return…, Normalizes a URL by parsing it, lowercasing the scheme and netloc, and sorting… (+4 more)

### Community 24 - "settings.py"
Cohesion: 0.18
Nodes (10): get_worker_pool_status(), Any, get, Get the current status of worker pools and queues., arq WorkerSettings — defines the worker process configuration. Run the worker…, Returns the configuration for a specific queue., Runs once when the worker process shuts down., arq worker settings class. Discovered by: python -m arq… (+2 more)

### Community 25 - "research/service.py"
Cohesion: 0.33
Nodes (10): GraphRepository, UUID, Projects an OutputGraph into Neo4j. Nodes get labels: OutputNode, plus their…, OutputGraph, OutputGraphEdge, OutputGraphNode, ProvenanceBundle, BaseModel (+2 more)

### Community 26 - "chat/service.py"
Cohesion: 0.10
Nodes (24): OpenNotebookConversationBinding, ChatEventRepository, ChatEventService, format_sse_event(), AsyncSession, Service coordinating event recording into PostgreSQL and broadcast across local…, Formats an event as standard Server-Sent Event (SSE): event: <event_type>\n…, Repository for atomic ChatEvent persistence with monotonic sequence allocation… (+16 more)

### Community 27 - "routes/chat.py"
Cohesion: 0.17
Nodes (29): create_conversation(), get_chat_service(), get_conversation(), get_conversation_repository(), get_turn(), get_workspace_repository(), list_conversations(), list_turn_events() (+21 more)

### Community 28 - "promotions.py"
Cohesion: 0.35
Nodes (14): accept_promotion(), get_promotion(), _get_promotion_service(), list_promotions(), AsyncSession, get, post, Redis (+6 more)

### Community 29 - "WorkspaceRepository"
Cohesion: 0.24
Nodes (6): Base, WorkspaceCommit, AsyncSession, UUID, Atomically rolls back the workspace to a target commit under a row lock (FOR…, WorkspaceRepository

### Community 30 - "MemoryRouter"
Cohesion: 0.33
Nodes (5): MemoryRouter, ArqRedis, Central memory and context router. Cleanly separates write routing, policy…, Central coordinator for Research Engine Phase 2. Implements explicit promotion…, ResearchService

### Community 31 - "create_research_run"
Cohesion: 0.24
Nodes (11): create_research_run(), get_queue_status(), Any, AsyncSession, get, post, Redis, Response (+3 more)

### Community 32 - "KnowledgeMemory"
Cohesion: 0.22
Nodes (10): KnowledgeMemory, Base, KnowledgeRepository, AsyncSession, UUID, KnowledgeMemoryCreate, KnowledgeMemoryResponse, Provenance (+2 more)

### Community 33 - "streamlit_app.py"
Cohesion: 0.23
Nodes (7): Neo4jAdapter, AsyncDriver, create_db_workspace(), get_litellm_gateway(), project_graph_to_neo4j(), run_agent(), run_ground_mode()

### Community 34 - "routes/research.py"
Cohesion: 0.16
Nodes (15): get_arq_redis(), Request, Dependency to get the arq Redis pool. We lazily initialize the pool and attach…, get_current_user(), UUID, get_rate_limit_status(), get, Redis (+7 more)

### Community 35 - "GroundModeOrchestrator"
Cohesion: 0.14
Nodes (12): GroundModeOrchestrator, GroundModeState, Any, deprecated, TypedDict, UUID, Deprecated: Use OpenNotebookGroundEngine instead. This orchestrator handles the…, ContextBundle (+4 more)

### Community 36 - "is_token_limit_exceeded"
Cohesion: 0.27
Nodes (10): _check_anthropic_token_limit(), _check_gemini_token_limit(), _check_openai_token_limit(), is_token_limit_exceeded(), McpError, Exception, Determine if an exception indicates a token/context limit was exceeded. Args:…, Check if exception indicates OpenAI token limit exceeded. (+2 more)

### Community 37 - "UsageTracker"
Cohesion: 0.20
Nodes (3): UsageTracker, MCPRetriever, Any

### Community 38 - "repositories/workspace.py"
Cohesion: 0.29
Nodes (9): patch, start_research(), update_workspace(), BaseModel, ResearchRequest, WorkspaceCommitResponse, WorkspaceCreate, WorkspaceResponse (+1 more)

### Community 39 - "stream_job_events"
Cohesion: 0.40
Nodes (5): ArqRedis, get, Request, Streams Server-Sent Events (SSE) from the Redis Pub/Sub channel for a given job., stream_job_events()

### Community 40 - "OpenNotebookGroundEngine"
Cohesion: 0.18
Nodes (9): OpenNotebookGroundEngine, AsyncSession, UUID, Facade for interacting with Open Notebook's retrieval and asking APIs., ArqRedis, AsyncSession, get_ground_engine(), Request (+1 more)

### Community 41 - "repositories/block.py"
Cohesion: 0.25
Nodes (6): UUID, DocumentBlockCreate, DocumentBlockResponse, BaseModel, Any, Takes the raw dictionary output from Docling and converts it into…

### Community 42 - "ResearchModeOrchestrator"
Cohesion: 0.16
Nodes (10): Any, BaseModel, deprecated, TypedDict, UUID, ResearchContext, ResearchModeOrchestrator, ResearchState (+2 more)

### Community 43 - "derivation.py"
Cohesion: 0.18
Nodes (12): ProvenanceRef, CrossWorkspaceBoundaryError, DerivationService, Any, AsyncSession, Exception, UUID, Raised when a provenance reference points across workspace boundaries or does… (+4 more)

### Community 44 - "upload_file_to_workspace"
Cohesion: 0.25
Nodes (7): get_source_repository(), Request, upload_file_to_workspace(), AsyncSession, SourceRepository, limit, UploadFile

### Community 45 - "GPTResearcherRetriever"
Cohesion: 0.18
Nodes (8): GPTResearcherTool, Any, BaseTool, RunnableConfig, Use the tool asynchronously., GPTResearcherRetriever, Any, Creates a mock LLM provider for GPTResearcher that uses Neosis's llm_gateway.…

### Community 46 - "get_notes_from_tool_calls"
Cohesion: 0.40
Nodes (5): get_notes_from_tool_calls(), Extract notes from tool call messages., Truncate message history by removing up to the last AI message. This is useful…, remove_up_to_last_ai_message(), MessageLikeRepresentation

### Community 47 - "research/budget.py"
Cohesion: 0.20
Nodes (6): Any, UUID, Research-specific budget policy to enforce cost and usage limits., Check if the budget for a research run has been exceeded. Returns True if the…, Returns the current budget status., ResearchBudgetPolicy

### Community 49 - "EpisodicMemory"
Cohesion: 0.24
Nodes (9): EpisodicMemory, Base, EpisodicRepository, AsyncSession, UUID, Used by the background worker to detect duplicate compress_episodic_job calls., EpisodicMemoryCreate, EpisodicMemoryResponse (+1 more)

### Community 50 - "UUID"
Cohesion: 0.29
Nodes (10): create_workspace(), create_workspace_commit(), get_projection_status(), get_source_status(), get_workspace(), get, post, UUID (+2 more)

### Community 52 - "schemas/promotion.py"
Cohesion: 0.36
Nodes (9): ClaimCandidatePayload, DerivationExpression, FindingCandidatePayload, GraphCandidatePayload, HypothesisCandidatePayload, MemoryCandidatePayload, PromotionCandidateResponse, PromotionReviewRequest (+1 more)

### Community 54 - "GraphStore"
Cohesion: 0.25
Nodes (3): GraphStore, Any, Abstract base class for our operational Knowledge Graph. This hides the…

### Community 55 - "ResearchSourceResult"
Cohesion: 0.29
Nodes (5): AcademicRetriever, Any, Execute retrieval for a given query and return normalized ResearchSourceResult…, ResearchSourceResult, Any

### Community 56 - "chat_ground_mode"
Cohesion: 0.25
Nodes (9): chat_ground_mode(), delete_workspace(), get_memory_router(), ArqRedis, Response, ChatRequest, ChatResponse, BaseModel (+1 more)

### Community 57 - "schemas/source.py"
Cohesion: 0.67
Nodes (3): BaseModel, SourceResponse, SourceSnapshotResponse

### Community 59 - "S3ObjectStore"
Cohesion: 0.28
Nodes (5): AsyncSession, WorkspaceExportService, S3ObjectStore, export_workspace_job(), Background job: Executes the workspace export using WorkspaceExportService and…

### Community 61 - "get_quota_status"
Cohesion: 0.33
Nodes (6): get_quota_status(), AsyncSession, get, Redis, UUID, Get the current quota status for the user and workspace.

### Community 63 - ".retrieve"
Cohesion: 0.40
Nodes (3): Any, Get a registered retriever by name., Execute retrieval using the specified retriever or policy defaults, enforcing…

## Knowledge Gaps
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ResearchRepository` connect `ResearchRepository` to `workspaces.py`, `ProviderRateLimiter`, `tasks.py`, `ask_ground_mode`, `run_research_agent_job`, `ResearchNormalizationService`, `research/service.py`, `chat/service.py`, `promotions.py`, `MemoryRouter`, `create_research_run`, `KnowledgeMemory`, `routes/research.py`, `repositories/workspace.py`, `OpenNotebookGroundEngine`, `GPTResearcherRetriever`, `research/budget.py`, `get_quota_status`, `.__init__`?**
  _High betweenness centrality (0.297) - this node is a cross-community bridge._
- **Why does `neosis_web_search()` connect `ResearchNormalizationService` to `ResearchRepository`, `get_all_tools`, `utils.py`?**
  _High betweenness centrality (0.149) - this node is a cross-community bridge._
- **Why does `OpenNotebookClient` connect `OpenNotebookClient` to `workspaces.py`, `tasks.py`, `OpenNotebookGroundEngine`, `chat/service.py`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `ResearchRepository` (e.g. with `ResearchArtifact` and `ResearchEvent`) actually correct?**
  _`ResearchRepository` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `WorkspaceRepository` (e.g. with `DeletionTombstone` and `OpenNotebookWorkspaceBinding`) actually correct?**
  _`WorkspaceRepository` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `ChatService` (e.g. with `get_turn()` and `list_turn_events()`) actually correct?**
  _`ChatService` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `ConversationRepository` (e.g. with `ChatEvent` and `Conversation`) actually correct?**
  _`ConversationRepository` has 3 INFERRED edges - model-reasoned connections that need verification._