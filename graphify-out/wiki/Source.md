# Source

> 22 nodes · cohesion 0.13

## Key Concepts

- **Source** (12 connections) — `models/source.py`
- **ResearchProvenanceService** (10 connections) — `services/research/provenance.py`
- **SourceRepository** (8 connections) — `repositories/source.py`
- **SourceSnapshot** (7 connections) — `models/source.py`
- **get_source_status()** (6 connections) — `api/routes/workspaces.py`
- **.create_source_with_snapshot()** (4 connections) — `repositories/source.py`
- **.resolve_source()** (4 connections) — `services/research/provenance.py`
- **UUID** (3 connections)
- **.audit_claim_citations()** (3 connections) — `services/research/provenance.py`
- **models/source.py** (2 connections) — `models/source.py`
- **Base** (2 connections)
- **repositories/source.py** (2 connections) — `repositories/source.py`
- **UUID** (2 connections)
- **.__init__()** (2 connections) — `repositories/source.py`
- **provenance.py** (2 connections) — `services/research/provenance.py`
- **.__init__()** (2 connections) — `services/research/provenance.py`
- **AsyncSession** (1 connections)
- **Any** (1 connections)
- **AsyncSession** (1 connections)
- **Attempts to resolve an external citation to an existing workspace Source.…** (1 connections) — `services/research/provenance.py`
- **Audits the full provenance chain for a given report_id. Chain: Report ->…** (1 connections) — `services/research/provenance.py`
- **Manages the mapping of external citations/evidence to canonical workspace…** (1 connections) — `services/research/provenance.py`

## Relationships

- [workspaces.py](workspaces.py.md) (5 shared connections)
- [tasks.py](tasks.py.md) (3 shared connections)
- [ResearchRepository](ResearchRepository.md) (3 shared connections)
- [QuotaService](QuotaService.md) (2 shared connections)
- [WorkspaceRepository](WorkspaceRepository.md) (1 shared connections)
- [OpenNotebookRepository](OpenNotebookRepository.md) (1 shared connections)
- [WorkspaceExportService](WorkspaceExportService.md) (1 shared connections)
- [upload_file_to_workspace](upload_file_to_workspace.md) (1 shared connections)

## Source Files

- `api/routes/workspaces.py`
- `models/source.py`
- `repositories/source.py`
- `services/research/provenance.py`

## Audit Trail

- EXTRACTED: 30 (64%)
- INFERRED: 17 (36%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*