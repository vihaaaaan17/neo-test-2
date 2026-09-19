# Glossary

## Export Bundle
A portable, polyglot `.zip` archive containing a workspace's entire canonical state, extracted text chunks, and metadata. 
- **Analytical dump**: It is designed to be loaded into Pandas, Jupyter, or another agentic framework to prevent vendor lock-in, rather than being a rigid 1-to-1 backup for bidirectional restoration.
- **Polyglot format**: Uses `.json` for hierarchical metadata and `.parquet` for large tabular arrays (e.g., embeddings, source chunks).
- **Scope**: By default, the bundle contains only structured metadata and extracted content. Raw binaries (e.g., source PDFs) are optionally referenced via signed URLs rather than packaged into the zip to prevent archive bloat.

## Ground Engine
The execution substrate for Ground Mode. In Chapter 2, this is the actual upstream Open Notebook implementation running as an isolated internal HTTP service. Neosis delegates Ground-mode retrieval, search, ask, and chat execution to the Ground Engine. Neosis does not reimplement the engine's internal behavior.

## Source Projection
The process of uploading a canonical Neosis source file (from S3) into Open Notebook through its native source-ingestion pathway. The projection is derived and rebuildable from the canonical Neosis source snapshot. Projection is intentionally duplicative: the canonical source lives in Neosis S3; the execution copy lives in Open Notebook's SurrealDB.

## Workspace Binding
An explicit, persisted mapping record between a Neosis `workspace_id` and an Open Notebook `notebook_id`. These identifiers are never equated. The binding supports creation, lookup, synchronization state, and failure metadata.

## Source Binding
An explicit, persisted mapping record between a Neosis `source_id`/`snapshot_id` pair and an Open Notebook `source_id`. Keyed on `(workspace_id, source_id, snapshot_id, checksum_sha256)` for idempotency.

## Compatibility Layer
The thin integration boundary (`app/integrations/open_notebook/`) that owns HTTP transport, binding resolution, source projection, response translation, citation mapping, error translation, and health checking between Neosis and the Ground Engine. It must not become a second Ground engine.

## Upstream Revision
The pinned version of the Open Notebook implementation used as the Ground Engine runtime. Recorded in `UPSTREAM_REVISION.md` at the project root. Includes repository URL, Git tag/commit, Docker image tag, Docker image digest, and acquisition date. Upgrades are deliberate, controlled migrations.
