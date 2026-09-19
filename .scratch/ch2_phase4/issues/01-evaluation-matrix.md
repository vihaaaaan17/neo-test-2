# 01: Phase 4 Evaluation Matrix & Baseline CI Gating

**What to build:** The explicit, offline Pytest Integration Matrix running against the real Open Notebook dependency. This ensures all functional requirements (provenance, tenant isolation, streaming, backpressure, circuit-breaker) pass reliably, acting as the hard production-readiness gate before cutover.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Create or expand integration tests in `tests/integration/test_phase4_evaluation.py` (or existing files).
- [ ] Test multi-source grounding and provenance tracking correctly handles missing/unmapped evidence.
- [ ] Test tenant isolation (requests for Workspace A cannot access Workspace B via Open Notebook).
- [ ] Test the streaming SSE interface reliability and data shapes.
- [ ] Test Circuit Breaker triggering and recovery against the real dependency mock.
- [ ] Verify the full evaluation test suite passes consistently.
