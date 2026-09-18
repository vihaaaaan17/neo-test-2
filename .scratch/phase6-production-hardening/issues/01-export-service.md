# 01: Build WorkspaceExportService

**What to build:** The core domain logic that packages a workspace's state into a downloadable ZIP archive. It fetches hierarchical metadata (Workspace, Source, Memory) from Postgres and serializes it to `metadata.json`. It fetches tabular data (Chunks, Embeddings) and uses Pandas/PyArrow to serialize it to `chunks.parquet`. It then compresses these into a `.zip` file, uploads it to the `ObjectStore`, and returns a presigned download URL.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `pandas` and `pyarrow` added to project dependencies.
- [ ] `WorkspaceExportService` created in `app/services/export.py`.
- [ ] Service generates a `.zip` in memory or using temp files containing `metadata.json` and `chunks.parquet`.
- [ ] Service uploads `.zip` to `ObjectStore` and returns a signed URL.
- [ ] Unit tests verify the archive creation and payload structure by mocking database and object store interactions.
