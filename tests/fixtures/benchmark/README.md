# Benchmark fixtures

- `corpus.jsonl` — frozen objectives used by `scripts/benchmark_runner.py`.
- `legacy_baseline.json` — **obsolete, immutable historical data.** It was produced by the legacy research engine, which was removed in
  Chapter 5 Phase 1. Do not regenerate it and do not compare new runs against it as a performance floor.
- `odr_unoptimized_baseline.json`, `odr_optimized_baseline.json` — earlier Open Deep Research baselines.
- `odr_baseline.json` — default output of `scripts/benchmark_runner.py` (real provider, ODR only).
