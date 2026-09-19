# 04: Phase 2 Normalization & Provenance Services

**What to build:** 
Two services in `app/services/research/` to manage the ingestion of external data. The normalization service deduplicates evidence by fingerprinting content/URLs. The provenance service maps external citations to the canonical `Source` entity and gracefully handles unresolved or partial provenance.

**Blocked by:** 02 (02-unified-research-repository.md)

**Status:** ready-for-agent

- [x] Create `app/services/research/normalization.py`.
- [x] Implement evidence fingerprinting logic (e.g. hashing normalized URLs + excerpt text) to enable deduplication before insertion into `ResearchEvidence`.
- [x] Create `app/services/research/provenance.py`.
- [x] Implement source mapping logic that attempts to resolve external citations to an existing workspace `Source`, falling back to `null` and storing raw provenance on the `ResearchEvidence` record if unresolved.
- [x] Write unit tests verifying that identical external results produce the same fingerprint and that unresolved sources do not crash the pipeline.
