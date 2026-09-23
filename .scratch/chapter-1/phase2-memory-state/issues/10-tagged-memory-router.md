# 10: Tagged Memory Router (Provenance Enforcement)

**What to build:** A `MemoryRouter` service that intercepts all pushes to canonical `Knowledge Memory`. It enforces that a valid tag (`source_mode="ground"` or `"research"`) and explicit source citations are attached to every memory object before saving it to the database, ensuring perfect provenance tracking.

**Blocked by:** 09: Canonical Knowledge Memory Models

**Status:** ready-for-agent

- [ ] `MemoryRouter` service created
- [ ] Router validates that `source_mode` exists and is strictly either `ground` or `research`
- [ ] Router delegates valid memory objects to `KnowledgeRepository` for persistence
- [ ] Unit tests verify that untagged memories are rejected and tagged memories are isolated correctly
