# 05: Integration Test Infrastructure and Fixtures

**What to build:** 
The automated test suite is configured to isolate Open Notebook tests and skip them gracefully if the Docker container isn't running. A stable corpus of test documents is provided for ingestion tests.

**Blocked by:** 02: Neosis Config and Integration Boundary

**Status:** done

- [x] Add `open_notebook` marker to `pytest.ini`.
- [x] Update `tests/conftest.py` with an auto-skip logic for `@pytest.mark.open_notebook` that probes port 5055.
- [x] Create `tests/fixtures/open_notebook/` directory.
- [x] Add a short sample markdown file and a sample JSON file to the fixtures directory.
