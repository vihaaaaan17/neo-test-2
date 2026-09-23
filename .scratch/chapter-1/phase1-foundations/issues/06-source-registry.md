# 06: Source Registry & Snapshot Creation

**What to build:** When a file is uploaded, the system creates a canonical `Source` and a `SourceSnapshot` record in Postgres. This tracks the immutable file metadata (checksum, size, URI) bridging the Object Store and the database.

**Blocked by:** 05: Object Storage Interface & File Upload

**Status:** ready-for-agent

- [ ] Alembic migration for `sources` and `source_snapshots` tables
- [ ] Pydantic schemas and Repository pattern for Source creation
- [ ] File upload endpoint updated to compute file checksum and size
- [ ] Endpoint persists Source and SourceSnapshot records linking to the object URI
