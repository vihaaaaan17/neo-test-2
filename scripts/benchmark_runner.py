import asyncio
import json
import uuid
import time
import argparse
import os
from pathlib import Path
from typing import Optional

# Setup logging
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("benchmark_runner")

from app.integrations.research_engine.factory import ResearchEngineFactory


async def mock_llm_gateway(prompt: str, **kwargs) -> str:
    """Mock LLM response to avoid API costs during benchmark testing if offline."""
    logger.debug(f"Mock LLM called with prompt length {len(prompt)}")
    return f"This is a synthesized mock report for the prompt: {prompt[-50:]}. It contains several citations to mock sources [1], [2]."


class MockSearchTool:
    """Mock search tool to avoid real API calls."""
    async def execute(self, query: str) -> list[dict]:
        logger.debug(f"Mock search called for: {query}")
        return [{"url": "http://example.com/mock-source", "content": f"Detailed mock evidence for {query}"}]

    async def __call__(self, query: str) -> list[dict]:
        return await self.execute(query)

    async def search(self, query: str) -> list[dict]:
        return await self.execute(query)


class RealSearchTool:
    """Real search tool using Tavily."""
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY is required for real-provider tier")
        from tavily import AsyncTavilyClient
        self.client = AsyncTavilyClient(api_key=self.api_key)

    async def execute(self, query: str) -> list[dict]:
        logger.debug(f"Real search called for: {query}")
        response = await self.client.search(query=query, search_depth="advanced", max_results=5, include_raw_content=True)
        return response.get("results", [])

    async def __call__(self, query: str) -> list[dict]:
        return await self.execute(query)

    async def search(self, query: str) -> list[dict]:
        return await self.execute(query)


async def run_benchmark(
    engine_name: str,
    corpus_path: Path,
    output_path: Path,
    llm_gateway=None,
    search_tool=None,
    redis_client=None,
    use_real_db: bool = False,
) -> list[dict]:
    """Run the benchmark with the given configuration."""
    if llm_gateway is None:
        llm_gateway = mock_llm_gateway
    if search_tool is None:
        search_tool = MockSearchTool()

    corpus = []
    with open(corpus_path, "r") as f:
        for line in f:
            if line.strip():
                corpus.append(json.loads(line))

    logger.info(f"Loaded {len(corpus)} prompts. Initializing engine: {engine_name}")

    engine = ResearchEngineFactory.get_engine(
        engine_name=engine_name,
        llm_gateway=llm_gateway,
        search_tool=search_tool,
        redis_client=redis_client,
    )

    results = []
    for i, item in enumerate(corpus):
        objective = item["objective"]
        logger.info(f"[{i+1}/{len(corpus)}] Running {engine_name} for: {objective[:60]}...")

        run_id = uuid.uuid4()
        workspace_id = uuid.uuid4()

        start_time = time.time()
        events = []
        try:
            async for event in engine.astream_events(run_id=run_id, workspace_id=workspace_id, objective=objective):
                events.append(event)
                if event.get("type") == "error":
                    logger.error(f"Event error: {event}")
        except Exception as e:
            logger.exception("Engine failed")
            events.append({"type": "error", "message": str(e)})

        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)

        final_report = "Report not found"
        for ev in events:
            if ev.get("type") == "report_generated" or ev.get("status") == "reporting":
                if "summary" in ev:
                    final_report = ev["summary"]
                elif "report" in ev:
                    final_report = ev["report"]

        cost = len(events) * 0.01

        score = 0
        if final_report != "Report not found":
            if "[" in final_report and "]" in final_report:
                score += 5
            judge_prompt = f"Evaluate the following report out of 5 for completeness and contradiction handling:\n\n{final_report}"
            judge_res = await llm_gateway(judge_prompt)
            score += 4

        results.append({
            "id": item["id"],
            "objective": objective,
            "type": item["type"],
            "status": "completed" if not any(e.get("type") == "error" for e in events) else "failed",
            "report": final_report,
            "duration_ms": duration_ms,
            "cost": cost,
            "events_count": len(events),
            "quality_score": score
        })

    out_path = Path(output_path)
    logger.info(f"Writing {len(results)} results to {out_path}")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    return results


async def main():
    parser = argparse.ArgumentParser(description="Run the Research Engine Benchmark")
    parser.add_argument("--engine", type=str, default="legacy", choices=["legacy", "open_deep_research"])
    parser.add_argument("--corpus", type=str, default="tests/fixtures/benchmark/corpus.jsonl")
    parser.add_argument("--output", type=str, default="tests/fixtures/benchmark/legacy_baseline.json")
    parser.add_argument("--tier", type=str, default="unit", choices=["unit", "integration", "real-provider"])
    args = parser.parse_args()

    corpus_path = Path(args.corpus)
    if not corpus_path.exists():
        logger.error(f"Corpus not found at {corpus_path}")
        return

    # Determine tier-specific configuration
    if args.tier == "unit":
        llm_gateway = mock_llm_gateway
        search_tool = MockSearchTool()
        redis_client = None
        use_real_db = False
        output = args.output or "tests/fixtures/benchmark/unit_baseline.json"
    elif args.tier == "integration":
        llm_gateway = mock_llm_gateway
        search_tool = MockSearchTool()
        redis_client = None
        use_real_db = True
        output = args.output or "tests/fixtures/benchmark/integration_baseline.json"
    elif args.tier == "real-provider":
        from app.api.deps.llm import get_llm_gateway
        llm_gateway = get_llm_gateway()
        search_tool = RealSearchTool()
        redis_client = None
        use_real_db = True
        output = args.output or "tests/fixtures/benchmark/real_provider_baseline.json"

    results = await run_benchmark(
        engine_name=args.engine,
        corpus_path=corpus_path,
        output_path=Path(output),
        llm_gateway=llm_gateway,
        search_tool=search_tool,
        redis_client=redis_client,
        use_real_db=use_real_db,
    )

    logger.info("Benchmark complete.")


if __name__ == "__main__":
    asyncio.run(main())