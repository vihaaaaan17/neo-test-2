# 14: AsyncPostgresSaver Checkpointing

**What to build:** Replaces the process-local MemorySaver in ODR with LangGraph's AsyncPostgresSaver for production, gated behind a feature flag so local dev can still use in-memory.

**Blocked by:** 01: Canonical ResearchRun Creation API

**Status:** ready-for-agent

- [ ] Acceptance criterion 1
- [ ] Acceptance criterion 2
