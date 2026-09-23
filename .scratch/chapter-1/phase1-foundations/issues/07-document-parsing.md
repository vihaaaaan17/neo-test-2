# 07: Document Parsing Pipeline (Docling)

**What to build:** A service that takes a newly created `SourceSnapshot` (e.g., a PDF) from Object Storage, runs it through the Docling parser, and extracts structured layout and text content.

**Blocked by:** 06: Source Registry & Snapshot Creation

**Status:** ready-for-agent

- [ ] Integration with Docling (as a library or sub-process)
- [ ] Service layer downloads a `SourceSnapshot` from the ObjectStore
- [ ] PDF is parsed into structured output (text, layout bounding boxes, tables)
- [ ] Parsed output is temporarily saved/returned for the chunking step
