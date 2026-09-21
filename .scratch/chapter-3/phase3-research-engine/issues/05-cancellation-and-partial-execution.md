# 05: Cancellation and Partial Execution

**What to build:** 
Ensure the adapter gracefully handles cooperative cancellation from the Arq worker (`asyncio.CancelledError`). When interrupted (by user cancellation or a budget exception), the adapter must flush any pending evidence and ensure the run safely finalizes its state as `CANCELLED` or `PARTIAL`. The collected canonical evidence is preserved without attempting a fallback report synthesis.

**Blocked by:** 04: Budgets and Usage Tracking

**Status:** ready-for-agent

- [x] Update adapter execution loop to catch `asyncio.CancelledError` and `ResearchBudgetExceeded`.
- [x] Implement cleanup logic to ensure in-flight evidence and usage metrics are flushed.
- [x] Ensure the adapter returns a partial result payload that transitions the `ResearchRun` state to `CANCELLED` or `PARTIAL`.
