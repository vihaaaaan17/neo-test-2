# tasks.py

> 21 nodes · cohesion 0.14

## Key Concepts

- **tasks.py** (12 connections) — `workers/tasks.py`
- **parse_and_chunk_job()** (9 connections) — `workers/tasks.py`
- **Any** (9 connections)
- **_get_source_and_snapshot()** (8 connections) — `workers/tasks.py`
- **project_to_open_notebook_job()** (7 connections) — `workers/tasks.py`
- **compress_episodic_job()** (6 connections) — `workers/tasks.py`
- **process_deletion_tombstone_job()** (5 connections) — `workers/tasks.py`
- **project_output_graph_job()** (5 connections) — `workers/tasks.py`
- **reconcile_deletion_tombstones_job()** (4 connections) — `workers/tasks.py`
- **sync_knowledge_to_graph_job()** (4 connections) — `workers/tasks.py`
- **UUID** (2 connections)
- **AsyncSession** (1 connections)
- **Background job functions executed by the arq worker. Design rules: - Every job…** (1 connections) — `workers/tasks.py`
- **Background job: summarise working memory state into an episodic memory record.…** (1 connections) — `workers/tasks.py`
- **Background job: synchronizes a KnowledgeMemory row from Postgres to the Neo4j…** (1 connections) — `workers/tasks.py`
- **Background job: Projects the final OutputGraph from the research agent into…** (1 connections) — `workers/tasks.py`
- **Load the source + its first snapshot in a single query.** (1 connections) — `workers/tasks.py`
- **Background job: Projects a new source snapshot to Open Notebook.** (1 connections) — `workers/tasks.py`
- **Background job: Processes a DeletionTombstone against Open Notebook.** (1 connections) — `workers/tasks.py`
- **Periodic task: Sweeps for pending tombstones and enqueues processing.** (1 connections) — `workers/tasks.py`
- **Background job: download from S3, parse with Docling, chunk, bulk-insert…** (1 connections) — `workers/tasks.py`

## Relationships

- [run_research_agent_job](run_research_agent_job.md) (5 shared connections)
- [WorkspaceExportService](WorkspaceExportService.md) (3 shared connections)
- [EpisodicRepository](EpisodicRepository.md) (3 shared connections)
- [Source](Source.md) (3 shared connections)
- [OpenNotebookRepository](OpenNotebookRepository.md) (3 shared connections)
- [OpenNotebookClient](OpenNotebookClient.md) (2 shared connections)
- [ObjectStoreProtocol](ObjectStoreProtocol.md) (1 shared connections)
- [DocumentBlock](DocumentBlock.md) (1 shared connections)
- [DocumentParser](DocumentParser.md) (1 shared connections)
- [DocumentBlockCreate](DocumentBlockCreate.md) (1 shared connections)

## Source Files

- `workers/tasks.py`

## Audit Trail

- EXTRACTED: 33 (63%)
- INFERRED: 19 (37%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*