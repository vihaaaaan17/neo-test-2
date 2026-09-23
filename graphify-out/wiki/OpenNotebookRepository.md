# OpenNotebookRepository

> 35 nodes · cohesion 0.11

## Key Concepts

- **OpenNotebookRepository** (15 connections) — `repositories/open_notebook.py`
- **UUID** (10 connections)
- **OpenNotebookSourceBinding** (9 connections) — `models/open_notebook_binding.py`
- **OpenNotebookWorkspaceBinding** (9 connections) — `models/open_notebook_binding.py`
- **DeletionTombstone** (8 connections) — `models/open_notebook_binding.py`
- **map_citations()** (7 connections) — `integrations/open_notebook/citation_mapper.py`
- **OpenNotebookGroundEngine** (7 connections) — `integrations/open_notebook/ground_engine.py`
- **.get_workspace_binding()** (6 connections) — `repositories/open_notebook.py`
- **.get_source_binding()** (5 connections) — `repositories/open_notebook.py`
- **.update_projection_status()** (5 connections) — `repositories/open_notebook.py`
- **.run()** (4 connections) — `integrations/open_notebook/ground_engine.py`
- **open_notebook_binding.py** (4 connections) — `models/open_notebook_binding.py`
- **Base** (4 connections)
- **.claim_projection_job()** (4 connections) — `repositories/open_notebook.py`
- **.create_tombstone_and_delete_source_binding()** (4 connections) — `repositories/open_notebook.py`
- **.create_workspace_binding()** (4 connections) — `repositories/open_notebook.py`
- **.get_active_projections_for_source()** (4 connections) — `repositories/open_notebook.py`
- **ground_engine.py** (3 connections) — `integrations/open_notebook/ground_engine.py`
- **.__init__()** (3 connections) — `integrations/open_notebook/ground_engine.py`
- **UUID** (3 connections)
- **OpenNotebookConversationBinding** (3 connections) — `models/open_notebook_binding.py`
- **.delete_workspace_binding()** (3 connections) — `repositories/open_notebook.py`
- **.get_notebook_id_for_workspace()** (3 connections) — `repositories/open_notebook.py`
- **citation_mapper.py** (2 connections) — `integrations/open_notebook/citation_mapper.py`
- **UUID** (2 connections)
- *... and 10 more nodes in this community*

## Relationships

- [workspaces.py](workspaces.py.md) (4 shared connections)
- [WorkspaceRepository](WorkspaceRepository.md) (3 shared connections)
- [tasks.py](tasks.py.md) (3 shared connections)
- [OpenNotebookClient](OpenNotebookClient.md) (2 shared connections)
- [Source](Source.md) (1 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)
- [GroundModeOrchestrator](GroundModeOrchestrator.md) (1 shared connections)

## Source Files

- `integrations/open_notebook/citation_mapper.py`
- `integrations/open_notebook/ground_engine.py`
- `models/open_notebook_binding.py`
- `repositories/open_notebook.py`

## Audit Trail

- EXTRACTED: 58 (73%)
- INFERRED: 21 (27%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*