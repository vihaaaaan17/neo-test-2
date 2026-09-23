# DocumentBlock

> 9 nodes · cohesion 0.28

## Key Concepts

- **DocumentBlock** (5 connections) — `models/block.py`
- **BlockRepository** (5 connections) — `repositories/block.py`
- **.bulk_create_blocks()** (4 connections) — `repositories/block.py`
- **repositories/block.py** (2 connections) — `repositories/block.py`
- **.__init__()** (2 connections) — `repositories/block.py`
- **UUID** (2 connections)
- **models/block.py** (1 connections) — `models/block.py`
- **Base** (1 connections)
- **AsyncSession** (1 connections)

## Relationships

- [WorkspaceExportService](WorkspaceExportService.md) (1 shared connections)
- [tasks.py](tasks.py.md) (1 shared connections)
- [DocumentBlockCreate](DocumentBlockCreate.md) (1 shared connections)

## Source Files

- `models/block.py`
- `repositories/block.py`

## Audit Trail

- EXTRACTED: 10 (77%)
- INFERRED: 3 (23%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*