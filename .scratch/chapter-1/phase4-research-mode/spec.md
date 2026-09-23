**Status:** ready-for-agent

## Problem Statement
When triggering a deep, autonomous research run, researchers want the agent to independently search the web, plan its methodology, and synthesize a comprehensive set of curated findings. They need visibility into the agent's real-time thoughts (even when jobs take several minutes), the ability to visually map the final curated findings, and the safety to roll back their workspace if the autonomous agent pollutes it with bad data.

## Solution
Phase 4 implements "Research Mode," an autonomous agent loop (based on STORM/Open Deep Research patterns) capable of long-running web exploration using Tavily. 

Because autonomous research takes minutes, we will not block the main API thread. Instead, runs will execute asynchronously via `arq` background jobs. To provide a ChatGPT/Claude-like UX (where the user sees real-time "thoughts" such as "Searching the web..." or "Reading 5 sources..."), we will stream LangGraph events using Server-Sent Events (SSE) backed by a Redis Pub/Sub backplane. 

The output of the research run is a curated "Research Output KG". Per the architecture, this is logically a distinct second graph from the internal KG. It will be projected into Neo4j using specific semantic labels (e.g., `OutputNode`, `[:DERIVES_FROM]`). Crucially, the nodes in this graph will be enriched with deep provenance bundles—so if a user hovers over a claim like "18% efficiency increase," the graph can render exactly which papers/pages it was derived from, the exact mathematical calculation used, and its verification status.

## User Stories

1. As a researcher, I want to trigger an autonomous "Research Mode" run with a broad objective, so that the agent can autonomously plan and search for answers.
2. As a frontend client, I want to connect to a streaming SSE endpoint (`/api/v1/jobs/{job_id}/stream`), so that I can render a ChatGPT-style "thinking" UI (e.g., "Searching the web...", "Synthesizing...") to keep the user engaged while the background agent runs.
3. As an engineer, I want the autonomous LangGraph execution to be offloaded to an `arq` background worker, so that long-running web searches do not block Uvicorn worker threads.
4. As a researcher, I want the system to generate a clean "Research Output Graph" at the end of the run, so that I can visually explore the curated claims and evidence without wading through operational noise.
5. As a researcher, I want the nodes in the Output Graph to contain deep provenance bundles, so that if I hover over a derived claim (like a calculation), I can see the exact sources, pages, equations, and verification status.
6. As a researcher, I want to create a "Snapshot" of my workspace before running an autonomous agent, so that if the agent goes down a rabbit hole, I can easily roll back my workspace to the exact state of knowledge memory it had prior.
7. As a system administrator, I want the web search tool to use the Tavily API, so that we avoid complex scraping infrastructure and rate-limiting overhead during this phase.

## Implementation Decisions

- **Async Agent Execution**: The `POST /api/v1/workspaces/{id}/research` endpoint will not await the LangGraph run. Instead, it will immediately enqueue an `arq` job and return a `202 Accepted` with a `job_id`.
- **SSE + Redis Pub/Sub (ChatGPT-style UX)**: The `arq` LangGraph worker will use `astream_events()` to emit granular agent steps (e.g., tool calls, node transitions). A lightweight publisher pushes these to a Redis channel (`research:{job_id}`). A FastAPI route `GET /api/v1/jobs/{job_id}/stream` subscribes to this and yields `text/event-stream` SSE payloads. The frontend interprets these streams to show animated, real-time "thinking" states.
- **Neo4j Output Graph Projection**: The curated graph (Research Output KG) is a core USP. Instead of a flat JSON file, we will strictly follow the architecture and project this graph into Neo4j. To avoid spinning up a second physical cluster on the free tier, we will store it in the same local Neo4j database but strictly isolate it using labels (e.g., `OutputNode` and `[:EXPLAINS]`). 
- **Deep Provenance Bundles**: The agent will explicitly bundle `Citation/Provenance` metadata into the Output Graph nodes. Properties like `derived_from_refs` (pointing to chunks/pages), `calculation`, and `verification_status` will be attached directly to the Neo4j nodes so the frontend can render rich hover-cards.
- **Snapshot Versioning**: We will not build a full event-sourced rollback log. We will implement "Snapshot Versioning". A new Postgres table `workspace_commits` will store `(commit_id, parent_id, active_knowledge_ids=[...])`. A rollback simply points the workspace back to an older `commit_id`, effectively isolating the context window from unwanted memories.
- **Web Search**: The agent will be provided with a `WebSearchTool` backed by the `Tavily` API.

## Updates to Previous Phases (Phase 3 Refactors)
To support the Output KG and deep provenance, we must update the following Phase 3 components:
- **`app/repositories/graph.py` (`GraphRepository`)**: Update the Neo4j adapter to support writing `OutputNode` and `OutputEdge` labels, ensuring it does not collide with the `InternalNode` data. We must also update the Cypher queries to support storing nested JSON metadata (the provenance bundles, `calculation`, `verification_status`) directly as node properties.
- **`app/schemas/graph.py`**: Introduce new Pydantic models for `OutputGraphNode` and `ProvenanceBundle` that enforce the schema required for the interactive hover-cards.
- **`app/workers/tasks.py`**: Add a new `project_output_graph_job` alongside the existing `sync_knowledge_to_graph_job` to handle asynchronously projecting the LLM's final research output into Neo4j.

## Testing Decisions

- **Good Tests**: Tests should only verify external behavior. We will mock the Tavily API to return deterministic JSON results to prevent flaky network tests.
- **Modules Tested**: `app/orchestration/research_mode.py`, `app/api/routes/jobs.py` (SSE streaming), and `app/repositories/versioning.py`.
- **Prior Art**: We will mimic the dependency injection overrides used in `test_ground_mode_api.py` to seamlessly mock the `llm_gateway` and `search_gateway`.

## Out of Scope
- Playwright/Selenium headless scraping clusters (we are relying entirely on Tavily for now, tracked in `SCALING_MIGRATIONS.md`).
- Multi-database Neo4j federation.
- Real-time collaborative graph editing (the output graph is read-only).

## Further Notes
- We have created a `SCALING_MIGRATIONS.md` ledger to meticulously track temporary architectural bypasses (like relying on SQLite Checkpointer, local Neo4j, or Tavily) so that when the system scales to 1000 users, the migration paths are exhaustively mapped out.
