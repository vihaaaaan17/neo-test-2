# GATES: 03: Lifecycle & Event Service

- [x] Create `app/services/research/lifecycle.py`.
  - CHECK: `cat app/services/research/lifecycle.py | grep ResearchLifecycleService | wc -l`
  - EXPECT: `>0`
  - EVIDENCE: 1

- [x] Implement state validation for `ResearchRun`.
  - CHECK: `cat app/services/research/lifecycle.py | grep "def transition_run" | wc -l`
  - EXPECT: `>0`
  - EVIDENCE: 1

- [x] Implement state validation for `ResearchTask`.
  - CHECK: `cat app/services/research/lifecycle.py | grep "def transition_task" | wc -l`
  - EXPECT: `>0`
  - EVIDENCE: 1

- [x] Emit `ResearchEvent` automatically on transitions.
  - CHECK: `cat app/services/research/lifecycle.py | grep create_event | wc -l`
  - EXPECT: `>0`
  - EVIDENCE: 2

- [x] Write unit tests verifying state transitions.
  - CHECK: `pytest tests/unit/services/research/test_lifecycle.py`
  - EXPECT: `passed`
  - EVIDENCE: 5 passed in 2.71s
