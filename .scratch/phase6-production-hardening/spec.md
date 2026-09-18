## Problem Statement

Researchers and knowledge workers face platform lock-in when accumulating significant state in NeosisLM. Their Canonical Knowledge and active Workspace state are tightly coupled to the internal PostgreSQL database and pgvector extensions, making it difficult to perform external data science (e.g., using Pandas or Jupyter) on their extracted chunks and embeddings.

## Solution

An Export Bundle generator that allows users to export an entire Workspace's structured canonical state and tabular analytical data into a highly portable `.zip` polyglot archive containing JSON (for hierarchical metadata) and Parquet (for massive vector/chunk arrays).

## User Stories

1. As a user, I want to export my entire workspace as a portable JSON/Parquet bundle, so that I can own my data and prevent vendor lock-in.
2. As a data scientist, I want chunk and vector embeddings exported as Parquet, so that I can efficiently load them into Pandas/Jupyter without massive JSON parsing overhead.
3. As a developer, I want the export to run asynchronously in a background queue, so that massive workspaces don't trigger HTTP timeout errors on the API.

## Implementation Decisions

- **Domain Logic**: A new `WorkspaceExportService` module will be built.
- **Serialization**: 
  - Canonical metadata (`Workspace`, `Source`, `KnowledgeMemory`, `EpisodicMemory`) will be serialized into `metadata.json`.
  - Chunk and embedding arrays (`Block` objects) will be converted to a DataFrame and serialized into `chunks.parquet`. 
  - `pandas` and `pyarrow` will be added to the dependency tree.
- **Archiving**: The service will zip these files together in memory/tempfile and upload them to the `ObjectStore`, returning a presigned URL.
- **Asynchronous Execution**: The `app/workers/tasks.py` module will be extended with an `export_workspace_job`. This job will publish the final presigned URL to a Redis channel upon completion.
- **UI**: The Streamlit frontend will feature an "Export Workspace" button that enqueues the job and listens to Redis pub/sub for the download link.

## Testing Decisions

- **Test Seams**: The primary test seam is the `WorkspaceExportService`. We will test it by mocking the `ObjectStore` and database session.
- **Acceptance Criteria**: The test must assert that invoking the export generates a valid ZIP archive, and that extracting it yields valid JSON and Parquet files containing the seeded mock data.
- **Prior Art**: We will model the async worker tests off the existing background job tests (if any) and focus on pure domain logic for the service.

## Out of Scope

- Exporting raw binaries/assets (e.g., source PDFs) inside the ZIP archive. (This is documented as a future migration in `SCALING_MIGRATIONS.md` to prevent archive bloat).
- A reverse "Import Workspace" feature (true bidirectional restore requires strict primary-key conflict resolution and schema migration matching, which is deferred).

## Further Notes

- The term "Export Bundle" has been formalized in `CONTEXT.md` as an analytical dump, distinct from a 1-to-1 backup state.
