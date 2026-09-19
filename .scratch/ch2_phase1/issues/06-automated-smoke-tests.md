# 06: Automated Smoke Tests

**What to build:** 
CI and local test runs automatically prove that Phase 1's exit gates (booting, isolating, and querying the Ground Engine) are successfully satisfied using the real Open Notebook container.

**Blocked by:** 03: Expose Open Notebook in Main Health Endpoint, 05: Integration Test Infrastructure and Fixtures

**Status:** done

- [x] Create `tests/integration/test_open_notebook_health.py` asserting the health check logic respects the `OPEN_NOTEBOOK_ENABLED` flag.
- [x] Create `tests/integration/test_open_notebook_smoke.py` asserting a real source from `tests/fixtures/` can be ingested.
- [x] Assert an Ask query against the Open Notebook API returns a successful answer utilizing the ingested source.
