# DocumentBlockCreate

> 9 nodes · cohesion 0.25

## Key Concepts

- **DocumentBlockCreate** (5 connections) — `schemas/block.py`
- **.process_docling_output()** (4 connections) — `services/chunking.py`
- **ChunkingService** (3 connections) — `services/chunking.py`
- **schemas/block.py** (2 connections) — `schemas/block.py`
- **DocumentBlockResponse** (2 connections) — `schemas/block.py`
- **BaseModel** (1 connections)
- **chunking.py** (1 connections) — `services/chunking.py`
- **Any** (1 connections)
- **Takes the raw dictionary output from Docling and converts it into…** (1 connections) — `services/chunking.py`

## Relationships

- [DocumentBlock](DocumentBlock.md) (1 shared connections)
- [tasks.py](tasks.py.md) (1 shared connections)

## Source Files

- `schemas/block.py`
- `services/chunking.py`

## Audit Trail

- EXTRACTED: 10 (91%)
- INFERRED: 1 (9%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*