# 03: Quality, Cost, and Latency Evaluation Suite

**What to build:** Finalize the `benchmark.py` scoring logic using the `llm_gateway` for subjective report quality + deterministic citation checking. Establish empirical cost & p95 latency budgets from the legacy baseline. Execute offline shadow testing of the new ODR engine against the benchmark corpus to measure its unoptimized performance and quality score against the legacy baseline.

**Blocked by:** 01-benchmark-corpus-and-legacy-baseline

**Status:** ready-for-agent

- [x] Add LLM-judge scoring logic to `benchmark.py` for evaluating completeness and contradiction handling.
- [x] Calculate baseline cost and p95 latency from `legacy_baseline.json`.
- [x] Establish and document the hard production ceilings for cost and duration.
- [x] Execute `benchmark_runner.py` with the ODR engine and record the unoptimized metrics.
