# ObjectStoreProtocol

> 11 nodes · cohesion 0.22

## Key Concepts

- **ObjectStoreProtocol** (9 connections) — `services/storage.py`
- **get_object_store()** (6 connections) — `services/storage.py`
- **storage.py** (5 connections) — `services/storage.py`
- **UUID** (3 connections)
- **.upload_file()** (2 connections) — `services/storage.py`
- **.upload_file()** (2 connections) — `services/storage.py`
- **.download_file()** (1 connections) — `services/storage.py`
- **.generate_presigned_url()** (1 connections) — `services/storage.py`
- **Protocol** (1 connections)
- **Request** (1 connections)
- **Dependency to provide shared S3ObjectStore from app state.** (1 connections) — `services/storage.py`

## Relationships

- [WorkspaceExportService](WorkspaceExportService.md) (3 shared connections)
- [DocumentParser](DocumentParser.md) (2 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)
- [tasks.py](tasks.py.md) (1 shared connections)
- [upload_file_to_workspace](upload_file_to_workspace.md) (1 shared connections)

## Source Files

- `services/storage.py`

## Audit Trail

- EXTRACTED: 17 (85%)
- INFERRED: 3 (15%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*