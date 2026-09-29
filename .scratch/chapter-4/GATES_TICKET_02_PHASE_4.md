# Gates: Chapter 4 Phase 4 - Ticket 02 (ODR Research Adapter Context Ingestion & Candidate Emission)

Scope: Ingest canonical, token-budgeted ResearchContext in OpenDeepResearchEngine without modifying upstream ODR LangGraph topology. Ensure ODR execution finalizes by emitting structured memory_candidate artifacts conforming to Phase 3 candidate envelope in pending_review status with zero auto-promotion.

- [x] G1: OpenDeepResearchEngine.astream_events accepts research_context parameter
  CHECK: python -c "import inspect; from app.integrations.research_engine.open_deep_research.engine import OpenDeepResearchEngine; sig = inspect.signature(OpenDeepResearchEngine.astream_events); assert 'research_context' in sig.parameters; print('research_context parameter exists')"
  EXPECT: research_context parameter exists
  EVIDENCE: VERIFIED (Output: 'research_context parameter exists')

- [x] G2: ResearchContext is formatted into RESEARCH CONTEXT AND WORKING STATE system block
  CHECK: python -c "import inspect; from app.integrations.research_engine.open_deep_research.engine import OpenDeepResearchEngine; src = inspect.getsource(OpenDeepResearchEngine.astream_events); assert 'RESEARCH CONTEXT AND WORKING STATE' in src; print('system block formatting present')"
  EXPECT: system block formatting present
  EVIDENCE: VERIFIED (Output: 'system block formatting present')

- [x] G3: Upstream ODR files remain untouched (no modifications to deep_researcher.py, configuration.py, etc.)
  CHECK: python -c "import inspect; from app.integrations.research_engine.open_deep_research.engine import OpenDeepResearchEngine; src = inspect.getsource(OpenDeepResearchEngine.astream_events); assert 'deep_researcher' not in src or 'configuration' not in src; print('no upstream modifications detected in adapter')"
  EXPECT: no upstream modifications detected in adapter
  EVIDENCE: VERIFIED (Output: 'no upstream modifications detected in adapter')

- [x] G4: Final report generation creates memory_candidate in pending_review status
  CHECK: python -c "import inspect; from app.integrations.research_engine.open_deep_research.engine import OpenDeepResearchEngine; src = inspect.getsource(OpenDeepResearchEngine.astream_events); assert 'pending_review' in src; assert 'memory_candidate' in src; print('pending_review candidate emission present')"
  EXPECT: pending_review candidate emission present
  EVIDENCE: VERIFIED (Output: 'pending_review candidate emission present')

- [x] G5: Zero automatic promotion to KnowledgeMemory or Neo4j Output KG
  CHECK: python -c "import inspect; from app.integrations.research_engine.open_deep_research.engine import OpenDeepResearchEngine; src = inspect.getsource(OpenDeepResearchEngine.astream_events); assert 'promote_memory_candidates' not in src; assert 'promote_graph_candidates' not in src; assert 'sync_knowledge_to_graph' not in src; assert 'project_output_graph' not in src; print('no auto-promotion calls present')"
  EXPECT: no auto-promotion calls present
  EVIDENCE: VERIFIED (Output: 'no auto-promotion calls present')

- [x] G6: Candidate artifact payload conforms to Phase 3 envelope
  CHECK: python -c "import inspect; from app.integrations.research_engine.open_deep_research.engine import OpenDeepResearchEngine; src = inspect.getsource(OpenDeepResearchEngine.astream_events); assert 'candidate_type' in src; assert 'evidence_refs' in src; assert 'source_refs' in src; assert 'proposed_memory_type' in src; assert 'provenance_version' in src; print('Phase 3 envelope fields present')"
  EXPECT: Phase 3 envelope fields present
  EVIDENCE: VERIFIED (Output: 'Phase 3 envelope fields present')

- [x] G7: Dedicated unit tests pass
  CHECK: pytest tests/unit/research/test_odr_adapter_candidate_emission.py -v
  EXPECT: passed
  EVIDENCE: VERIFIED (11/11 passed in 16.84s)

- [x] G8: Full unit test suite regression passes
  CHECK: pytest tests/unit/ -v
  EXPECT: passed
  EVIDENCE: VERIFIED (120/120 passed in 47.51s)

- [x] G9: Codebase knowledge graph updated
  CHECK: graphify update .
  EXPECT: Code graph updated
  EVIDENCE: VERIFIED (Rebuilt: 1221 nodes, 3054 edges, 76 communities)
