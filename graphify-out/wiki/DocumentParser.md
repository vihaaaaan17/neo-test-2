# DocumentParser

> 7 nodes · cohesion 0.33

## Key Concepts

- **DocumentParser** (6 connections) — `services/parsing.py`
- **.parse_document()** (3 connections) — `services/parsing.py`
- **.__init__()** (2 connections) — `services/parsing.py`
- **._run_docling()** (2 connections) — `services/parsing.py`
- **Any** (2 connections)
- **parsing.py** (1 connections) — `services/parsing.py`
- **Downloads a document from Object Storage and parses it using docling. Returns a…** (1 connections) — `services/parsing.py`

## Relationships

- [ObjectStoreProtocol](ObjectStoreProtocol.md) (2 shared connections)
- [tasks.py](tasks.py.md) (1 shared connections)

## Source Files

- `services/parsing.py`

## Audit Trail

- EXTRACTED: 8 (80%)
- INFERRED: 2 (20%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*