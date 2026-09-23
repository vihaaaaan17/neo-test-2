# 18: Postgres FTS & Hybrid Retrieval Service

**What to build:** A `HybridRetrievalService` that merges keyword searches (via Postgres Full-Text Search) with semantic searches (via `pgvector`). This requires adding `tsvector` indexed columns to our `document_blocks` to make keyword lookups fast and scalable at the 1000-user mark.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Alembic migration adds `tsvector` columns and Generalized Inverted Indexes (GIN) to `document_blocks`.
- [x] A `HybridRetrievalService` is implemented in `app/services/hybrid_retrieval.py`.
- [x] The service executes a fused search (e.g. Reciprocal Rank Fusion) combining `pgvector` similarity and FTS matching.
- [x] All retrieval queries are strictly scoped by `workspace_id` to enforce tenant isolation.
- [x] Unit tests verify that the service returns a combined, ranked list of chunks.
