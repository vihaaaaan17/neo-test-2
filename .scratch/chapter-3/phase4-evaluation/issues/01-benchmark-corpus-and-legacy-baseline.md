# 01: Benchmark Corpus & Legacy Baseline

**What to build:** Create `scripts/benchmark_runner.py` capable of executing both engines offline. Synthesize a frozen JSONL corpus of 20-30 representative research prompts (`tests/fixtures/benchmark/corpus.jsonl`). Run the legacy `ResearchModeOrchestrator` across this corpus once and store the output (reports, metrics) in `legacy_baseline.json`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] Create `tests/fixtures/benchmark/corpus.jsonl` with 20-30 diverse research prompts.
- [x] Implement `scripts/benchmark_runner.py` to process the corpus using a specified engine.
- [x] Generate and commit `legacy_baseline.json` containing legacy outputs and baseline metrics.
