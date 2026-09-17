# Scalability & Migration Ledger

This document tracks all temporary "Phase 1-4" shortcuts made for speed or free-tier constraints, detailing exactly how, where, and when to migrate them to hit the 1000-user production benchmark.

## Phase 1 & 2: Memory & State Fabric

### 1. In-Memory / SQLite Checkpointer -> Durable Redis/Postgres Checkpointer
- **Current State**: LangGraph might be defaulting to `MemorySaver` or an in-memory SQLite store during tests. 
- **Migration Path**: 
  - **File**: `app/orchestration/checkpointer.py` (or where LangGraph is initialized).
  - **Action**: Replace `MemorySaver()` with `AsyncPostgresSaver` (from `langgraph-checkpoint-postgres`) using the existing Supabase Postgres connection pool.
  - **Function**: Update the DI dependency `get_checkpointer()`.

### 2. Local File Uploads -> S3 Object Storage
- **Current State**: `ObjectStore` might be writing PDFs to a local `./tmp` directory for parsing.
- **Migration Path**: 
  - **File**: `app/services/object_store.py`.
  - **Action**: Implement `S3ObjectStore` using `aioboto3`. Route all file bytes directly to Supabase Storage or AWS S3. 

## Phase 3: Internal KG & Ground Mode

### 3. Local Docker Neo4j -> Neo4j Aura (Managed Cluster)
- **Current State**: We rely on `docker-compose.yml` spinning up a local Neo4j Community Edition container on `localhost:7687`.
- **Migration Path**:
  - **File**: `app/core/config.py` and `docker-compose.yml`.
  - **Action**: Update `NEO4J_URI` to point to `neo4j+s://<instance>.databases.neo4j.io`. No application code needs to change, just connection credentials.

### 4. Raw SQL RRF -> Qdrant / Dedicated Vector DB
- **Current State**: `app/services/hybrid_retrieval.py` executes a raw Postgres query joining `to_tsquery` and `pgvector` `<=>` distance.
- **Migration Path**:
  - **File**: `app/services/hybrid_retrieval.py`.
  - **Action**: At ~1M chunks, Postgres RRF will slow down. Introduce a new class `QdrantRetrievalService` inheriting from a `RetrievalBase` interface. Dual-write chunks to Postgres and Qdrant, then flip the read path.

## Phase 4: Research Mode & Output KG

### 5. Tavily Search API -> Playwright Headless Cluster
- **Current State**: Relying on Tavily's LLM-optimized search API (`TavilySearchResults` or direct HTTP calls).
- **Migration Path**:
  - **File**: `app/tools/web_search.py` (to be created).
  - **Action**: Replace the Tavily call with a custom Playwright scraping cluster (e.g., using `Browserbase` or a custom Kubernetes deployment) to avoid Tavily rate limits and costs at scale. You'll need to write a custom DOM-to-Markdown parser.

### 6. Local Neo4j Output Graph Projection -> Federated Neo4j Projection
- **Current State**: The user-facing "Curated Graph" is projected into the same local Neo4j Community Edition instance as the internal KG, isolated merely by labels (`OutputNode`).
- **Migration Path**:
  - **File**: `app/orchestration/research_mode.py` and `app/repositories/graph.py`.
  - **Action**: When users need strict physical tenant isolation or federated graph capabilities across workspaces, you will need to push this curated graph into a dedicated Neo4j instance or a completely separate Aura database endpoint.
