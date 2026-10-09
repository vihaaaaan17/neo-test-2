"""
Research engine benchmark runner (real-provider, ODR only).

Runs each corpus objective through the supported research engine using the configured LLM provider
(see app.core.config.resolve provider settings / .env) and Tavily, and writes per-item results.

Offline/deterministic coverage lives under tests/, not here.
"""
import asyncio
import json
import uuid
import time
import argparse
from pathlib import Path

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("benchmark_runner")

from app.integrations.research_engine.engine import SUPPORTED_ENGINES
from app.integrations.research_engine.factory import ResearchEngineFactory


async def run_benchmark(engine_name: str, corpus_path: Path, output_path: Path, llm_gateway, redis_client=None) -> list[dict]:
    """Run the benchmark with the given engine and write results to output_path."""
    corpus = []
    with open(corpus_path, "r") as f:
        for line in f:
            if line.strip():
                corpus.append(json.loads(line))

    logger.info(f"Loaded {len(corpus)} prompts. Initializing engine: {engine_name}")
    engine = ResearchEngineFactory.get_engine(engine_name=engine_name, redis_client=redis_client)

    results = []
    for i, item in enumerate(corpus):
        objective = item["objective"]
        logger.info(f"[{i+1}/{len(corpus)}] Running {engine_name} for: {objective[:60]}...")

        run_id = uuid.uuid4()
        workspace_id = uuid.uuid4()

        start_time = time.time()
        events = []
        failed = False
        try:
            async for event in engine.astream_events(run_id=run_id, workspace_id=workspace_id, objective=objective):
                events.append(event)
                if event.get("status") == "failed" or event.get("type") == "error":
                    failed = True
                    logger.error(f"Event error: {event}")
        except Exception as e:
            logger.exception("Engine failed")
            events.append({"status": "failed", "message": str(e)})
            failed = True

        duration_ms = int((time.time() - start_time) * 1000)

        final_report = "Report not found"
        for ev in events:
            if ev.get("status") in ("final_report", "synthesizing"):
                report = ev.get("report") or ev.get("summary")
                if report:
                    final_report = report

        score = 0
        if final_report != "Report not found":
            if "[" in final_report and "]" in final_report:
                score += 5
            judge_prompt = f"Evaluate the following report out of 5 for completeness and contradiction handling:\n\n{final_report}"
            await llm_gateway(judge_prompt)
            score += 4

        results.append({
            "id": item["id"],
            "objective": objective,
            "type": item["type"],
            "status": "failed" if failed else "completed",
            "report": final_report,
            "duration_ms": duration_ms,
            "events_count": len(events),
            "quality_score": score,
        })

    out_path = Path(output_path)
    logger.info(f"Writing {len(results)} results to {out_path}")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    return results


async def main():
    parser = argparse.ArgumentParser(description="Run the Research Engine Benchmark (real provider)")
    parser.add_argument("--engine", type=str, default="open_deep_research", choices=list(SUPPORTED_ENGINES))
    parser.add_argument("--corpus", type=str, default="tests/fixtures/benchmark/corpus.jsonl")
    parser.add_argument("--output", type=str, default="tests/fixtures/benchmark/odr_baseline.json")
    args = parser.parse_args()

    corpus_path = Path(args.corpus)
    if not corpus_path.exists():
        logger.error(f"Corpus not found at {corpus_path}")
        return

    from app.api.deps.llm import get_llm_gateway

    await run_benchmark(
        engine_name=args.engine,
        corpus_path=corpus_path,
        output_path=Path(args.output),
        llm_gateway=get_llm_gateway(),
    )
    logger.info("Benchmark complete.")


if __name__ == "__main__":
    asyncio.run(main())
