"""
Offline, deterministic run of the real ODR graph through the Neosis adapter, over the benchmark corpus.
Verifies the engine contract (progress events, exactly one final_report, no terminal statuses) and that
search results enter Neosis evidence through neosis_web_search with provenance.
"""
import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.integrations.research_engine.open_deep_research.engine import OpenDeepResearchEngine
from tests.harness.odr_offline import offline_odr

CORPUS = Path(__file__).resolve().parents[3] / "fixtures" / "benchmark" / "corpus.jsonl"
ITEMS = [json.loads(line) for line in CORPUS.read_text().splitlines() if line.strip()]
TERMINAL = {"completed", "failed", "partial", "cancelled", "aborted_by_timeline_fence"}


@pytest.mark.asyncio
@pytest.mark.parametrize("item", ITEMS, ids=[i["id"] for i in ITEMS])
async def test_offline_odr_run_honours_engine_contract(item):
    run_id, workspace_id = uuid4(), uuid4()

    with offline_odr(item["objective"]) as rec:
        engine = OpenDeepResearchEngine()
        events = [e async for e in engine.astream_events(run_id=run_id, workspace_id=workspace_id, objective=item["objective"])]

    statuses = [e["status"] for e in events]

    # Contract: progress events, then exactly one final_report as the last event, never a terminal status.
    assert statuses[0] == "starting"
    assert "planning" in statuses and "executing" in statuses and "synthesizing" in statuses
    assert statuses.count("final_report") == 1 and statuses[-1] == "final_report"
    assert not TERMINAL & set(statuses)
    assert item["objective"] in events[-1]["report"]

    # The real ODR loop ran: supervisor delegated once then completed; researcher searched once.
    assert rec.supervisor_calls == 2
    assert rec.search_queries == [item["objective"]]

    # Search results entered Neosis evidence via neosis_web_search, scoped to this run, with provenance.
    assert len(rec.evidence) == 1
    ev = rec.evidence[0]
    assert ev["run_id"] == run_id and ev["workspace_id"] == workspace_id
    assert ev["locator"] == "https://offline.example/1"
    assert ev["provenance"] == {"title": "Offline source", "url": "https://offline.example/1"}
