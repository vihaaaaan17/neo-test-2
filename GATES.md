# GATES: 05: Research Service Coordinator

- [x] Create `app/services/research/service.py`.
  - CHECK: `cat app/services/research/service.py | grep ResearchService | wc -l`
  - EXPECT: `>0`
  - EVIDENCE: 1

- [x] Implement memory promotion logic (`route_to_memory`).
  - CHECK: `cat app/services/research/service.py | grep promote_memory_candidates | wc -l`
  - EXPECT: `>0`
  - EVIDENCE: 1

- [x] Implement graph promotion logic (`project_output_graph`).
  - CHECK: `cat app/services/research/service.py | grep promote_graph_candidates | wc -l`
  - EXPECT: `>0`
  - EVIDENCE: 1

- [x] Write integration tests verifying promotion correctly dispatches.
  - CHECK: `pytest tests/integration/research/test_service.py`
  - EXPECT: `passed`
  - EVIDENCE: 2 passed in 5.68s
