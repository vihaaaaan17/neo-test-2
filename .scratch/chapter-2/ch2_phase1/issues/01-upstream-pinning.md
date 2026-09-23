# 01: Pin Upstream and Add Docker Infrastructure

**What to build:** 
Developers can run `docker compose up` and have Open Notebook (`v1.14.0`) and SurrealDB boot alongside existing Neosis services. The `UPSTREAM_REVISION.md` file exists at the root, pinning the exact runtime and upstream checkout details. The `.env.example` file provides the `OPEN_NOTEBOOK_ENCRYPTION_KEY` placeholder.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] Check out `references/open-notebook` to tag `v1.14.0`.
- [x] Create `UPSTREAM_REVISION.md` at the project root with the immutable Docker digest for `lfnovo/open_notebook:v1.14.0` and the corresponding Git SHA.
- [x] Add `surrealdb` (internal port only) and `open_notebook` (internal port 5055 exposed) services to `docker-compose.yml`.
- [x] Add `OPEN_NOTEBOOK_ENCRYPTION_KEY` and an example `GOOGLE_API_KEY` fallback to `.env.example`.
