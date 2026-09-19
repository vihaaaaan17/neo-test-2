# GATES: 02: Unified Research Repository

- [x] Create `app/repositories/research.py` with CRUD for ResearchEvidence.
  - CHECK: `cat app/repositories/research.py | grep create_evidence | wc -l`
  - EXPECT: `>0`
  - EVIDENCE: 1

- [x] Implement CRUD for ResearchArtifact.
  - CHECK: `cat app/repositories/research.py | grep create_artifact | wc -l`
  - EXPECT: `>0`
  - EVIDENCE: 1

- [x] Implement CRUD for ResearchReport.
  - CHECK: `cat app/repositories/research.py | grep create_report | wc -l`
  - EXPECT: `>0`
  - EVIDENCE: 1

- [x] Implement CRUD for ResearchUsage.
  - CHECK: `cat app/repositories/research.py | grep create_usage | wc -l`
  - EXPECT: `>0`
  - EVIDENCE: 1

- [x] Implement CRUD for ResearchEvent.
  - CHECK: `cat app/repositories/research.py | grep create_event | wc -l`
  - EXPECT: `>0`
  - EVIDENCE: 1

- [x] Write integration tests enforcing cross-workspace isolation.
  - CHECK: `pytest tests/integration/research/test_repository.py`
  - EXPECT: `passed`
  - EVIDENCE: 3 passed in 3.58s
