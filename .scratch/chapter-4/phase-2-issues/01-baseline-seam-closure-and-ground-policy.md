# 01: Baseline Seam Closure & Context Policy Boundary (Ground Isolation)

**What to build:**
A unified conversational entry point for legacy research runs and a formal, verifiable policy boundary that strictly isolates Ground mode from Research-derived state. Ground mode will be able to retrieve multi-turn context only from prior Ground turns, completely ignoring Research turns. Additionally, Ground answers will persist strictly to conversation turns and evidence references, without creating durable knowledge memory records or triggering graph synchronization.

**Blocked by:** None (can start immediately)

**Status:** closed-done

- [x] Legacy `POST /workspaces/{workspace_id}/research` delegates to `ChatService.submit_turn(mode="research")`
- [x] If `conversation_id` is passed in legacy research request, it appends to that conversation; if omitted, it automatically creates a dedicated canonical `Conversation` titled `Research: <objective[:40]>...`
- [x] `TurnCreate` in `app/schemas/chat.py` includes optional fields `selected_source_ids: Optional[List[UUID]] = None` and `research_options: Optional[Dict[str, Any]] = None`
- [x] `app/services/memory/policy.py` implements `GroundContextPolicy` and `ResearchContextPolicy`
- [x] Ground policy explicitly denies `KnowledgeMemory`, `ResearchEvidence`, `ResearchReport`, `OutputGraph`, `ScratchpadEntry`, and unverified candidates
- [x] `app/services/chat/context.py` implements `build_ground_context()` and `resolve_ground_source_scope()`
- [x] Ground multi-turn execution filters conversation turns strictly by `mode == "ground"`, stripping all Research turns from Open Notebook context
- [x] Ground answer execution in `ChatService._execute_ground_turn` and legacy routes does NOT create `KnowledgeMemory` or enqueue `sync_knowledge_to_graph_job`
- [x] Unit and isolation tests in `tests/unit/memory/test_policy.py`, `tests/unit/chat/test_ground_context.py`, and `tests/unit/api/test_research_route_delegation.py` pass 100% (9/9 passed)
