# 12: Episodic Memory Compressor

**What to build:** An `EpisodicMemory` pipeline that takes a completed `WorkingMemory` log and compresses it into a high-level semantic summary using an LLM. This summary is then saved to Postgres so future agents can recall past failures and decisions without injecting 100k tokens into their prompt context.

**Blocked by:** 11: Working Memory State Engine

**Status:** ready-for-agent

- [ ] Alembic migration and SQLAlchemy model for `episodic_memories` table
- [ ] `EpisodicMemoryService` pipeline configured with an LLM prompt for summarization
- [ ] Pipeline accepts a terminal `WorkingMemoryState` and extracts key failures/decisions
- [ ] Summary is persisted to the `episodic_memories` table via repository
- [ ] Integration test using a mocked LLM gateway to verify compression flow
