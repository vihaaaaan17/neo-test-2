# 04: Authentication & Tenant Isolation (Supabase)

**What to build:** Secures the Workspace API. Requests must include a valid authentication token (e.g., Supabase JWT). Users can only retrieve Workspaces they own, implementing the required tenant isolation policy.

**Blocked by:** 03: Workspace Lifecycle API

**Status:** ready-for-agent

- [ ] FastAPI dependency extracts and validates JWT tokens
- [ ] Workspace API endpoints require valid authentication
- [ ] Postgres Row-Level Security (RLS) or application-level filtering ensures a user can only query their own workspaces
- [ ] Tests verify unauthorized access is rejected (401) and cross-tenant access is blocked (403/404)
