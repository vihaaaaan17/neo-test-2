# 05: Production Hardening + Contracts + E2E

**What to build:**
Harden production runtime hygiene, synchronize handoff documentation, and deliver comprehensive true end-to-end integration tests for Chapter 4. Populate real metrics (tokens, tool call counts, latency) in `ResearchMetricsService`, enforce UTC timestamps across all operations, manage checkpointer lifecycles cleanly, and scope reconciliation scripts strictly to the target workspace. Synchronize `chapter4-api-contract.md`, `chapter4-event-catalog.md`, `chapter4-state-model.md`, and `chapter4-ui-handoff.md` to match the canonical implementation (standard error envelope, terminal event definitions, unified lifecycle enums, and version read APIs). Provide high-fidelity integration tests using real ASGI HTTP, PostgreSQL, and Redis verifying the complete Ground, Research, Promotion, Rollback, and Fencing flows with 100% CI pass rate.

**Blocked by:** 01: Ground + Streaming Fabric, 02: Turn + Event Concurrency, 03: Timeline + Promotion + Graph, 04: Rollback + State Integrity + Legacy

**Status:** completed

- [x] Research metrics are populated with real runtime execution values and all timestamps use `timezone.utc`.
- [x] Checkpointer lifecycle and reconciliation scripts are safely scoped without leaking cross-workspace state.
- [x] Frozen handoff documents match the exact implementation and TypeScript contracts.
- [x] End-to-end tests verify Ground source containment, SSE reconnection, timeline fencing, and rollback visibility without mock shortcuts.
- [x] Complete test suite passes with 100% success on GitHub Actions CI.
