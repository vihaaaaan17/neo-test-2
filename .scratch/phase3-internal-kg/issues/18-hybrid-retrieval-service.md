# 18: Postgres FTS & Hybrid Retrieval Service

**What to build:** A `HybridRetrievalService` that merges keyword searches (via Postgres Full-Text Search) with semantic searches (via `pgvector`). This requires adding `tsvector` indexed columns to our `document_blocks` to make keyword lookups fast and scalable at the 1000-user mark.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Alembic migration adds `tsvector` columns and Generalized Inverted Indexes (GIN) to `document_blocks`.
- [ ] A `HybridRetrievalService` is implemented in `app/services/hybrid_retrieval.py`.
- [ ] The service executes a fused search (e.g. Reciprocal Rank Fusion) combining `pgvector` similarity and FTS matching.
- [ ] All retrieval queries are strictly scoped by `workspace_id` to enforce tenant isolation.
- [ ] Unit tests verify that the service returns a combined, ranked list of chunks.
