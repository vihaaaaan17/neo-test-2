# 05: Object Storage Interface & File Upload

**What to build:** An abstraction layer for S3-compatible storage. An API endpoint to upload a raw file (e.g., PDF) into a Workspace, storing the bytes in S3 and returning a stable object URI.

**Blocked by:** 04: Authentication & Tenant Isolation (Supabase)

**Status:** ready-for-agent

- [ ] ObjectStore provider interface defined and implemented for S3 (or local mock for testing)
- [ ] File upload API endpoint created, receiving binary data
- [ ] File is securely saved to object storage using a UUID/hash-based key
- [ ] Endpoint returns the stable object URI
