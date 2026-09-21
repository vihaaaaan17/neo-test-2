# 06: Retries and Context Injection

**What to build:** 
Support state continuation across retries without modifying the canonical `run_id`. When a retry occurs, the adapter initializes a fresh upstream execution but queries PostgreSQL for already-persisted `ResearchEvidence` from the previous attempts of the same `run_id`. This evidence is injected into ODR's initial context to ensure the engine doesn't duplicate costly research work.

**Blocked by:** 05: Cancellation and Partial Execution

**Status:** ready-for-agent

- [x] Implement evidence fetching logic in the ODR adapter initialization phase.
- [x] Inject fetched evidence into the initial ODR state / context.
- [x] Verify that a retried run maintains the original `run_id` but does not duplicate retrieved sources.
