# 11: Working Memory State Engine (Ephemeral Scratchpad)

**What to build:** Implement the `WorkingMemory` layer using LangGraph state schemas and reducers. This acts as an ephemeral scratchpad where agents can hold temporary reasoning context, pinned evidence, and active hypotheses without persisting them directly to the canonical database.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Define LangGraph `StateGraph` and Pydantic schema for `WorkingMemoryState`
- [ ] Implement state reducers for appending scratchpad thoughts and pinning evidence
- [ ] Configure an ephemeral checkpoint saver (e.g., in-memory or Redis-backed)
- [ ] Create tests proving the state can be mutated without hitting the canonical Postgres tables
