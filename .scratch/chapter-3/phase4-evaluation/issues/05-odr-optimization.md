# 05: ODR Optimization

**What to build:** Based on the results of Ticket 03, optimize the Open Deep Research engine's concurrency, prompt depth, and retriever selection. The goal is to bring the new engine within the established cost and latency ceilings without degrading the provenance or quality scores. Re-run the benchmark to verify the optimized engine passes all thresholds.

**Blocked by:** 03-quality-cost-latency-evaluation

**Status:** ready-for-agent

- [x] Analyze the unoptimized ODR metrics from Ticket 03.
- [x] Adjust ODR configuration (e.g., search depth, max concurrency) in the adapter to constrain runtime behavior.
- [x] Re-run the benchmark suite to confirm cost/latency ceilings are met.
- [x] Confirm quality and provenance scores still meet or exceed the legacy baseline.
