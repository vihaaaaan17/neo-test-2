# main.py

> 23 nodes · cohesion 0.10

## Key Concepts

- **main.py** (6 connections) — `main.py`
- **check_open_notebook_health()** (5 connections) — `integrations/open_notebook/health.py`
- **.__init__()** (4 connections) — `integrations/open_notebook/client.py`
- **get_open_notebook_timeout()** (4 connections) — `integrations/open_notebook/config.py`
- **health_check()** (4 connections) — `main.py`
- **open_notebook/config.py** (3 connections) — `integrations/open_notebook/config.py`
- **get_open_notebook_base_url()** (3 connections) — `integrations/open_notebook/config.py`
- **is_open_notebook_enabled()** (3 connections) — `integrations/open_notebook/config.py`
- **lifespan()** (3 connections) — `main.py`
- **Request** (3 connections)
- **UploadSizeLimitMiddleware** (3 connections) — `main.py`
- **limit_upload_size()** (2 connections) — `main.py`
- **set_neosis_run_id()** (2 connections) — `main.py`
- **.dispatch()** (2 connections) — `main.py`
- **AsyncClient** (1 connections)
- **BaseHTTPMiddleware** (1 connections)
- **Get the default HTTP timeout for Open Notebook requests.** (1 connections) — `integrations/open_notebook/config.py`
- **Check if the Open Notebook Ground Engine is enabled.** (1 connections) — `integrations/open_notebook/config.py`
- **Get the base URL for the Open Notebook API.** (1 connections) — `integrations/open_notebook/config.py`
- **health.py** (1 connections) — `integrations/open_notebook/health.py`
- **Check if the Open Notebook Ground Engine is reachable and healthy. Returns:…** (1 connections) — `integrations/open_notebook/health.py`
- **get** (1 connections)
- **Deep health check verifying Postgres and Neo4j connectivity.** (1 connections) — `main.py`

## Relationships

- [OpenNotebookClient](OpenNotebookClient.md) (2 shared connections)
- [FastAPI](FastAPI.md) (2 shared connections)

## Source Files

- `integrations/open_notebook/client.py`
- `integrations/open_notebook/config.py`
- `integrations/open_notebook/health.py`
- `main.py`

## Audit Trail

- EXTRACTED: 24 (80%)
- INFERRED: 6 (20%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*