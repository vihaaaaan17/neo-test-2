# Graph Report - NeosisLM  (2026-09-24)

## Corpus Check
- 102 files · ~38,721 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1017 nodes · 2446 edges · 54 communities (49 shown, 4 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 186 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `061519f9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- streamlit_app.py
- QuotaService
- OpenNotebookWorkspaceBinding
- ResearchRepository
- ObjectStoreProtocol
- ResearchQuotaService
- utils.py
- WorkingMemoryState
- Configuration
- tasks.py
- state.py
- workspaces.py
- BudgetEnforcingCallbackHandler
- .record_and_publish
- create_research_run
- OpenNotebookClient
- deep_researcher.py
- ResearchSourceResult
- run_research_agent_job
- ResearchNormalizationService
- get_all_tools
- ConversationRepository
- export.py
- ResearchMetricsService
- settings.py
- OpenNotebookGroundEngine
- chat/service.py
- routes/chat.py
- FastAPI
- WorkspaceRepository
- start_research
- GPTResearcherRetriever
- UsageTracker
- KnowledgeMemory
- ResearchRun
- .retrieve
- is_token_limit_exceeded
- research/budget.py
- GPTResearcherTool
- stream_job_events
- database.py
- DocumentBlock
- ._execute_ground_turn
- AcademicRetriever
- .resolve_source
- schemas/source.py
- get_notes_from_tool_calls
- .__init__
- integrations/__init__.py
- S3ObjectStore
- upload_file_to_workspace
- .list_retrievers
- ProviderRateLimiter

## God Nodes (most connected - your core abstractions)
1. `ResearchRepository` - 62 edges
2. `WorkspaceRepository` - 40 edges
3. `ChatService` - 34 edges
4. `OpenNotebookClient` - 30 edges
5. `ConversationRepository` - 28 edges
6. `ResearchQuotaService` - 26 edges
7. `ResearchRun` - 23 edges
8. `UsageTracker` - 21 edges
9. `Source` - 20 edges
10. `ResearchNormalizationService` - 20 edges

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

## Communities (54 total, 4 thin omitted)

### Community 0 - "streamlit_app.py"
Cohesion: 0.06
Nodes (34): Any, BaseModel, deprecated, TypedDict, UUID, ResearchContext, ResearchModeOrchestrator, ResearchState (+26 more)

### Community 1 - "QuotaService"
Cohesion: 0.16
Nodes (11): get_memory_router(), MemoryRouter, ArqRedis, get_quota_service(), AsyncSession, UUID, QuotaService, Check if user has exceeded their workspace limit. (+3 more)

### Community 2 - "OpenNotebookWorkspaceBinding"
Cohesion: 0.17
Nodes (14): map_citations(), AsyncSession, UUID, Map upstream Open Notebook source IDs back to canonical Neosis source_ids.…, DeletionTombstone, OpenNotebookSourceBinding, OpenNotebookWorkspaceBinding, Base (+6 more)

### Community 3 - "ResearchRepository"
Cohesion: 0.15
Nodes (11): ResearchUsage, Any, UUID, Creates multiple evidence records in batches with fingerprint deduplication., Retrieves evidence records by their fingerprints., Performs a bulk insert of evidence records., Unified repository for all Research Fabric models. Enforces workspace_id…, Persists usage metrics to the database as a periodic checkpoint. (+3 more)

### Community 4 - "ObjectStoreProtocol"
Cohesion: 0.14
Nodes (11): DocumentParser, Any, Downloads a document from Object Storage and parses it using docling. Returns a…, get_object_store(), ObjectStoreProtocol, Protocol, Request, UUID (+3 more)

### Community 5 - "ResearchQuotaService"
Cohesion: 0.12
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
Cohesion: 0.24
Nodes (11): Base, Source, SourceSnapshot, UUID, _get_source_and_snapshot(), project_to_open_notebook_job(), AsyncSession, UUID (+3 more)

### Community 10 - "state.py"
Cohesion: 0.12
Nodes (21): AgentInputState, AgentState, ClarifyWithUser, ConductResearch, override_reducer(), BaseModel, Graph state definitions and data structures for the Deep Research agent., Call this tool to conduct research on a specific topic. (+13 more)

### Community 11 - "workspaces.py"
Cohesion: 0.14
Nodes (26): ask_ground_mode(), ask_ground_mode_stream(), chat_ground_mode(), get_knowledge_repository(), get_projection_status(), get_quota(), get_research_repository(), get_source_repository() (+18 more)

### Community 12 - "BudgetEnforcingCallbackHandler"
Cohesion: 0.17
Nodes (8): BudgetEnforcingCallbackHandler, Intercepts LLM results to track usage and enforce budgets., Track token usage after an LLM call completes., Any, UUID, Execute the ODR graph and normalize its events., AsyncCallbackHandler, LLMResult

### Community 13 - ".record_and_publish"
Cohesion: 0.22
Nodes (6): Any, UUID, Atomically records the event in PostgreSQL and broadcasts it to both the in-…, Retrieves historical events for reconnect replay., Atomically allocates the next monotonic sequence number for the turn and…, Fetches all events for a given turn strictly after the specified sequence,…

### Community 14 - "create_research_run"
Cohesion: 0.23
Nodes (12): create_research_run(), enqueue_research_job(), get_queue_status(), Any, AsyncSession, get, post, Redis (+4 more)

### Community 15 - "OpenNotebookClient"
Cohesion: 0.06
Nodes (36): get_rate_limit_key(), Request, Rate limit by user ID if authenticated, else fallback to IP., Settings, setup_telemetry(), CircuitBreaker, CircuitState, OpenNotebookClient (+28 more)

### Community 16 - "deep_researcher.py"
Cohesion: 0.13
Nodes (17): execute_tool_safely(), Main LangGraph implementation for the Deep Research agent., Safely execute a tool with error handling., Execute tools called by the researcher, including search tools and strategic…, researcher_tools(), System prompts and prompt templates for the Deep Research agent., TypedDict, State for the supervisor that manages research tasks. (+9 more)

### Community 17 - "ResearchSourceResult"
Cohesion: 0.21
Nodes (12): ABC, BaseRetriever, Execute retrieval for a given query and return normalized ResearchSourceResult…, ResearchRetrievalPolicy, ResearchSourceResult, MCPRetriever, Any, Register a retriever instance under a name. (+4 more)

### Community 18 - "run_research_agent_job"
Cohesion: 0.08
Nodes (28): Any, UUID, Stream execution events from the research engine. Args: run_id: The canonical…, Trigger cooperative cancellation of the running execution., Abstract interface for all research engines in Neosis., ResearchEngine, Exception, Raised when token limits are exceeded. (+20 more)

### Community 19 - "ResearchNormalizationService"
Cohesion: 0.15
Nodes (12): GPTResearcherInput, BaseModel, neosis_web_search(), InjectedToolArg, RunnableConfig, tool, Fetch search results, immediately persist them to Neosis DB, and return…, Normalizes a URL by parsing it, lowercasing the scheme and netloc, and sorting… (+4 more)

### Community 20 - "get_all_tools"
Cohesion: 0.14
Nodes (16): MCPConfig, BaseModel, Enum, Configuration management for the Open Deep Research system., Enumeration of available search API providers., Configuration for Model Context Protocol (MCP) servers., SearchAPI, get_all_tools() (+8 more)

### Community 21 - "ConversationRepository"
Cohesion: 0.16
Nodes (14): ChatEvent, Conversation, ConversationTurn, GroundConversation, Base, Canonical conversational container within a Neosis workspace. Mode-agnostic:…, Canonical turn record representing a single prompt-response interaction within…, Durable event record for real-time turn execution streaming and reconnect… (+6 more)

### Community 22 - "export.py"
Cohesion: 0.18
Nodes (11): EpisodicMemory, Base, EpisodicRepository, AsyncSession, UUID, Used by the background worker to detect duplicate compress_episodic_job calls., EpisodicMemoryCreate, EpisodicMemoryResponse (+3 more)

### Community 23 - "ResearchMetricsService"
Cohesion: 0.13
Nodes (15): get_workspace_metrics(), AsyncSession, get, UUID, Get observability metrics for a workspace., Any, datetime, UUID (+7 more)

### Community 24 - "settings.py"
Cohesion: 0.11
Nodes (19): get_worker_pool_status(), Any, get, Get the current status of worker pools and queues., arq WorkerSettings — defines the worker process configuration. Run the worker…, Returns the configuration for a specific queue., Runs once when the worker process starts. Populate shared resources., Runs once when the worker process shuts down. (+11 more)

### Community 25 - "OpenNotebookGroundEngine"
Cohesion: 0.24
Nodes (6): OpenNotebookGroundEngine, AsyncSession, UUID, Facade for interacting with Open Notebook's retrieval and asking APIs., ArqRedis, AsyncSession

### Community 26 - "chat/service.py"
Cohesion: 0.11
Nodes (22): OpenNotebookConversationBinding, ChatEventRepository, ChatEventService, format_sse_event(), AsyncSession, Service coordinating event recording into PostgreSQL and broadcast across local…, Formats an event as standard Server-Sent Event (SSE): event: <event_type>\n…, Repository for atomic ChatEvent persistence with monotonic sequence allocation… (+14 more)

### Community 27 - "routes/chat.py"
Cohesion: 0.17
Nodes (29): create_conversation(), get_chat_service(), get_conversation(), get_conversation_repository(), get_turn(), get_workspace_repository(), list_conversations(), list_turn_events() (+21 more)

### Community 28 - "FastAPI"
Cohesion: 0.14
Nodes (18): get_arq_redis(), Request, Dependency to get the arq Redis pool. We lazily initialize the pool and attach…, get_current_user(), UUID, get_quota_status(), AsyncSession, get (+10 more)

### Community 29 - "WorkspaceRepository"
Cohesion: 0.23
Nodes (9): patch, update_workspace(), Base, Workspace, WorkspaceCommit, AsyncSession, UUID, WorkspaceRepository (+1 more)

### Community 30 - "start_research"
Cohesion: 0.26
Nodes (11): create_workspace(), create_workspace_commit(), post, rollback_workspace(), start_research(), BaseModel, ResearchRequest, RollbackRequest (+3 more)

### Community 31 - "GPTResearcherRetriever"
Cohesion: 0.47
Nodes (3): GPTResearcherRetriever, Any, Creates a mock LLM provider for GPTResearcher that uses Neosis's llm_gateway.…

### Community 32 - "UsageTracker"
Cohesion: 0.21
Nodes (4): Exception, Raised when an execution exceeds its allocated budget., ResearchBudgetExceeded, UsageTracker

### Community 33 - "KnowledgeMemory"
Cohesion: 0.17
Nodes (12): KnowledgeMemory, Base, KnowledgeRepository, AsyncSession, UUID, KnowledgeMemoryCreate, KnowledgeMemoryResponse, Provenance (+4 more)

### Community 34 - "ResearchRun"
Cohesion: 0.16
Nodes (19): Base, ResearchArtifact, ResearchEvent, ResearchEvidence, ResearchReport, ResearchRun, ResearchTask, InvalidTransitionError (+11 more)

### Community 35 - ".retrieve"
Cohesion: 0.40
Nodes (3): Any, Get a registered retriever by name., Execute retrieval using the specified retriever or policy defaults, enforcing…

### Community 36 - "is_token_limit_exceeded"
Cohesion: 0.27
Nodes (10): _check_anthropic_token_limit(), _check_gemini_token_limit(), _check_openai_token_limit(), is_token_limit_exceeded(), McpError, Exception, Determine if an exception indicates a token/context limit was exceeded. Args:…, Check if exception indicates OpenAI token limit exceeded. (+2 more)

### Community 37 - "research/budget.py"
Cohesion: 0.22
Nodes (6): Any, UUID, Research-specific budget policy to enforce cost and usage limits., Check if the budget for a research run has been exceeded. Returns True if the…, Returns the current budget status., ResearchBudgetPolicy

### Community 38 - "GPTResearcherTool"
Cohesion: 0.29
Nodes (5): GPTResearcherTool, Any, BaseTool, RunnableConfig, Use the tool asynchronously.

### Community 39 - "stream_job_events"
Cohesion: 0.40
Nodes (5): ArqRedis, get, Request, Streams Server-Sent Events (SSE) from the Redis Pub/Sub channel for a given job., stream_job_events()

### Community 40 - "database.py"
Cohesion: 0.07
Nodes (28): get_embed_gateway(), get_llm_gateway(), mock_embed_call(), mock_llm_call(), get_hybrid_retrieval_service(), get_db(), GroundModeOrchestrator, GroundModeState (+20 more)

### Community 41 - "DocumentBlock"
Cohesion: 0.17
Nodes (11): DocumentBlock, Base, BlockRepository, AsyncSession, UUID, DocumentBlockCreate, DocumentBlockResponse, BaseModel (+3 more)

### Community 42 - "._execute_ground_turn"
Cohesion: 0.40
Nodes (3): Any, Executes a Ground mode turn against Open Notebook with 1-time transparent 409…, Submits and executes a conversation turn synchronously (or 202 for research).…

### Community 44 - ".resolve_source"
Cohesion: 0.33
Nodes (4): Any, UUID, Attempts to resolve an external citation to an existing workspace Source.…, Audits the full provenance chain for a given report_id. Chain: Report ->…

### Community 45 - "schemas/source.py"
Cohesion: 0.67
Nodes (3): BaseModel, SourceResponse, SourceSnapshotResponse

### Community 46 - "get_notes_from_tool_calls"
Cohesion: 0.40
Nodes (5): get_notes_from_tool_calls(), Extract notes from tool call messages., Truncate message history by removing up to the last AI message. This is useful…, remove_up_to_last_ai_message(), MessageLikeRepresentation

### Community 49 - "S3ObjectStore"
Cohesion: 0.25
Nodes (4): AsyncSession, S3ObjectStore, export_workspace_job(), Background job: Executes the workspace export using WorkspaceExportService and…

### Community 50 - "upload_file_to_workspace"
Cohesion: 0.29
Nodes (7): delete_workspace(), ArqRedis, Request, upload_file_to_workspace(), delete, limit, UploadFile

### Community 53 - "ProviderRateLimiter"
Cohesion: 0.11
Nodes (15): Admits research run, links to turn, enqueues ARQ job, and returns running turn…, Any, UUID, Research Admission Controller to enforce quotas and rate limits before…, Admits a new research run after checking quotas and rate limits., Returns the current queue status., ResearchAdmissionController, ProviderRateLimiter (+7 more)

## Knowledge Gaps
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ResearchRepository` connect `ResearchRepository` to `streamlit_app.py`, `ResearchRun`, `research/budget.py`, `GPTResearcherTool`, `ResearchQuotaService`, `tasks.py`, `workspaces.py`, `BudgetEnforcingCallbackHandler`, `create_research_run`, `.__init__`, `run_research_agent_job`, `ResearchNormalizationService`, `ProviderRateLimiter`, `ResearchMetricsService`, `OpenNotebookGroundEngine`, `chat/service.py`, `FastAPI`, `start_research`?**
  _High betweenness centrality (0.359) - this node is a cross-community bridge._
- **Why does `neosis_web_search()` connect `ResearchNormalizationService` to `ResearchRepository`, `get_all_tools`, `utils.py`?**
  _High betweenness centrality (0.194) - this node is a cross-community bridge._
- **Why does `WorkspaceRepository` connect `WorkspaceRepository` to `streamlit_app.py`, `OpenNotebookWorkspaceBinding`, `workspaces.py`, `upload_file_to_workspace`, `OpenNotebookGroundEngine`, `chat/service.py`, `routes/chat.py`, `start_research`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `ResearchRepository` (e.g. with `ResearchArtifact` and `ResearchEvent`) actually correct?**
  _`ResearchRepository` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `WorkspaceRepository` (e.g. with `DeletionTombstone` and `OpenNotebookWorkspaceBinding`) actually correct?**
  _`WorkspaceRepository` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `ChatService` (e.g. with `get_turn()` and `list_turn_events()`) actually correct?**
  _`ChatService` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `OpenNotebookClient` (e.g. with `chat_ground_mode()` and `OpenNotebookGroundEngine`) actually correct?**
  _`OpenNotebookClient` has 3 INFERRED edges - model-reasoned connections that need verification._