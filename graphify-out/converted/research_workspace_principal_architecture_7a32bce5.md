<!-- converted from research_workspace_principal_architecture.xlsx -->

## Sheet: 00_Summary
| Area | What must exist | Reuse level | Primary ownership |
| --- | --- | --- | --- |
| Notebook/RAG | Ingestion, source parsing, retrieval, grounded citations | High reuse | Adapt Open Notebook + retrieval components |
| Research Agent | Planner, workers, web/search, synthesis, verification | Medium reuse | Adapt Open Deep Research/STORM/GPT Researcher |
| Memory Fabric | 16 distinct memory types behind one API | Mixed | Own semantic contract |
| State Engine | 20 state types + transitions/checkpoints/events | Low reuse | Own canonical state model |
| Grounded Graph | Source-backed evidence graph | Graph infra reuse | Own ontology/provenance |
| Research Graph | Hypothesis/finding/calculation/failure graph | Graph infra reuse | Own ontology/provenance |
| Versioning | Events, commits, branches, diff, merge, rollback | Git concepts only | Own research-specific semantics |
| Trust Layer | Citation/calculation/contradiction/coverage verification | Mixed | Own verification policy |
| Artifacts | Reports, citations, datasets, LaTeX later | Mixed | Own provenance integration |
## Sheet: 01_Architecture
| Component | Macro Layer | Responsibility | Build Strategy | Reference / Reuse | Principal Engineer Notes |
| --- | --- | --- | --- | --- | --- |
| Research Workspace | Product boundary | Single workspace containing sources, evidence, memories, graphs, runs, notes and artifacts | Build | Custom | Canonical scope boundary |
| Grounded Knowledge Graph | User-visible graph | Source-backed documents, fragments, claims, entities, citations | Build + graph infra | SurrealDB / Neo4j / Graphiti patterns | Strict provenance |
| Research Knowledge Graph | User-visible graph | Hypotheses, findings, derived claims, calculations, failures, contradictions | Build + graph infra | Graphiti / STORM patterns | Must preserve research lineage |
| Grounded Mode | Execution mode | Answer from user evidence with strict citations | Reuse + adapt | Open Notebook | Retrieval policy is yours |
| Research Mode | Execution mode | Plan/search/read/reason/calculate/verify/synthesize | Reuse + adapt | Open Deep Research / STORM / GPT Researcher | Own durable state contract |
| Memory Fabric | Agent context layer | Multiple typed memories selected by task and scope | Build + adapt | Letta / Mem0 / LlamaIndex | Never collapse into one vector store |
| State Engine | Runtime + persistence | Tracks active/completed/failed/blocked/verified state | Build + reuse | Workflow checkpoints | Typed state machine + event log |
| Versioning | Reproducibility | Git-like commits, branches, diffs, merges and rollback | Build | Git concepts | Domain-specific merge semantics |
| Evidence Store | Trust substrate | Immutable source snapshots, fragments, citations, evidence links | Build + reuse | Open Notebook / Docling | Append-first semantics |
| Scratchpad | Working surface | Loose notes, equations, questions, todos and hypotheses | Build | Custom | Typed and linkable |
| Artifact Layer | Outputs | Reports, tables, figures, datasets, paper drafts | Reuse + integrate | S3-compatible store + renderers | Every artifact traceable |
| Verification | Trust layer | Claim support, citation validation, calculations, contradictions | Build + reuse | NIST-inspired eval patterns | Separate support from verification |
| Observability | Operations | Traces, costs, latency, failures, model/tool metadata | Reuse + adapt | OpenTelemetry | Trace every run/task/tool |
| Security | Governance | Workspace isolation, tool permissions, secret isolation, sandboxing | Build + reuse | Vault / containers / browser-use | Threat model as first-class design |
## Sheet: 02_Component_Inventory
| Macro Domain | Component | Responsibility | Layer | Strategy | OSS / Reference | Build Effort | Architecture Note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ingestion | Source ingestion gateway | Accept files, URLs, pasted text, browser pages, APIs and datasets | Core | Adapt | Open Notebook | High | Own normalization contract |
| Ingestion | Document parser | Parse PDF/DOCX/PPTX/XLSX/HTML/EPUB/images and structured docs | Core | Reuse | Docling | Low | Use structured intermediate representation |
| Ingestion | OCR pipeline | OCR scanned pages and images | Core | Reuse | Docling/Tesseract/EasyOCR/RapidOCR | Low | Build backend routing only |
| Ingestion | Layout/table extraction | Preserve headings, reading order, tables, figures and formulas | Core | Reuse + adapt | Docling | Medium | Keep page/region coordinates |
| Ingestion | Web extraction | Fetch and normalize web content | Core | Reuse + adapt | trafilatura/Playwright/browser-use | Medium | Snapshot sources |
| Ingestion | Metadata enrichment | Add DOI, title, authors, date, venue, language and identifiers | Core | Reuse + adapt | OpenAlex/Crossref | Medium | Canonicalize identifiers |
| Ingestion | Content fingerprinting | Hash raw and normalized content | Integrity | Build | Standard hashing | Low | Drives dedupe/versioning |
| Retrieval | Lexical search | Exact/full-text/BM25 search | Retrieval | Reuse | SurrealDB/Postgres/OpenSearch | Medium | Useful for exact source facts |
| Retrieval | Vector index | Semantic ANN retrieval | Retrieval | Reuse | SurrealDB/pgvector/Qdrant | Low | Embeddings are regenerable |
| Retrieval | Graph retrieval | Traverse typed graph relations | Retrieval | Build + reuse | Graphiti/SurrealDB/Neo4j | High | Core differentiator |
| Retrieval | Hybrid retriever | Fuse lexical, vector and graph candidates | Retrieval | Build | LlamaIndex/Haystack patterns | High | Product-specific ranking |
| Retrieval | Reranker | Cross-encoder/LLM reranking | Retrieval | Reuse | bge-reranker/Jina/etc. | Low | Pluggable |
| Retrieval | Context assembler | Build model context with evidence and provenance | Agent runtime | Build | Custom | High | Source before derived material |
| Retrieval | Context budget manager | Allocate tokens by evidence value and task | Agent runtime | Build + adapt | LlamaIndex concepts | High | Dynamic budgets |
| Memory | Conversation recall | Immutable message history and semantic recall | Memory | Build + adapt | Letta/LlamaIndex | Medium | Separate from working context |
| Memory | Working memory | Current task variables, selected evidence and active hypotheses | Memory | Build | LlamaIndex Context patterns | High | Checkpointed |
| Memory | Semantic memory | Durable facts/claims | Memory | Build + adapt | Mem0/Letta/Graphiti | High | Graph-linked with provenance |
| Memory | Episodic research memory | Completed discoveries and run episodes | Memory | Build | Letta patterns | High | Positive and negative episodes |
| Memory | Negative memory | Failed searches, dead ends and rejected hypotheses | Memory | Build | Custom | High | Prevents repeated failure |
| Memory | Procedural memory | Research recipes, tool use patterns, prompts and workflows | Memory | Build + adapt | Letta concepts | High | Version like code |
| Memory | Reflective memory | Lessons learned from prior research | Memory | Build | Custom | High | Must link to evidence |
| Memory | Temporal memory | Facts with validity/observation times | Memory | Adapt | Graphiti/Zep concepts | High | Bi-temporal semantics |
| Memory | User/project memory | Research conventions and user preferences | Memory | Build + adapt | Letta blocks | Medium | Scoped separately from facts |
| State | Workspace state | Current head, branch, active scope, permissions | State | Build | Git concepts | High | Canonical |
| State | Research run state | Plan, branch, budgets, checkpoints, lifecycle | State | Build + adapt | LangGraph concepts | Critical | Durable |
| State | Task state | Subtask dependencies, retries, outputs | State | Build + adapt | Workflow engines | Critical | Parallelizable |
| State | Evidence state | Evidence lifecycle and verification state | State | Build | Custom | Critical | Not same as node type |
| State | Claim state | Proposed/sourced/supported/disputed/verified/refuted/superseded | State | Build | Custom | Critical | Typed lifecycle |
| State | Hypothesis state | Open/testing/supported/refuted/abandoned | State | Build | Custom | High | Branch-aware |
| State | Tool invocation state | Queued/running/succeeded/failed/timed-out/cancelled | State | Reuse + adapt | Workflow/queue systems | High | Every call traceable |
| State | Human review state | Pending/approved/rejected/edited/review | State | Build | Custom | High | Required for high-trust mode |
| State | Recovery state | Checkpoint/resume/compensation | State | Reuse + adapt | LangGraph/LlamaIndex | High | Idempotency |
| Knowledge Graph | Grounded graph | Source-backed nodes and edges | Graph | Build | Graph DB | Very High | User-visible |
| Knowledge Graph | Research graph | Research process and derived knowledge | Graph | Build | Graph DB | Very High | User-visible |
| Knowledge Graph | Cross-graph provenance | Derived items point to grounded inputs | Graph | Build | Custom | Critical | Non-negotiable |
| Knowledge Graph | Typed edge semantics | Supports/derives/contradicts/verifies/depends/correlates/etc. | Graph | Build | Graph DB | Very High | Ontology is product IP |
| Knowledge Graph | Graph projections | Topic/paper/hypothesis/failure/grounded subgraphs | Graph | Build | Graph queries | High | User can switch views |
| Agent | Planner | Break question into tasks and dependencies | Agent | Adapt + build | Open Deep Research/STORM/GPT Researcher | High | Emit typed tasks |
| Agent | Research worker | Run search/read/extract branches | Agent | Adapt | Open Deep Research/GPT Researcher | High | Durable worker state |
| Agent | Critic/verifier | Challenge claims and detect gaps | Agent | Build + adapt | STORM / evaluation patterns | High | Independent verification loop |
| Agent | Source comparator | Compare papers/claims and detect disagreement | Agent | Build | Custom | High | Graph-aware |
| Agent | Math engine | Symbolic and numerical calculation | Tool | Reuse | SymPy/NumPy/SciPy | Low | Store expression and result |
| Agent | Code sandbox | Execute data analysis and code | Tool | Reuse + harden | Jupyter/container sandbox | High | Security-critical |
| Agent | Browser worker | Research dynamic sites and pages | Tool | Reuse + harden | browser-use/Playwright | High | Isolated browser |
| Agent | Tool router | Choose search/web/graph/math/local tools | Agent | Build | MCP/tool patterns | High | Task-aware routing |
| Agent | Parallel executor | Run independent branches concurrently | Runtime | Reuse + adapt | LangGraph/queues | High | Budget aware |
| Agent | Retry/repair engine | Repair failed tasks or tools | Runtime | Build + adapt | Agent harness patterns | High | Failure class driven |
| Versioning | Event log | Append-only record of every mutation | Versioning | Build | Event sourcing | Very High | Canonical mutation history |
| Versioning | Commit | Research workspace snapshot/version | Versioning | Build | Git concepts | Very High | Hash parent + mutation set |
| Versioning | Branch | Alternative research path/hypothesis | Versioning | Build | Git concepts | High | Supports experiments |
| Versioning | Merge | Reconcile divergent research paths | Versioning | Build | Git concepts | Very High | Domain-aware conflicts |
| Versioning | Diff | Compare graph/memory/state/artifact changes | Versioning | Build | Git concepts | High | Human-readable |
| Versioning | Revert | Undo via new inverse commit | Versioning | Build | Git concepts | High | Preserve history |
| Verification | Citation validator | Check cited claim actually supported by source | Trust | Build | NIST-inspired | Very High | Claim-level |
| Verification | Calculation verifier | Rerun deterministic calculations | Trust | Reuse + adapt | SymPy/Python | High | Compare stored outputs |
| Verification | Contradiction detector | Find incompatible claims/results | Trust | Build | Custom + LLM | High | Graph-driven |
| Verification | Coverage analyzer | Measure unsupported generated claims | Trust | Build | Custom | Critical | Per sentence/claim |
| Verification | Risk classifier | Classify evidence strength and uncertainty | Trust | Build | Model evaluator | High | Show provenance status |
| Infrastructure | Object storage | Raw sources and generated artifacts | Storage | Reuse | S3-compatible | Low | Canonical blobs |
| Infrastructure | Database | Metadata, state, permissions and transactions | Storage | Reuse | SurrealDB/Postgres | Medium | Transaction boundary |
| Infrastructure | Vector store | Embeddings/ANN | Storage | Reuse | SurrealDB/pgvector/Qdrant | Low | Pluggable |
| Infrastructure | Cache | Fast non-canonical data | Storage | Reuse | Redis/Valkey | Low | Never source of truth |
| Infrastructure | Queue | Durable async jobs | Storage | Reuse | NATS/RabbitMQ/Redis/SQS | Medium | Needed for ingestion/research |
| Infrastructure | Observability | Traces/metrics/logs | Ops | Reuse | OpenTelemetry | Medium | Trace run/task/tool/model |
| Artifacts | Report generator | Research reports with embedded provenance | Artifact | Adapt | Markdown/HTML/Jinja/Pandoc | Medium | Every claim resolvable |
| Artifacts | Citation formatter | BibTeX/RIS/CSL output | Artifact | Reuse | CSL ecosystem | Low | Canonical citation object |
| Artifacts | LaTeX compiler | Compile research papers | Artifact | Reuse + integrate | Tectonic/TeXLive | Medium | Later phase |
| Evaluation | Retrieval evaluation | Recall/precision/nDCG/source hit metrics | Quality | Build + reuse | Ragas/DeepEval patterns | High | Separate grounded/research |
| Evaluation | Agent trajectory evaluation | Plan/tool/reasoning trajectory scoring | Quality | Build + reuse | Eval frameworks | High | Trace-backed |
| Evaluation | Research benchmark harness | Run fixed research tasks as regression suite | Quality | Build | Custom | High | Version benchmark data |
## Sheet: 03_Memory_Taxonomy
| ID | Memory Type | Stores | Persistence | Scope | Retrieval | Confidence/Trust | Versioning |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M01 | Context Window | Current messages + selected evidence | Ephemeral | Request | Token-limited recency + relevance | Not durable | No |
| M02 | Conversation Recall | Past messages and conversation summaries | Persistent | User/workspace | Lexical + semantic | Raw history | Yes |
| M03 | Working Task | Current task variables, evidence shortlist, active hypotheses | Checkpointed | Run/task | Key-value + structured queries | Operational | Yes |
| M04 | Semantic Fact | Stable accepted facts/claims | Persistent | Workspace | Hybrid vector + graph + lexical | Source/provenance based | Yes |
| M05 | Episodic Research | Completed research episodes/discoveries | Persistent | Workspace/project | Semantic + graph + time | Outcome-linked | Yes |
| M06 | Negative Memory | Dead ends, failed searches, rejected paths | Persistent | Workspace/project | Exact + semantic + task filter | Failure confidence | Yes |
| M07 | Hypothesis Memory | Unverified candidate explanations | Persistent | Research branch | Graph + semantic | Explicitly unverified | Yes |
| M08 | Derived Knowledge | Calculated or inferred results | Persistent | Workspace | Graph + vector + structured | Derived; never source fact | Yes |
| M09 | Procedural Memory | Research workflows/tool recipes/prompts | Persistent | User/workspace | Versioned lookup | Performance/effectiveness | Yes |
| M10 | Reflective Memory | Lessons learned from prior runs | Persistent | Workspace | Semantic + graph | Evidence-linked | Yes |
| M11 | User Preference | Research depth, style, preferred models/sources | Persistent | User | Key-value/profile | Not factual | Yes |
| M12 | Project Convention | Definitions, notation, assumptions, domain vocabulary | Persistent | Workspace | Graph + config | Scoped | Yes |
| M13 | Temporal Fact | Facts with valid/observed/invalid dates | Persistent | Workspace | Temporal graph | Temporal confidence | Yes |
| M14 | Decision Memory | Human approvals, overrides, rejected options | Persistent | Workspace | Event + graph | Governance authoritative | Yes |
| M15 | Tool Experience | Tool reliability, latency, failure patterns | Persistent | System/workspace | Structured + semantic | Statistical | Yes |
| M16 | Artifact Memory | Reports, datasets, figures, drafts | Persistent | Workspace | Object metadata | Provenance-based | Yes |
## Sheet: 04_State_Taxonomy
| ID | State Type | Tracks | Scope | Persistence | Authoritative? | Checkpoint? | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | Workspace State | Current head, active branch, selected scope, permissions | Workspace | Persistent | Yes | Yes | Canonical product state |
| S02 | Session State | Active UI session and selection context | User session | Ephemeral | No | Optional | Not research truth |
| S03 | Conversation State | Message lifecycle + conversation metadata | Conversation | Persistent | Yes | Yes | Messages immutable |
| S04 | Research Run State | Question, plan, mode, budget, current branch, status | Run | Persistent | Yes | Yes | Primary execution state |
| S05 | Task State | Subtask lifecycle, dependencies, outputs | Task | Persistent | Yes | Yes | Supports DAG |
| S06 | Worker State | Individual agent/tool worker context | Worker | Checkpointed | Yes | Yes | Recoverable |
| S07 | Retrieval State | Query, candidates, filters, ranking, selected context | Step | Ephemeral | No | Optional | Traceable, not truth |
| S08 | Evidence Lifecycle | Candidate/accepted/verified/contradicted/invalidated | Evidence | Persistent | Yes | Yes | Separate from graph node type |
| S09 | Claim Lifecycle | Proposed/sourced/supported/disputed/verified/refuted/superseded | Claim | Persistent | Yes | Yes | Critical |
| S10 | Hypothesis Lifecycle | Open/testing/supported/refuted/abandoned | Hypothesis | Persistent | Yes | Yes | Branch-aware |
| S11 | Graph Projection State | Materialized graph view at a commit/timepoint | Graph | Derived | No | Yes | Recomputable |
| S12 | Scratchpad State | Loose notes, equations, todos, temporary reasoning | Workspace | Persistent | No | Optional | Should be typed |
| S13 | Human Review State | Pending/approved/rejected/edited/review | Review | Persistent | Yes | Yes | Governance |
| S14 | Artifact State | Draft/generated/checked/approved/published | Artifact | Persistent | Yes | Yes | Artifact lifecycle |
| S15 | Tool Invocation State | Queued/running/succeeded/failed/cancelled/timeout | Tool call | Persistent | Yes | Yes | Audit + retry |
| S16 | Budget State | Token/time/money/search/browser/compute budgets | Run/task | Checkpointed | Yes | Yes | Prevents runaway agents |
| S17 | Model Invocation State | Model/provider/version/parameters/prompt/toolset | Invocation | Immutable | Yes | No | Reproducibility |
| S18 | Failure State | Error class, context, retryability, remediation | Failure | Persistent | Yes | Yes | Fails become research data |
| S19 | Version State | Commit, parent, branch, actor, mutation hash | Workspace | Persistent | Yes | Yes | Git-like |
| S20 | Recovery State | Resume point, idempotent actions, compensation | Preemption boundary | Persistent | Yes | Yes | Long-running agent recovery |
## Sheet: 05_Graph_Model
| Graph | Concept | Type | Purpose | User-visible? |
| --- | --- | --- | --- | --- |
| Grounded | Document | Node | Canonical source identity, metadata, blob hash | Yes |
| Grounded | Source Snapshot | Node | Immutable captured source version | Yes |
| Grounded | Fragment | Node | Exact page/region/text retrieval unit | Yes |
| Grounded | Extracted Claim | Node | Directly source-derived claim | Yes |
| Grounded | Entity | Node | Person/org/concept/method/dataset/entity | Yes |
| Grounded | Citation | Node | Bibliographic/source reference | Yes |
| Grounded | Table/Figure | Node | Structured evidence object | Yes |
| Grounded | Equation | Node | Source equation/formula | Yes |
| Grounded | Grounded Note | Node | User/AI note anchored to source evidence | Yes |
| Research | Research Question | Node | Root research objective | Yes |
| Research | Research Task | Node | Subproblem in research plan | Yes |
| Research | Hypothesis | Node | Candidate explanation/answer | Yes |
| Research | Finding | Node | Research-discovered result | Yes |
| Research | Derived Claim | Node | Calculated/inferred claim | Yes |
| Research | Calculation | Node | Expression, inputs, result and verifier | Yes |
| Research | Experiment | Node | Test designed around hypothesis | Yes |
| Research | Failure | Node | Dead end, failed tool, bad source, rejected path | Yes |
| Research | Contradiction | Node | Incompatible claims/results | Yes |
| Research | Decision | Node | Human/agent branch/approval decision | Yes |
| Research | Artifact | Node | Report/table/figure/dataset/paper | Yes |
| Cross | Provenance Link | Edge | Derived/research object -> grounded evidence | Yes |
| Cross | Verification Link | Edge | Verifier/check -> claim/result | Yes |
| Cross | Correlation Link | Edge | Observed association, explicitly non-causal | Yes |
| Cross | Dependency Link | Edge | Task/claim/calculation dependency | Yes |
| Cross | Supersession Link | Edge | New item replaces old item | Yes |
| Cross | Refutation Link | Edge | Evidence/result challenges prior claim | Yes |
| Projection | Topic Subgraph | View | All nodes relevant to a topic | Yes |
| Projection | Paper Subgraph | View | All evidence + research derived from one paper | Yes |
| Projection | Hypothesis Branch | View | Downstream graph of a hypothesis | Yes |
| Projection | Failure Map | View | Failures + causes + retries + avoided paths | Yes |
| Projection | Grounded Slice | View | Only source-backed nodes and edges | Yes |
## Sheet: 06_Graph_Edge_Semantics
| Edge | Source | Target | Meaning | Rule |
| --- | --- | --- | --- | --- |
| supports | Source/Claim/Finding | Claim/Hypothesis | Provides positive evidence | Must carry provenance refs |
| cites | Claim/Artifact | Source/Document | References a source | Exact location preferred |
| contains | Document | Fragment | Document structure relation | Deterministic |
| mentions | Fragment | Entity | Entity occurs in fragment | Weak semantic relation |
| derives_from | Derived Claim/Finding | Claim/Fragment/Calculation | Result depends on inputs | All direct inputs recorded |
| calculated_from | Calculation | Evidence/values | Inputs used in calculation | Expression and units stored |
| tests | Experiment | Hypothesis | Experiment evaluates hypothesis | Outcome required |
| supports | Hypothesis/Finding | Evidence/Claim | Research result supports candidate | Analytical not source fact |
| contradicts | Claim/Finding | Claim/Finding | Items conflict | Keep both; never overwrite |
| refutes | Evidence/Finding | Claim/Hypothesis | Item weakens/rejects target | Store reason |
| depends_on | Task/Claim/Calculation | Task/Claim | Dependency for execution/logic | Used for scheduling |
| correlates_with | Entity/Claim | Entity/Claim | Observed association | Explicitly non-causal |
| verifies | Verifier/Check | Claim/Calculation/Evidence | Validation relationship | Record verifier + method |
| supersedes | New Claim/Artifact | New/old object | Replaces previous state | Old object remains queryable |
| failed_because | Failure | Task/Tool/Source | Failure cause | Classified + linked to negative memory |
| retry_of | Retry Task/Tool | Previous Task/Tool | Retry lineage | Bounded |
| generated_from | Artifact | Graph/Claim/Prompt/Source | Artifact provenance | Generator manifest required |
| human_approved | User decision | Claim/Artifact/Branch | Explicit human approval | Record actor/time |
| branch_of | Branch | Commit | Research version lineage | Git-like |
| merged_from | Merge Commit | Parent Commit | Merge lineage | Conflicts recorded |
## Sheet: 07_Data_Model
| Object | Core Fields | Persistence | Primary Store | Notes |
| --- | --- | --- | --- | --- |
| Workspace | workspace_id, owner_id, head_commit_id, active_branch, created_at | Authoritative | SQL/document DB | Top-level isolation |
| Source | source_id, uri, blob_hash, source_type, title, authors, published_at, captured_at | Immutable | DB + object store | Canonical source identity |
| SourceSnapshot | snapshot_id, source_id, retrieval_time, content_hash, parser_version, raw_uri | Immutable | DB + object store | Reproducible reprocessing |
| Document | document_id, source_id, parsed_hash, parser, language, page_count | Immutable | DB | Normalized logical source |
| Fragment | fragment_id, document_id, page, region, text, structure_path, token_count | Immutable | DB | Primary citation unit |
| Embedding | embedding_id, object_id, model, dimension, vector_hash | Regenerable | Vector store | Do not make vector canonical |
| Entity | entity_id, canonical_name, type, aliases, metadata | Versioned | Graph + DB | Entity resolution |
| Claim | claim_id, text, claim_type, lifecycle_status, created_by | Versioned | Graph + DB | Typed epistemic object |
| EvidenceLink | evidence_id, claim_id, fragment_id/source_id, relation, span, verifier_status | Versioned | DB + graph | Claim-level grounding |
| Hypothesis | hypothesis_id, text, status, branch_id, created_by | Versioned | Graph + DB | Can be supported/refuted |
| Calculation | calculation_id, expression, inputs, units, engine, code_hash, result | Versioned | DB + object store | Deterministic replay |
| ResearchRun | run_id, workspace_id, question, plan_version, mode, status, head_commit | Versioned | State store | Primary research execution |
| Task | task_id, run_id, parent_task_id, type, status, dependencies, budget | Versioned | State store | Parallelizable |
| ToolCall | tool_call_id, task_id, tool_name, args_hash, result_ref, status | Immutable | Trace/state store | Audit |
| Failure | failure_id, task_id, class, message, retryable, resolution | Immutable | Trace + graph | Failure is data |
| MemoryItem | memory_id, type, scope, payload, salience, valid_at, invalid_at | Versioned | DB + vector + graph | Typed memory |
| ScratchItem | scratch_id, type, text, links, status, author | Versioned | DB | Human/agent workspace |
| GraphNode | node_id, graph_id, object_id, node_type, version_id | Versioned | Graph store | Projection anchor |
| GraphEdge | edge_id, graph_id, src_id, dst_id, edge_type, confidence, provenance_refs | Versioned | Graph store | First-class provenance |
| ReviewItem | review_id, object_type, object_id, reviewer, decision, comments | Append-only | DB | Governance |
| Commit | commit_id, parent_ids, branch, author, mutation_set_hash, created_at | Immutable | DB/object store | Git-like |
| Event | event_id, aggregate_type, aggregate_id, event_type, payload, actor, timestamp, commit_id | Immutable | Event store | Canonical mutation log |
| Artifact | artifact_id, type, object_uri, source_commit, status, generator | Versioned | Object store + DB | Every output traceable |
| PromptVersion | prompt_id, template, model_role, version, checksum | Immutable | Git/object store | Reproducibility |
| ModelInvocation | invocation_id, model, provider, params, prompt_hash, input_refs, output_ref, usage | Immutable | Trace store | Cost + reproducibility |
## Sheet: 08_OSS_Landscape
| Project | Role | Use | Provides | License / status | URL | Key caveat |
| --- | --- | --- | --- | --- | --- | --- |
| Open Notebook | Notebook/RAG foundation | Fork/adapt | Multi-notebook ingestion, PDFs/web/audio/video/docs, full-text/vector search, contextual chat, notes, citations | Open source | https://github.com/lfnovo/open-notebook | Keep your canonical research state separate from its internal schema |
| LangChain Open Deep Research | Deep-research agent | Architecture/reference | Planner/researcher/synthesis workflow, configurable tools and providers | MIT; archived Aug 21 2026 | https://github.com/langchain-ai/open_deep_research | Use patterns, not as a hard dependency |
| STORM / knowledge-storm | Research + knowledge curation | Adapt/reference | Multi-perspective research, outline creation, citation-oriented synthesis, Co-STORM collaboration | Open source | https://github.com/stanford-oval/storm | Excellent reference for research curation |
| GPT Researcher | Autonomous research agent | Adapt/reference | Parallel research, web search, source aggregation, reports/citations | MIT | https://github.com/assafelovic/gpt-researcher | Own durable state and provenance |
| Letta | Stateful agent memory | Reuse selectively | Persistent agent identity, memory blocks, recall and learning patterns | Apache-2.0 | https://github.com/letta-ai/letta | Your domain memory is richer than generic agent memory |
| Letta Agent SDK | Stateful agent SDK | Reuse selectively | Agent identity + persistent memory API | Apache-2.0 | https://github.com/letta-ai/letta-agent-sdk | Consider as adapter, not source of truth |
| Mem0 | Agent memory | Reuse selectively | Memory extraction/retrieval and graph memory | Apache-2.0 | https://github.com/mem0ai/mem0 | Native graph is useful but provenance semantics need your layer |
| Graphiti | Temporal agent knowledge graph | Strong candidate | Incremental graph updates, bi-temporal model, hybrid retrieval | Apache-2.0 | https://github.com/getzep/graphiti | Potential graph subsystem foundation |
| LlamaIndex | RAG/agent/workflow primitives | Reuse selectively | Memory, workflow context, retrieval and agent modules | MIT | https://github.com/run-llama/llama_index | Avoid framework duplication |
| pgvector | Vector similarity | Reuse | Exact/ANN vector search in Postgres | Postgres-compatible | https://github.com/pgvector/pgvector | Good if Postgres is selected |
| Docling | Document understanding | Reuse | PDF/DOCX/PPTX/XLSX/HTML/image parsing, OCR, layout, tables, formulas | MIT | https://github.com/docling-project/docling | Very strong ingestion layer |
| browser-use | Browser agent tooling | Reuse + harden | Agent browser control | Open source | https://github.com/browser-use/browser-use | Run isolated |
| Playwright | Browser automation | Reuse | Deterministic Chromium/WebKit/Firefox automation | Apache-2.0 | https://github.com/microsoft/playwright | Lower-level substrate |
| SymPy | Math engine | Reuse | Symbolic math and deterministic algebra | BSD | https://github.com/sympy/sympy | Store expressions/results in graph |
| OpenTelemetry | Observability | Reuse | Standard traces/metrics/logs | Apache-2.0 | https://github.com/open-telemetry/opentelemetry-python | Use as common telemetry layer |
| Tectonic | LaTeX compiler | Later reuse | LaTeX compilation | Open source | https://github.com/tectonic-typesetting/tectonic | Keep compiler isolated |
| OpenAlex | Scholarly metadata | Integrate | Paper/author/institution/venue metadata | API/CC0 data | https://openalex.org/ | Enrichment/discovery, not source of truth |
| Crossref | Citation metadata | Integrate | DOI and bibliographic metadata | API | https://www.crossref.org/ | Canonicalize citations |
## Sheet: 09_Build_vs_Reuse
| Component | Domain | Recommendation | Effort | Reason |
| --- | --- | --- | --- | --- |
| Notebook/RAG base | Notebook | Adapt | High | Open Notebook already implements core source/RAG workflow |
| Research agent runtime | Agent | Adapt | High | Open Deep Research/STORM/GPT Researcher give strong orchestration patterns |
| Planner | Agent | Adapt + build | High | Planner must emit your typed task/state schema |
| Web search connectors | Tooling | Reuse | Low | Use existing providers/clients |
| Browser worker | Tooling | Reuse + harden | High | browser-use/Playwright |
| PDF/OCR | Document | Reuse | Low | Docling and OCR backends |
| Chunking | Retrieval | Adapt | Medium | Need citation-aware/structure-aware chunking |
| Embeddings | Retrieval | Reuse | Low | Model/provider is replaceable |
| Vector store | Retrieval | Reuse | Low | SurrealDB/pgvector/Qdrant |
| Hybrid ranking | Retrieval | Build | High | Ranking policy is product-specific |
| Grounded graph | Knowledge | Build | Very High | Core product feature |
| Research graph | Knowledge | Build | Very High | Core product feature |
| Graph storage | Infra | Reuse/adapt | Medium | Use existing graph capabilities; own ontology |
| Memory API | Memory | Build | Very High | Unifies multiple memory types |
| Working memory | Memory | Build | High | Task-scoped context is domain specific |
| Semantic memory | Memory | Build + adapt | High | Can borrow retrieval primitives, not semantics |
| Negative memory | Memory | Build | High | Differentiator |
| Procedural memory | Memory | Build + adapt | High | Research workflows need versioning |
| Reflective memory | Memory | Build | High | Learning layer |
| Temporal memory | Memory | Adapt | High | Graphiti/Zep concepts |
| State machine | State | Build | Very High | Canonical lifecycle semantics |
| Checkpointing | State | Reuse + adapt | High | LangGraph/LlamaIndex concepts |
| Event sourcing | State/versioning | Build | Very High | Canonical mutation history |
| Git-like commits | Versioning | Build | Very High | Domain-specific commit object |
| Branches | Versioning | Build | High | Alternative hypotheses/research paths |
| Merge | Versioning | Build | Very High | Need semantic conflict resolution |
| Graph diff | Versioning | Build | High | User-facing lineage |
| Citation extraction | Evidence | Adapt + build | High | Need exact source spans |
| Citation validation | Trust | Build | Very High | Claim-level support is custom |
| Calculation engine | Tools | Reuse | Low | SymPy/NumPy/SciPy |
| Calculation verification | Trust | Reuse + adapt | High | Deterministic replay + provenance |
| Contradiction detection | Trust | Build | High | Knowledge-graph aware |
| Coverage analyzer | Trust | Build | Critical | Output support metrics |
| Scratchpad | Workspace | Build | Medium | Typed and linked |
| Report generator | Artifacts | Adapt | Medium | Markdown/HTML/Pandoc |
| Citation formatter | Artifacts | Reuse | Low | CSL ecosystem |
| LaTeX compiler | Artifacts | Later reuse | Medium | Tectonic/TeXLive |
| Code sandbox | Tools | Reuse + harden | Critical | Untrusted execution |
| Queue | Infra | Reuse | Low | NATS/Redis/RabbitMQ/SQS |
| Object storage | Infra | Reuse | Low | S3-compatible |
| Database | Infra | Reuse + choose | Medium | SurrealDB or Postgres |
| Observability | Infra | Reuse | Medium | OpenTelemetry |
| Auth | Platform | Reuse | Medium | Existing auth provider/library |
| Evaluation harness | Quality | Build + reuse | High | Need research-specific regression datasets |
## Sheet: 10_Research_Lifecycle
| ID | Stage | Purpose | Primary Objects/State | Rule |
| --- | --- | --- | --- | --- |
| R01 | Question intake | Capture question, constraints, scope, output format | ResearchRun + Question | Version the initial specification |
| R02 | Context selection | Select sources, memories, graph slices and conventions | RetrievalState + Memory | Record exact selected context |
| R03 | Mode selection | Ground or Research | SessionState | Mode changes tool policy and answer constraints |
| R04 | Plan generation | Decompose question into research tasks | ResearchRun + Task | Plan itself is versioned |
| R05 | Task scheduling | Construct dependency DAG and budgets | TaskState | Independent tasks may parallelize |
| R06 | Evidence acquisition | Search local/web/scholarly/graph sources | ToolCall + Source + Evidence | Every source is snapshotted |
| R07 | Evidence extraction | Extract claims/entities/tables/equations | EvidenceState + Grounded Graph | Keep exact spans |
| R08 | Hypothesis generation | Create candidate explanations/answers | Hypothesis | Explicitly unverified |
| R09 | Analysis | Compare, calculate, infer and test | Calculation + Finding | All derivations record dependencies |
| R10 | Verification | Check citations/calculations/contradictions | Review + Verification | May create failures/refutations |
| R11 | Graph update | Commit nodes/edges and projections | GraphState | Atomic graph mutation |
| R12 | Memory consolidation | Promote useful episode information | Memory | Do not promote everything |
| R13 | Report synthesis | Generate response/report/artifact | Artifact | Claims link to graph/evidence |
| R14 | Human review | Approve/edit/reject outputs | ReviewState | Edits become events |
| R15 | Workspace commit | Create logical research snapshot | VersionState | Commit includes mutation set |
| R16 | Resume/follow-up | Continue from prior state | Recovery + Memory | No need to restart research |
## Sheet: 11_State_Transitions
| Aggregate | From | To | Trigger | Design Rule |
| --- | --- | --- | --- | --- |
| Task | queued | running | worker claimed | Start event persisted |
| Task | running | blocked | dependency/tool/user blocker | Explicit blocker required |
| Task | running | succeeded | output committed | Atomic output commit |
| Task | running | failed | failure recorded | Failure is persisted data |
| Task | failed | retrying | retry policy | Retry bounded by budget |
| Task | failed | abandoned | policy/human | Generate negative memory candidate |
| Claim | proposed | sourced | evidence linked | Must have source relationship |
| Claim | sourced | supported | support threshold reached | Support is not verification |
| Claim | sourced | disputed | conflict detected | Keep both claims |
| Claim | supported | verified | verification passed | Separate verifier state |
| Claim | supported | superseded | newer claim | Old remains queryable |
| Hypothesis | open | testing | task/experiment created | Must have test path |
| Hypothesis | testing | supported | evidence supports | Record evidence |
| Hypothesis | testing | refuted | evidence refutes | Record reason |
| Evidence | candidate | accepted | provenance valid | Allowed into grounded graph |
| Evidence | accepted | verified | validator passed | Validation metadata retained |
| Evidence | accepted | contradicted | conflict detected | Do not delete original |
| ToolCall | queued | running | worker started | Trace start |
| ToolCall | running | succeeded | result persisted | Immutable result ref |
| ToolCall | running | failed | failure persisted | Classify retryability |
| Artifact | draft | generated | generator finished | Manifest stored |
| Artifact | generated | checked | validation passed | Verification metadata stored |
| Artifact | checked | approved | human approval | Governance event |
| Artifact | approved | published | export/shared | Publication snapshot immutable |
## Sheet: 12_Memory_Routing
| Mode | Task | Preferred Memory | Supporting Sources | Strictness | Output Rule |
| --- | --- | --- | --- | --- | --- |
| Ground | Direct factual answer | Semantic facts + grounded evidence | Current workspace sources | Very high | Only source-backed claims |
| Ground | Citation lookup | Conversation + lexical evidence | Exact fragments/pages | Very high | Prefer exact spans |
| Ground | Follow-up question | Working + conversation recall | Selected source scope | High | No external expansion unless explicitly requested |
| Research | Planning | Episodic + negative + procedural memory | Prior runs and tool lessons | Medium | Use memory to shape plan |
| Research | Source discovery | Semantic + episodic | Workspace + external scholarly/web sources | Medium | Snapshot all external evidence |
| Research | Hypothesis testing | Graph + semantic + temporal memory | Claims/evidence/hypotheses/calculations | High | Graph-first |
| Research | Calculation | Working + structured derived memory | Equations/data/calculation history | Very high | Deterministic verifier required |
| Research | Failure recovery | Negative + episodic + tool experience | Failure graph | High | Avoid repeated dead ends |
| Research | Synthesis | Grounded + research graph + selected artifacts | All verified/qualified objects | High | Label derived/inferred output |
| Both | User preferences | User/project preference memory | User profile/project settings | Low | Never override factual evidence |
| Both | Project vocabulary | Project convention memory | Definitions/notation/assumptions | High | Inject only in scope |
| Both | Temporal question | Temporal memory + source snapshots | Time-aware graph | High | Answer as-of requested time |
## Sheet: 13_Security_Governance
| Concern | Threat / Need | Design | Priority |
| --- | --- | --- | --- |
| Workspace isolation | Cross-user/project leakage | Every object, graph query and vector search requires workspace scope | Critical |
| Prompt injection | Source text attempts to control agent | Treat all retrieved content as untrusted data; isolate instructions | Critical |
| Tool permissions | Agent overreach | Per-run capability tokens and allow/deny policies | Critical |
| Browser isolation | Untrusted websites and sessions | Isolated browser worker with network controls | Critical |
| Code execution | Arbitrary code | Container/VM sandbox, CPU/memory/time limits and network policy | Critical |
| Secrets isolation | API keys exposed to models | Secrets injected only into tool process; never context | Critical |
| Source provenance | Evidence tampering | Hash raw snapshots and normalized fragments | Critical |
| Human override | User edits/approvals | Record actor, time, reason and affected objects | High |
| Model audit | Non-reproducible model behavior | Store provider/model/params/prompt/toolset hashes | High |
| Deletion | Need to remove data | Separate soft-delete, purge and graph cleanup workflows | High |
| Export portability | User owns research | Export sources, graph, commits, memories and artifacts | Medium |
## Sheet: 14_Architecture_Decisions
| ID | Area | Proposed Decision | Why | Status |
| --- | --- | --- | --- | --- |
| D01 | Canonical authority | Event log + versioned objects/graph are canonical; embeddings are derived indexes | Prevents memory/index divergence | Adopt |
| D02 | Epistemic typing | Separate source, extracted, derived, hypothesis, assumption and note types | Prevents derived information becoming fake source fact | Adopt |
| D03 | Two graphs | Grounded graph + Research graph with cross-graph provenance | Matches user's visible research lineage model | Adopt |
| D04 | Graph storage | Start with one multi-model store if query/transaction requirements are met; split only when necessary | Avoid premature distributed complexity | Evaluate |
| D05 | Memory | Multiple typed memories behind one Memory API | Enables intelligent retrieval/routing | Adopt |
| D06 | State | Typed lifecycle state + event sourcing + checkpoints | Supports long-running/resumable research | Adopt |
| D07 | Versioning | Git-like commit/branch/diff/revert; domain-aware merge | Research paths naturally diverge | Adopt |
| D08 | Agent reuse | Reuse open research-agent patterns but own state/provenance contract | Avoid hard framework lock-in | Adopt |
| D09 | Failures | Failures are graph objects and negative memories | Agent learns what not to repeat | Adopt |
| D10 | Context assembly | Separate retrieval, memory selection and runtime state compilation | Prevents hidden context behavior | Adopt |
| D11 | Verification | Separate support from verification | A source can support a claim without proving it | Adopt |
| D12 | Temporal facts | Store valid_at, observed_at, invalidated/superseded metadata | Research state evolves | Adopt |
| D13 | Scratchpad | Typed and linkable but lower trust than evidence | Human reasoning remains visible without contaminating knowledge | Adopt |
| D14 | Artifacts | Every artifact stores source commit and generator manifest | Enables reproducibility | Adopt |
## Sheet: 15_Implementation_Phases
| Phase | Name | Scope | Exit Criteria | Complexity |
| --- | --- | --- | --- | --- |
| P0 | Foundation | Fork/adapt Open Notebook, establish IDs, workspace, storage, auth boundary | Stable workspace and source ingestion | High |
| P1 | Evidence substrate | Ingestion, Docling parsing, source snapshots, fragments, citations, embeddings, hybrid retrieval | Grounded graph can populate | High |
| P2 | Two graphs | Graph ontology, grounded/research graphs, typed edges, provenance projections | User can inspect lineage | Very High |
| P3 | Memory fabric | Working/episodic/semantic/negative/procedural/reflective/temporal memory + routing API | Agent recalls intelligently | Very High |
| P4 | State engine | Run/task states, checkpoints, events and recovery | Long-running research resumes | Very High |
| P5 | Agent integration | Planner, workers, web/scholar/math/browser tools | Research mode works end-to-end | High |
| P6 | Versioning | Commits, branches, diffs, revert, reproducibility manifests | Research is reproducible | Very High |
| P7 | Trust | Citation validation, calculation verification, contradiction detection, coverage | High-trust answers | High |
| P8 | Human collaboration | Scratchpad, review queues, approvals and notes | Human-AI research loop | Medium |
| P9 | Artifacts | Reports, BibTeX, exports and figures | End-to-end outputs | Medium |
| P10 | Advanced | Temporal graph, tool experience, learned procedures, LaTeX compiler | Long-term differentiation | High |