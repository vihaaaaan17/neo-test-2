# 02: Neosis Config and Integration Boundary

**What to build:** 
The Neosis backend configuration is extended to support Open Notebook settings. The `app/integrations/open_notebook/` boundary is established with basic configuration parsing, an HTTP client capable of reaching Open Notebook, and an internal health-check function.

**Blocked by:** 01: Pin Upstream and Add Docker Infrastructure

**Status:** done

- [x] Add `OPEN_NOTEBOOK_ENABLED` (default `False`), `OPEN_NOTEBOOK_BASE_URL`, and `OPEN_NOTEBOOK_TIMEOUT` to the `Settings` class in `app/core/config.py`.
- [x] Create `app/integrations/open_notebook/__init__.py`.
- [x] Create `app/integrations/open_notebook/config.py` as a localized integration config helper.
- [x] Create `app/integrations/open_notebook/client.py` wrapping basic asynchronous HTTP transport to Open Notebook's `/health` endpoint.
- [x] Create `app/integrations/open_notebook/health.py` exposing a `check_open_notebook_health()` function.
