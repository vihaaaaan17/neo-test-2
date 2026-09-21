# 02: Provenance Audit & Isolation Testing

**What to build:** Develop a deterministic provenance audit script (`test_provenance_audit.py`) that strictly validates the `Report -> Claim -> Artifact -> Evidence -> Source -> Task -> Run -> Workspace` chain for generated reports, failing on any fabricated links. Create `test_workspace_isolation.py` to run parallel jobs and actively assert authorization rejections on cross-workspace evidence, report, and promotion access.

**Blocked by:** 01-benchmark-corpus-and-legacy-baseline

**Status:** ready-for-agent

- [x] Implement `test_provenance_audit.py` to parse markdown citations and verify their existence in the database against the exact `run_id`.
- [x] Implement `test_workspace_isolation.py` simulating parallel jobs in different workspaces.
- [x] Assert that attempting to read or promote memory/graph artifacts across workspaces raises hard authorization exceptions.
