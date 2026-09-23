# run_research_agent_job

> 60 nodes · cohesion 0.05

## Key Concepts

- **run_research_agent_job()** (13 connections) — `workers/tasks.py`
- **KnowledgeRepository** (11 connections) — `repositories/knowledge.py`
- **KnowledgeMemory** (10 connections) — `models/knowledge.py`
- **MemoryRouter** (10 connections) — `services/memory_router.py`
- **ResearchService** (9 connections) — `services/research/service.py`
- **GraphRepository** (8 connections) — `repositories/graph.py`
- **GraphStore** (7 connections) — `repositories/graph.py`
- **OutputGraph** (7 connections) — `schemas/graph.py`
- **KnowledgeMemoryCreate** (7 connections) — `schemas/knowledge.py`
- **.promote_graph_candidates()** (7 connections) — `services/research/service.py`
- **.get_output_graph()** (6 connections) — `repositories/graph.py`
- **Neo4jAdapter** (6 connections) — `repositories/graph.py`
- **.synthesizer_node()** (5 connections) — `orchestration/research_mode.py`
- **repositories/graph.py** (5 connections) — `repositories/graph.py`
- **.route_to_memory()** (5 connections) — `services/memory_router.py`
- **.promote_memory_candidates()** (5 connections) — `services/research/service.py`
- **.project_output_graph()** (4 connections) — `repositories/graph.py`
- **.create_knowledge()** (4 connections) — `repositories/knowledge.py`
- **UUID** (4 connections)
- **schemas/graph.py** (4 connections) — `schemas/graph.py`
- **OutputGraphEdge** (4 connections) — `schemas/graph.py`
- **OutputGraphNode** (4 connections) — `schemas/graph.py`
- **ProvenanceBundle** (4 connections) — `schemas/graph.py`
- **BaseModel** (4 connections)
- **Provenance** (4 connections) — `schemas/knowledge.py`
- *... and 35 more nodes in this community*

## Relationships

- [workspaces.py](workspaces.py.md) (7 shared connections)
- [tasks.py](tasks.py.md) (5 shared connections)
- [ResearchRepository](ResearchRepository.md) (5 shared connections)
- [ResearchModeOrchestrator](ResearchModeOrchestrator.md) (4 shared connections)
- [QuotaService](QuotaService.md) (3 shared connections)
- [GroundModeOrchestrator](GroundModeOrchestrator.md) (2 shared connections)
- [LegacyResearchEngine](LegacyResearchEngine.md) (2 shared connections)
- [WorkspaceExportService](WorkspaceExportService.md) (1 shared connections)
- [BaseRetriever](BaseRetriever.md) (1 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)
- [WorkspaceRepository](WorkspaceRepository.md) (1 shared connections)

## Source Files

- `models/knowledge.py`
- `orchestration/research_mode.py`
- `repositories/graph.py`
- `repositories/knowledge.py`
- `schemas/graph.py`
- `schemas/knowledge.py`
- `services/memory_router.py`
- `services/research/service.py`
- `workers/tasks.py`

## Audit Trail

- EXTRACTED: 93 (73%)
- INFERRED: 34 (27%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*