import asyncio
import json
import uuid
import time
import argparse
from pathlib import Path

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

async def main():
    parser = argparse.ArgumentParser(description="Run the Research Engine Benchmark")
    parser.add_argument("--engine", type=str, default="legacy", choices=["legacy", "open_deep_research"])
    parser.add_argument("--corpus", type=str, default="tests/fixtures/benchmark/corpus.jsonl")
    parser.add_argument("--output", type=str, default="tests/fixtures/benchmark/legacy_baseline.json")
    args = parser.parse_args()

    corpus_path = Path(args.corpus)
    if not corpus_path.exists():
        logger.error(f"Corpus not found at {corpus_path}")
        return

    logger.info(f"Loading corpus from {corpus_path}")
    corpus = []
    with open(corpus_path, "r") as f:
        for line in f:
            if line.strip():
                corpus.append(json.loads(line))
                
    logger.info(f"Loaded {len(corpus)} prompts. Initializing engine: {args.engine}")
    
    # Instantiate engine with mocked dependencies
    engine = ResearchEngineFactory.get_engine(
        engine_name=args.engine,
        llm_gateway=mock_llm_gateway,
        search_tool=MockSearchTool(),
        redis_client=None
    )

    results = []

    for i, item in enumerate(corpus):
        objective = item["objective"]
        logger.info(f"[{i+1}/{len(corpus)}] Running {args.engine} for: {objective[:60]}...")
        
        run_id = str(uuid.uuid4())
        workspace_id = str(uuid.uuid4())
        
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
            # Look for the final report event
            if ev.get("type") == "report_generated" or ev.get("status") == "reporting":
                if "summary" in ev:
                    final_report = ev["summary"]
                elif "report" in ev:
                    final_report = ev["report"]

        cost = len(events) * 0.01  # Mock cost
        
        # LLM-as-a-judge scoring logic
        score = 0
        if final_report != "Report not found":
            # Deterministic check for citations
            if "[" in final_report and "]" in final_report:
                score += 5
            
            # Subjective check (mocked)
            judge_prompt = f"Evaluate the following report out of 5 for completeness and contradiction handling:\n\n{final_report}"
            judge_res = await mock_llm_gateway(judge_prompt)
            # In a real scenario we'd parse the score, here we just mock add 4.
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

    out_path = Path(args.output)
    logger.info(f"Writing {len(results)} results to {out_path}")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    logger.info("Benchmark complete.")

if __name__ == "__main__":
    asyncio.run(main())
