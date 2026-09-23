# 03: Expose Open Notebook in Main Health Endpoint

**What to build:** 
DevOps and operators can see Open Notebook's health status via the standard Neosis `/health` API. When enabled, it reports `ok` or `failed` (degrading overall status). When disabled, it safely skips the check without degrading health.

**Blocked by:** 02: Neosis Config and Integration Boundary

**Status:** done

- [x] Update `app/main.py` health_check route.
- [x] If `settings.OPEN_NOTEBOOK_ENABLED` is `False`, report `open_notebook: disabled` and leave overall status unaffected.
- [x] If `True`, call `check_open_notebook_health()`.
- [x] If reachable, report `open_notebook: ok`.
- [x] If unreachable, report `open_notebook: failed` and degrade overall status to `degraded`.
