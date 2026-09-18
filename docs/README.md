# NeosisLM Documentation

Welcome to the NeosisLM documentation! NeosisLM is an advanced, multi-agent AI research platform designed to combine source-grounded memory (NotebookLM style) with autonomous deep-research capabilities (Open Deep Research style) over a unified memory and state fabric.

## Table of Contents

1. [Architecture Overview](architecture.md)
   * High-level system design, graphs, storage layers, and domain boundaries.
2. [Local Setup & Development](setup.md)
   * How to start the FastAPI server, Arq background workers, and the Streamlit test UI.
3. [Agents & Orchestrators](orchestrators.md)
   * Deep dive into the `ResearchModeOrchestrator` and `GroundModeOrchestrator` using LangGraph.
4. [API & Integrations](api.md)
   * Overview of the FastAPI routes, Workspace management, and background jobs.
5. [Scaling & Migrations](migrations.md)
   * Operational guide for schema evolution, scaling out the database, and managing background workers.

## Core Philosophy

NeosisLM is built with strict, production-ready engineering standards:
- **Provider Agnostic**: LLMs (via LiteLLM), Object Stores (S3 compatible), and Vector DBs are abstracted.
- **Strict Tenant Isolation**: All data is strictly separated by `workspace_id` using Row-Level Security and explicit code validation.
- **Two-Graph Design**: An internal operational Postgres/Neo4j graph for exhaustive knowledge, and a curated Semantic Output graph for users.
- **Asynchronous Execution**: Heavy tasks (Agent execution, workspace exports, data parsing) are completely offloaded to Redis/Arq background workers.
