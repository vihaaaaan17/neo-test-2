# 19: Graph Synchronization Worker (`arq`)

**What to build:** An `arq` background job that synchronizes newly created Canonical `KnowledgeMemory` entries in Postgres into nodes and edges in the Neo4j Internal KG. This offloads the graph creation latency from the core API endpoints.

**Blocked by:** 17

**Status:** done

- [x] A new `sync_knowledge_to_graph` task is registered in `app/workers/tasks.py`.
- [x] The `MemoryRouter` (or relevant repository) triggers this task asynchronously via the Redis queue whenever a new memory object is created.
- [x] The background task reads the memory object from Postgres and upserts corresponding nodes and edges into Neo4j via the `GraphStore`.
- [x] The task is idempotent (re-running it on the same memory ID updates existing nodes rather than duplicating them).
