# 04: Budgets and Usage Tracking

**What to build:** 
Accumulate token and API call metrics in-memory within the `ResearchEngine` adapter and custom retriever tools during execution. Enforce time, token, and cost boundaries centrally; if a boundary is exceeded, raise a `ResearchBudgetExceeded` exception to gracefully interrupt the execution. Checkpoint the accumulated usage periodically and fully persist it as a canonical `ResearchUsage` record when finalizing the run.

**Blocked by:** 03: Neosis-Aware Retrievers and Evidence Interception

**Status:** ready-for-agent

- [x] Implement a usage accumulator inside `ResearchEngine`.
- [x] Add budget enforcement checks in the retriever wrappers and LLM callbacks.
- [x] Define the `ResearchBudgetExceeded` exception.
- [x] Implement periodic checkpointing and final persistence logic for `ResearchUsage`.
