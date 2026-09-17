# 08: Chunking & Storage of Parsed Content

**What to build:** Takes the structured output from the Docling parser, splits it into bounded retrieval units (Chunks), and stores them in Postgres. Crucially, each Chunk must retain an exact locator (page, section) pointing back to the `SourceSnapshot`.

**Blocked by:** 07: Document Parsing Pipeline (Docling)

**Status:** ready-for-agent

- [ ] Alembic migration for `chunks` table
- [ ] Chunking logic splits parsed Docling output into retrieval units
- [ ] Locator metadata (page, section) is preserved on each chunk
- [ ] Chunks are saved to Postgres via a ChunkRepository
