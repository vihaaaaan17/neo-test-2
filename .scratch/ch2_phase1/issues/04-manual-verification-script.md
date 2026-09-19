# 04: Manual Verification Script

**What to build:** 
Developers can quickly run a standalone python script that interacts with the local Open Notebook container to ensure the Ask/Search workflow works against the real engine, proving ingestion and AI model functionality.

**Blocked by:** 01: Pin Upstream and Add Docker Infrastructure

**Status:** done

- [x] Create `scripts/verify_open_notebook.py`.
- [x] Script should verify the `/health` endpoint is `200`.
- [x] Script should simulate a basic text/markdown ingestion against the ON API.
- [x] Script should execute an Ask query and print the response.
- [x] Ensure clear error messages if the service is unreachable or credentials (like `GOOGLE_API_KEY`) are missing.
