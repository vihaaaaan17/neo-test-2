# workspaces.py

> 25 nodes · cohesion 0.17

## Key Concepts

- **workspaces.py** (23 connections) — `api/routes/workspaces.py`
- **UUID** (14 connections)
- **ask_ground_mode()** (11 connections) — `api/routes/workspaces.py`
- **chat_ground_mode()** (11 connections) — `api/routes/workspaces.py`
- **start_research()** (10 connections) — `api/routes/workspaces.py`
- **AsyncSession** (9 connections)
- **ask_ground_mode_stream()** (8 connections) — `api/routes/workspaces.py`
- **post** (8 connections)
- **get_projection_status()** (7 connections) — `api/routes/workspaces.py`
- **create_workspace()** (6 connections) — `api/routes/workspaces.py`
- **GroundEngineProtocol** (6 connections) — `services/ground/factory.py`
- **create_workspace_commit()** (5 connections) — `api/routes/workspaces.py`
- **delete_workspace()** (5 connections) — `api/routes/workspaces.py`
- **get_memory_router()** (5 connections) — `api/routes/workspaces.py`
- **rollback_workspace()** (5 connections) — `api/routes/workspaces.py`
- **get_workspace()** (4 connections) — `api/routes/workspaces.py`
- **ArqRedis** (4 connections)
- **get_knowledge_repository()** (3 connections) — `api/routes/workspaces.py`
- **get_quota()** (3 connections) — `api/routes/workspaces.py`
- **get_research_repository()** (3 connections) — `api/routes/workspaces.py`
- **get_source_repository()** (3 connections) — `api/routes/workspaces.py`
- **get_workspace_repository()** (3 connections) — `api/routes/workspaces.py`
- **get** (3 connections)
- **delete** (1 connections)
- **Protocol** (1 connections)

## Relationships

- [WorkspaceRepository](WorkspaceRepository.md) (11 shared connections)
- [run_research_agent_job](run_research_agent_job.md) (7 shared connections)
- [Source](Source.md) (5 shared connections)
- [schemas/workspace.py](schemas-workspace.py.md) (5 shared connections)
- [upload_file_to_workspace](upload_file_to_workspace.md) (4 shared connections)
- [GroundModeOrchestrator](GroundModeOrchestrator.md) (4 shared connections)
- [OpenNotebookRepository](OpenNotebookRepository.md) (4 shared connections)
- [AskRequest](AskRequest.md) (3 shared connections)
- [QuotaService](QuotaService.md) (3 shared connections)
- [FastAPI](FastAPI.md) (2 shared connections)
- [ChatRequest](ChatRequest.md) (2 shared connections)
- [ResearchRepository](ResearchRepository.md) (2 shared connections)

## Source Files

- `api/routes/workspaces.py`
- `services/ground/factory.py`

## Audit Trail

- EXTRACTED: 92 (84%)
- INFERRED: 17 (16%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*