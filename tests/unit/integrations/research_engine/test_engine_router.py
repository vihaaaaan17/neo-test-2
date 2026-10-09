"""
EngineRouter: deterministic intent routing, calibrated sufficiency diagnosis, independent readiness gates, capacity
slots, one shared turn budget, at most one sequential specialist escalation, fallback, cancellation, timeouts and
attempt recording. Engines are fakes (plus the real STORM adapter over a stand-in runner); no network, no credentials.
"""
import asyncio
import json
import sys
import time
from pathlib import Path
from uuid import uuid4

import pytest

from app.integrations.research_engine.budget import ResearchBudgetExceeded
from app.integrations.research_engine.engine import ResearchEngine, turn_response
from app.integrations.research_engine import router as router_module
from app.integrations.research_engine.router import (
    SPECIALIST_FOR,
    EngineRouter,
    SpecialistSlots,
    assess_answer,
    classify_intent,
    engine_readiness,
)

ODR, STORM, GPTR = "open_deep_research", "storm", "gpt_researcher"
LONG = " ".join(["word"] * 120)
TERMINAL = {"completed", "failed", "partial", "cancelled", "aborted_by_timeline_fence"}
CASES = json.loads((Path(__file__).resolve().parents[3] / "fixtures" / "routing" / "assessment_cases.json").read_text(encoding="utf-8"))
SUFFICIENT = next(c for c in CASES if c["id"] == "sufficient_normal")
OBJECTIVE = SUFFICIENT["objective"]


def ev(url, n, excerpt="retrieval-augmented generation reduces hallucinations in language models"):
    return {"evidence_id": f"e{n}", "url": url, "title": f"T{n}", "excerpt": excerpt, "retriever": "r", "provenance": {"url": url}}


GOOD_EVIDENCE = [ev("https://a.org/1", 1), ev("https://b.org/2", 2), ev("https://c.org/3", 3)]


class FakeStore:
    def __init__(self):
        self.evidence: list[dict] = []
        self.attempts: dict = {}
        self.answer = None
        self.usage = {"input_tokens": 1000, "output_tokens": 200, "cost": 0.0}

    async def list_evidence(self, workspace_id, run_id):
        return list(self.evidence)

    async def start_attempt(self, run_id, sequence, engine, profile, trigger, reason, routing_mode="explicit", preferred_engine=None):
        aid = uuid4()
        self.attempts[aid] = {"sequence": sequence, "engine": engine, "profile": profile, "trigger": trigger, "reason": reason,
                              "routing_mode": routing_mode, "preferred_engine": preferred_engine}
        return aid

    async def usage_since(self, run_id, since):
        return dict(self.usage)

    async def finish_attempt(self, attempt_id, **fields):
        self.attempts[attempt_id].update(fields)

    async def record_answer(self, run_id, engine, attempt_id, set_engine):
        self.answer = (engine, attempt_id, set_engine)

    def ordered(self):
        return sorted(self.attempts.values(), key=lambda a: a["sequence"])


class FakeEngine(ResearchEngine):
    timeline: list = []

    def __init__(self, name, store, text=None, evidence=None, raises=None, hang=False, sleep=0.01, metrics=None,
                 details=None):
        self.name, self.store = name, store
        self.text = SUFFICIENT["answer"] if text is None else text
        self.evidence, self.raises, self.hang, self.sleep, self.metrics, self.details = evidence, raises, hang, sleep, metrics, details
        self.cancelled = False

    async def astream_events(self, run_id, workspace_id, objective, research_context=None, **kwargs):
        FakeEngine.timeline.append(("start", self.name, time.monotonic()))
        try:
            yield {"status": "starting", "message": f"{self.name} starting"}
            await asyncio.sleep(self.sleep)
            yield {"status": "completed", "message": "engines must not end runs"}  # ignored by the router
            if self.hang:
                await asyncio.sleep(60)
            if self.raises:
                raise self.raises
            self.store.evidence.extend(self.evidence if self.evidence is not None else [])
            yield {"status": "executing", "message": "working"}
            if self.metrics:
                yield {"status": "metrics", **self.metrics}
            yield turn_response(self.text, details=self.details)
        finally:
            FakeEngine.timeline.append(("end", self.name, time.monotonic()))

    async def cancel(self):
        self.cancelled = True


def readiness_for(*eligible, states=None):
    async def readiness(engine):
        ok = engine == ODR or engine in eligible
        state = (states or {}).get(engine, "eligible" if ok else "disabled")
        return {"engine": engine, "state": state, "eligible": state == "eligible", "gate": "auto" if ok else "off",
                "checks": {}, "reason": "ok" if state == "eligible" else f"{engine} {state}"}
    return readiness


async def all_prereqs_ok(engine):
    return {"runtime": True}


def make_router(store, behaviours, mode="auto", engine=None, eligible=(), **kw):
    created = []

    def factory(name, redis, profile, token_ceiling=None):
        e = FakeEngine(name, store, **behaviours.get(name, {}))
        e.profile, e.token_ceiling = profile, token_ceiling
        created.append(e)
        return e

    kw.setdefault("readiness", readiness_for(*eligible))
    kw.setdefault("prerequisites", all_prereqs_ok)
    router = EngineRouter(routing_mode=mode, engine=engine, engine_factory=factory, store=store, **kw)
    return router, created


async def drive(router, objective=OBJECTIVE):
    return [e async for e in router.astream_events(run_id=uuid4(), workspace_id=uuid4(), objective=objective)]


def case_evidence(case, prefix="o"):
    return [{**e, "evidence_id": f"{prefix}{i}", "provenance": {"url": e["url"]}} for i, e in enumerate(case["evidence"])]


@pytest.fixture(autouse=True)
def _reset():
    FakeEngine.timeline = []
    SpecialistSlots._local.clear()
    router_module._PREREQ_CACHE.clear()


# --------------------------------------------------------------------------- #
# Intent and calibrated assessment
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("text,intent", [
    ("What is the boiling point of water?", "simple"),
    ("Who wrote Dune?", "simple"),
    ("Explain how transformers use attention and why it matters for long documents.", "normal"),
    ("What are the latest developments in solid-state batteries?", "normal"),
    ("Give me an in-depth, multi-hop investigation of how CRISPR patents shaped biotech funding.", "deep"),
    ("Do a literature review of retrieval-augmented generation.", "deep"),
    ("Find as many sources as possible about microplastics in drinking water.", "broad"),
    ("Crawl the web for every vendor offering vector databases.", "broad"),
    ("Which techniques extend transformer context windows efficiently?", "normal"),  # live misclassification fixed
    ("What are the main causes of inflation?", "normal"),
    ("When was the transformer architecture published?", "simple"),
])
def test_classify_intent(text, intent):
    assert classify_intent(text)[0] == intent


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_assessment_matches_calibration_fixture(case):
    a = assess_answer(case["answer"], case["evidence"], case["intent"], case["objective"])
    assert a.failure == case["expected"], a.metrics
    assert a.sufficient is (case["expected"] is None)
    if a.failure:
        assert a.failure in SPECIALIST_FOR and a.diagnosis[0] == a.failure


def test_cited_urls_not_backed_by_evidence_are_reported():
    answer = "Dune was written by Frank Herbert [1]. Sources: https://en.wikipedia.org/wiki/Frank_Herbert"
    m = assess_answer(answer, [], "simple", "Who wrote the novel Dune?").metrics
    assert m["cited_urls_not_retrieved"] == ["https://en.wikipedia.org/wiki/Frank_Herbert"]
    m = assess_answer(answer, [ev("https://en.wikipedia.org/wiki/Frank_Herbert", 1)], "simple", "Who wrote the novel Dune?").metrics
    assert m["cited_urls_not_retrieved"] == []


def test_evidence_row_count_alone_is_not_quality():
    many_irrelevant = [ev(f"https://x{i}.org/p", i, excerpt="sourdough bread baking temperature") for i in range(30)]
    assert assess_answer(SUFFICIENT["answer"], many_irrelevant, "normal", OBJECTIVE).failure == "no_usable_evidence"


# --------------------------------------------------------------------------- #
# Readiness gates
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_readiness_gate_states(monkeypatch):
    from app.core.config import settings

    async def prereq_ok(engine):
        return {"runtime": True}

    async def prereq_missing(engine):
        return {"runtime": False, "credentials": True}

    monkeypatch.setattr(router_module, "check_prerequisites", prereq_ok)
    monkeypatch.setattr(settings, "ROUTER_AUTO_STORM", "auto")
    assert (await engine_readiness(STORM))["state"] == "eligible"  # default "auto" gate: on when prerequisites pass
    monkeypatch.setattr(settings, "ROUTER_AUTO_STORM", "off")
    r = await engine_readiness(STORM)
    assert r["state"] == "disabled" and "ROUTER_AUTO_STORM=off" in r["reason"]
    monkeypatch.setattr(router_module, "check_prerequisites", prereq_missing)
    monkeypatch.setattr(settings, "ROUTER_AUTO_GPT_RESEARCHER", "auto")
    r = await engine_readiness(GPTR)
    assert r["state"] == "unavailable" and "runtime" in r["reason"]


def test_defaults_enable_specialist_auto_routing():
    from app.core.config import Settings

    fields = Settings.model_fields
    assert fields["ROUTER_AUTO_STORM"].default == "auto" and fields["ROUTER_AUTO_GPT_RESEARCHER"].default == "auto"
    assert fields["ROUTER_TURN_DEADLINE_S"].default < 1800  # below the ARQ job_timeout


# --------------------------------------------------------------------------- #
# Routing through router -> adapter
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_sufficient_odr_answer_returns_immediately_with_one_attempt():
    store = FakeStore()
    router, created = make_router(store, {ODR: {"evidence": case_evidence(SUFFICIENT)}}, eligible=(STORM, GPTR))
    events = await drive(router)

    statuses = [e["status"] for e in events]
    assert statuses.count("turn_response") == 1 and statuses[-1] == "turn_response"
    assert not TERMINAL & set(statuses)
    final = events[-1]
    assert [e.name for e in created] == [ODR] and created[0].profile == "balanced"
    assert created[0].token_ceiling == router._token_ceiling  # the turn's whole token allowance reaches ODR
    routing = final["routing"]
    assert routing["answered_by"] == ODR and routing["escalated"] is False and routing["escalation"] is None
    assert routing["preferred_engine"] == ODR and routing["answer_budget_profile"] == "balanced"
    attempt = store.ordered()[0]
    assert attempt["status"] == "answered" and attempt["routing_mode"] == "auto" and attempt["preferred_engine"] == ODR
    assert attempt["assessment"]["decision"] == {"sufficient": True}
    assert store.answer[0] == ODR and store.answer[2] is True


@pytest.mark.asyncio
async def test_simple_question_passes_the_low_profile_to_the_engine():
    store = FakeStore()
    router, created = make_router(store, {ODR: {"text": "The novel Dune was written by Frank Herbert and published in 1965."}},
                                  eligible=(STORM, GPTR))
    events = await drive(router, "Who wrote the novel Dune?")
    assert [e.name for e in created] == [ODR] and created[0].profile == "low"
    assert events[-1]["routing"]["intent"] == "simple" and events[-1]["routing"]["escalated"] is False


def test_default_factory_builds_odr_with_the_selected_profile_and_ceiling():
    """The profile reaches the real adapter (not just the routing label)."""
    from app.integrations.research_engine.open_deep_research.engine import ODR_BUDGET_PROFILES, OpenDeepResearchEngine
    from app.integrations.research_engine.router import _default_factory

    engine = _default_factory(ODR, None, "low", 5000)
    assert isinstance(engine, OpenDeepResearchEngine) and engine.budget_profile == "low" and engine.token_ceiling == 5000
    assert ODR_BUDGET_PROFILES["low"]["max_researcher_iterations"] < ODR_BUDGET_PROFILES["balanced"]["max_researcher_iterations"]


@pytest.mark.asyncio
@pytest.mark.parametrize("objective,specialist", [
    ("Give me an in-depth investigation of the causes of the 2008 financial crisis.", STORM),
    ("Find as many sources as possible about microplastics in drinking water.", GPTR),
])
async def test_deep_and_broad_requests_select_the_eligible_specialist_directly(objective, specialist):
    store = FakeStore()
    router, created = make_router(store, {specialist: {"evidence": GOOD_EVIDENCE}}, eligible=(STORM, GPTR))
    events = await drive(router, objective)
    assert [e.name for e in created] == [specialist]  # no ODR cost first
    attempt = store.ordered()[0]
    assert attempt["trigger"] == "intent" and attempt["preferred_engine"] == specialist and attempt["profile"] == "bounded"
    assert events[-1]["routing"]["answered_by"] == specialist and events[-1]["routing"]["budget_enforced"] is False


@pytest.mark.asyncio
async def test_preferred_specialist_disabled_falls_back_to_odr_and_records_why():
    store = FakeStore()
    router, created = make_router(store, {ODR: {"evidence": GOOD_EVIDENCE, "text": " ".join(["investigation causes crisis"] * 100)}})
    events = await drive(router, "Give me an in-depth investigation of the causes of the 2008 financial crisis.")
    routing = events[-1]["routing"]
    assert [e.name for e in created] == [ODR] and created[0].profile == "deep"
    assert routing["preferred_engine"] == STORM and routing["answered_by"] == ODR
    assert routing["readiness"][0]["state"] == "disabled" and "not used" in store.ordered()[0]["reason"]


@pytest.mark.asyncio
@pytest.mark.parametrize("case_id,specialist", [
    ("low_source_coverage", GPTR), ("duplicated_sources", GPTR), ("no_usable_evidence", GPTR), ("uncited_claims", GPTR),
    ("insufficient_depth", STORM), ("unanswered_parts", STORM), ("unresolved_relationship", STORM), ("engine_reported_gap", STORM),
])
async def test_weak_odr_answer_escalates_once_to_the_matching_specialist(case_id, specialist):
    case = next(c for c in CASES if c["id"] == case_id)
    store = FakeStore()
    router, created = make_router(
        store,
        {ODR: {"text": case["answer"], "evidence": case_evidence(case)},
         specialist: {"text": "specialist answer " + LONG, "evidence": [ev("https://x.org/a", 7), ev("https://y.org/b", 8)]}},
        eligible=(STORM, GPTR),
    )
    events = await drive(router, case["objective"])

    assert [e.name for e in created] == [ODR, specialist]  # one escalation, never both specialists
    routing = events[-1]["routing"]
    assert routing["answered_by"] == specialist and routing["escalated"] is True
    assert routing["escalation"]["reason"] == case["expected"] and routing["escalation"]["to"] == specialist
    assert events[-1]["evidence_refs"] == ["e7", "e8"]  # the answering attempt's own evidence
    first, second = store.ordered()
    assert (first["trigger"], first["status"], second["trigger"], second["status"]) == ("initial", "answered", "escalation", "answered")
    assert first["assessment"]["decision"]["escalate_to"] == specialist  # the first attempt is kept and auditable
    t = {(kind, name): ts for kind, name, ts in FakeEngine.timeline}
    assert t[("start", specialist)] >= t[("end", ODR)]  # strictly sequential


@pytest.mark.asyncio
async def test_disabled_gate_blocks_escalation_transparently():
    store = FakeStore()
    router, created = make_router(store, {ODR: {"text": "Short answer [1].", "evidence": GOOD_EVIDENCE}})  # specialists off
    events = await drive(router)
    routing = events[-1]["routing"]
    assert [e.name for e in created] == [ODR] and routing["answered_by"] == ODR and routing["escalated"] is False
    assert routing["escalation"]["to"] == STORM and "disabled" in routing["escalation"]["blocked"]
    assert store.ordered()[0]["assessment"]["decision"]["blocked"]
    assert any("blocked" in e.get("message", "") for e in events)


@pytest.mark.asyncio
async def test_capacity_limit_blocks_escalation(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ROUTER_MAX_CONCURRENT_STORM", 1)
    SpecialistSlots._local[STORM] = 1  # another turn holds the only STORM slot
    store = FakeStore()
    router, created = make_router(store, {ODR: {"text": "Short answer [1].", "evidence": GOOD_EVIDENCE}}, eligible=(STORM,))
    events = await drive(router)
    assert [e.name for e in created] == [ODR] and "concurrency limit" in events[-1]["routing"]["escalation"]["blocked"]
    assert SpecialistSlots._local[STORM] == 1  # nothing leaked


@pytest.mark.asyncio
async def test_slots_are_released_after_specialist_attempts():
    store = FakeStore()
    router, _ = make_router(store, {STORM: {"evidence": GOOD_EVIDENCE}}, eligible=(STORM,))
    await drive(router, "Give me an in-depth investigation of the causes of the 2008 financial crisis.")
    assert SpecialistSlots._local.get(STORM, 0) == 0


@pytest.mark.asyncio
async def test_turn_deadline_is_shared_and_blocks_a_late_escalation():
    store = FakeStore()
    router, created = make_router(store, {ODR: {"text": "Short answer [1].", "evidence": GOOD_EVIDENCE, "sleep": 0.3}},
                                  eligible=(STORM,), turn_deadline_s=1.0, min_specialist_time_s=0.9)
    events = await drive(router)
    assert [e.name for e in created] == [ODR]
    assert "turn deadline" in events[-1]["routing"]["escalation"]["blocked"]


@pytest.mark.asyncio
async def test_specialist_timeout_is_capped_by_the_remaining_turn_deadline():
    store = FakeStore()
    router, created = make_router(store, {ODR: {"text": "Short answer [1].", "evidence": GOOD_EVIDENCE, "sleep": 0.2},
                                          STORM: {"hang": True}},
                                  eligible=(STORM,), turn_deadline_s=1.0, min_specialist_time_s=0.1,
                                  timeouts={ODR: 30, STORM: 30, GPTR: 30})
    t0 = time.monotonic()
    events = await drive(router)
    assert time.monotonic() - t0 < 3  # the 30 s engine timeout did not restart the clock
    assert store.ordered()[1]["status"] == "timeout" and events[-1]["routing"]["answered_by"] == ODR
    assert created[1].cancelled


@pytest.mark.asyncio
async def test_turn_token_ceiling_is_shared_across_attempts():
    store = FakeStore()
    store.usage = {"input_tokens": 900, "output_tokens": 200, "cost": 0.0}
    router, created = make_router(store, {ODR: {"text": "Short answer [1].", "evidence": GOOD_EVIDENCE}}, eligible=(STORM,),
                                  token_ceiling=1000)
    events = await drive(router)
    assert [e.name for e in created] == [ODR] and "token ceiling" in events[-1]["routing"]["escalation"]["blocked"]
    assert events[-1]["routing"]["timings"]["turn_tokens_used"] == 1100


@pytest.mark.asyncio
async def test_escalation_disabled_by_config():
    store = FakeStore()
    router, created = make_router(store, {ODR: {"text": "Short answer [1].", "evidence": GOOD_EVIDENCE}}, eligible=(STORM,),
                                  max_specialist_escalations=0)
    events = await drive(router)
    assert [e.name for e in created] == [ODR] and "disabled" in events[-1]["routing"]["escalation"]["blocked"]


@pytest.mark.asyncio
async def test_specialist_failure_after_escalation_keeps_odr_answer_and_its_evidence():
    store = FakeStore()
    router, created = make_router(
        store, {ODR: {"text": "Short answer [1].", "evidence": GOOD_EVIDENCE}, STORM: {"raises": RuntimeError("storm crashed")}},
        eligible=(STORM,),
    )
    events = await drive(router)
    routing = events[-1]["routing"]
    assert routing["answered_by"] == ODR and "storm crashed" in routing["escalation"]["specialist_failed"]
    assert events[-1]["evidence_refs"] == ["e1", "e2", "e3"]  # the initial engine's evidence is preserved
    assert [a["status"] for a in store.ordered()] == ["answered", "failed"] and len(created) == 2


@pytest.mark.asyncio
async def test_direct_specialist_failure_falls_back_to_odr_once():
    store = FakeStore()
    router, created = make_router(store, {GPTR: {"raises": RuntimeError("gptr down")}, ODR: {"evidence": GOOD_EVIDENCE}},
                                  eligible=(GPTR,))
    events = await drive(router, "Find as many sources as possible about microplastics.")
    assert [e.name for e in created] == [GPTR, ODR]
    assert [a["trigger"] for a in store.ordered()] == ["intent", "fallback"]
    assert events[-1]["routing"]["answered_by"] == ODR and events[-1]["routing"]["escalation"]["reason"] == "specialist_failed"


@pytest.mark.asyncio
async def test_odr_failure_and_empty_answers_are_raised_not_completed():
    store = FakeStore()
    router, _ = make_router(store, {ODR: {"raises": RuntimeError("odr broke")}}, eligible=(STORM, GPTR))
    with pytest.raises(RuntimeError, match="odr broke"):
        await drive(router)
    store = FakeStore()
    router, _ = make_router(store, {ODR: {"text": "   "}})
    with pytest.raises(RuntimeError, match="empty"):
        await drive(router)


@pytest.mark.asyncio
async def test_budget_exceeded_propagates_and_is_recorded():
    store = FakeStore()
    router, _ = make_router(store, {ODR: {"raises": ResearchBudgetExceeded("too many tokens")}}, eligible=(STORM,))
    with pytest.raises(ResearchBudgetExceeded):
        await drive(router)
    assert store.ordered()[0]["status"] == "budget_exceeded"


@pytest.mark.asyncio
async def test_cancellation_stops_the_active_engine_and_records_cancelled():
    store = FakeStore()
    router, created = make_router(store, {STORM: {"hang": True}}, eligible=(STORM,))
    started = asyncio.Event()

    async def consume():
        async for e in router.astream_events(run_id=uuid4(), workspace_id=uuid4(),
                                             objective="Give me an in-depth investigation of the 2008 crisis."):
            if e.get("status") == "starting":
                started.set()

    task = asyncio.create_task(consume())
    await asyncio.wait_for(started.wait(), timeout=5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert store.ordered()[0]["status"] == "cancelled" and created[0].cancelled
    assert ("end", STORM) in {(k, n) for k, n, _ in FakeEngine.timeline}
    assert SpecialistSlots._local.get(STORM, 0) == 0  # slot released on cancellation


@pytest.mark.asyncio
async def test_router_timeout_terminates_a_real_storm_subprocess(tmp_path):
    """Router timeout -> the real STORM adapter's process is terminated (not left running)."""
    from unittest.mock import AsyncMock, patch
    from app.core.config import settings
    from app.integrations.research_engine.storm.engine import StormResearchEngine

    runner = tmp_path / "slow_runner.py"
    runner.write_text("import json, sys, time\njson.load(sys.stdin)\n"
                      "print('@@NEOSIS@@' + json.dumps({'type': 'phase', 'phase': 'executing', 'message': 'x'}), flush=True)\n"
                      "time.sleep(60)\n")
    made = []

    def factory(name, redis, profile, token_ceiling=None):
        made.append(StormResearchEngine(python_executable=sys.executable, runner_path=str(runner), budget_profile=profile))
        return made[-1]

    store = FakeStore()
    router = EngineRouter(routing_mode="explicit", engine=STORM, engine_factory=factory, store=store,
                          prerequisites=all_prereqs_ok, timeouts={ODR: 5, STORM: 3, GPTR: 5})
    with patch("app.core.config.resolve_llm_provider") as resolve, \
         patch.object(StormResearchEngine, "_record_usage", new_callable=AsyncMock), \
         patch.object(settings, "TAVILY_API_KEY", "tvly-test"):
        resolve.return_value.api_key, resolve.return_value.base_url, resolve.return_value.model = "k", "http://x/v1", "auto"
        with pytest.raises(RuntimeError, match="timeout"):
            await drive(router, "anything")
    assert store.ordered()[0]["status"] == "timeout"
    assert made[0]._proc is None  # the adapter's cleanup terminated and released its subprocess
    assert made[0].runner_args["max_perspective"] == 2  # the bounded STORM profile reached the adapter


@pytest.mark.asyncio
async def test_explicit_mode_runs_only_the_named_engine_and_checks_its_runtime():
    store = FakeStore()
    router, created = make_router(store, {STORM: {"text": "Short."}}, mode="explicit", engine=STORM, eligible=(GPTR,))
    events = await drive(router)
    assert [e.name for e in created] == [STORM]
    routing = events[-1]["routing"]
    assert routing["mode"] == "explicit" and routing["answered_by"] == STORM and routing["escalation"] is None
    assert store.answer[2] is False

    async def missing(engine):
        return {"knowledge_storm_importable": False}

    router, created = make_router(FakeStore(), {}, mode="explicit", engine=STORM, prerequisites=missing)
    with pytest.raises(RuntimeError, match="knowledge_storm_importable"):
        await drive(router)
    assert created == []


@pytest.mark.asyncio
async def test_engine_metrics_are_recorded_on_the_attempt():
    store = FakeStore()
    router, _ = make_router(store, {ODR: {"evidence": case_evidence(SUFFICIENT),
                                          "metrics": {"model_calls": 9, "input_tokens": 50, "output_tokens": 5,
                                                      "node_ms": {"research_supervisor": 1234}}}})
    events = await drive(router)
    attempt = store.ordered()[0]
    assert attempt["timings"]["engine"]["node_ms"] == {"research_supervisor": 1234}
    assert {"engine_init_ms", "first_event_ms", "upstream_ms", "evidence_collection_ms"} <= set(attempt["timings"]["router"])
    assert attempt["input_tokens"] == 50  # measured tokens reported by the engine win over stored estimates
    assert events[-1]["routing"]["attempts"][0]["usage_quality"] == {"tokens": "measured", "cost": "unavailable"}


@pytest.mark.asyncio
async def test_storm_style_details_travel_with_the_answer():
    store = FakeStore()
    router, _ = make_router(store, {STORM: {"text": "Lead answer [1].", "details": "# summary\nLead\n\n# Body\nFull article"}},
                            mode="explicit", engine=STORM)
    events = await drive(router)
    assert events[-1]["text"] == "Lead answer [1]." and events[-1]["details"].endswith("Full article")


@pytest.mark.asyncio
async def test_answer_is_not_lost_when_engine_finishes_while_consumer_is_slow():
    store = FakeStore()

    class Burst(ResearchEngine):
        async def astream_events(self, run_id, workspace_id, objective, research_context=None, **kwargs):
            yield {"status": "synthesizing", "message": "writing"}
            await asyncio.sleep(0.01)  # real ODR does DB I/O here, so the engine finishes while the consumer is busy
            store.evidence.extend(case_evidence(SUFFICIENT))
            yield turn_response(SUFFICIENT["answer"])

        async def cancel(self):
            pass

    router = EngineRouter(routing_mode="auto", engine_factory=lambda *a, **k: Burst(), store=store, readiness=readiness_for())
    events = []
    async for e in router.astream_events(run_id=uuid4(), workspace_id=uuid4(), objective=OBJECTIVE):
        events.append(e)
        await asyncio.sleep(0.05)
    assert events[-1]["status"] == "turn_response" and events[-1]["text"] == SUFFICIENT["answer"]


def test_usage_quality_reports_what_was_actually_observed():
    from app.integrations.research_engine.router import observed_usage_quality

    assert observed_usage_quality(STORM, {"input_tokens": 0, "output_tokens": 0}, {"model_calls": 30}) == \
        {"tokens": "unavailable", "cost": "unavailable"}
    assert observed_usage_quality(ODR, {"input_tokens": 10, "output_tokens": 5}, {"model_calls": 2})["tokens"] == "measured"
    assert observed_usage_quality(GPTR, {"cost": 0.02}, {}) == {"tokens": "unavailable", "cost": "estimated"}
    assert observed_usage_quality(GPTR, {"cost": 0.0}, {})["cost"] == "unavailable"


@pytest.mark.asyncio
async def test_unsourced_specialist_answers_are_not_used():
    # Direct route: STORM answers with no evidence -> rejected, ODR fallback answers.
    store = FakeStore()
    router, created = make_router(store, {STORM: {"text": "Lead with phantom citations [1][2].", "evidence": []},
                                          ODR: {"evidence": GOOD_EVIDENCE}}, eligible=(STORM,))
    events = await drive(router, "Give me an in-depth investigation of the causes of the 2008 financial crisis.")
    assert [e.name for e in created] == [STORM, ODR]
    assert [a["status"] for a in store.ordered()] == ["rejected", "answered"]
    assert events[-1]["routing"]["answered_by"] == ODR
    # Escalation: GPT-R answers with no evidence -> ODR answer kept.
    store = FakeStore()
    case = next(c for c in CASES if c["id"] == "low_source_coverage")
    router, created = make_router(store, {ODR: {"text": case["answer"], "evidence": case_evidence(case)},
                                          GPTR: {"text": "broad " + LONG, "evidence": []}}, eligible=(GPTR,))
    events = await drive(router, case["objective"])
    assert events[-1]["routing"]["answered_by"] == ODR
    assert "without any persisted evidence" in events[-1]["routing"]["escalation"]["specialist_failed"]


def test_storm_unmatched_citation_markers_are_removed():
    from app.integrations.research_engine.storm.engine import strip_unmatched_citations

    text, removed = strip_unmatched_citations("A [1]. B [2]. C [3].", [{"index": 2, "url": "u"}])
    assert text == "A . B [2]. C ." and removed == 2


@pytest.mark.asyncio
async def test_unmetered_specialist_usage_is_marked_not_counted_as_zero():
    store = FakeStore()
    store.usage = {"input_tokens": 0, "output_tokens": 0, "cost": 0.0}
    router, _ = make_router(store, {STORM: {"evidence": GOOD_EVIDENCE, "metrics": {"model_calls": 30}}}, eligible=(STORM,))
    events = await drive(router, "Give me an in-depth investigation of the causes of the 2008 financial crisis.")
    budget = events[-1]["routing"]["budget"]
    assert budget["token_accounting"] == "incomplete" and budget["unmetered_attempts"] == ["storm#1"]
    assert budget["attempts_used"] == 1 and budget["max_attempts"] == 2


@pytest.mark.asyncio
async def test_escalation_after_an_initial_attempt_that_used_most_of_the_deadline_is_capped_not_reset():
    """ODR consumes most of the turn; the specialist only gets what is left and the attempt limit still holds."""
    store = FakeStore()
    router, created = make_router(store, {ODR: {"text": "Short answer [1].", "evidence": GOOD_EVIDENCE, "sleep": 0.6},
                                          STORM: {"hang": True}},
                                  eligible=(STORM,), turn_deadline_s=1.2, min_specialist_time_s=0.2,
                                  timeouts={ODR: 30, STORM: 30, GPTR: 30})
    t0 = time.monotonic()
    events = await drive(router)
    elapsed = time.monotonic() - t0
    assert elapsed < 2.5, elapsed  # whole turn bounded by the ORIGINAL 1.2 s deadline (+ cleanup), not 30 s per engine
    first, second = store.ordered()
    assert second["status"] == "timeout" and second["timings"]["router"]["timeout_s"] <= 1
    assert events[-1]["routing"]["budget"]["attempts_used"] == 2 and events[-1]["routing"]["answered_by"] == ODR


@pytest.mark.asyncio
async def test_deadline_exhausted_during_the_initial_attempt_fails_the_turn_and_records_timeout():
    store = FakeStore()
    router, created = make_router(store, {ODR: {"hang": True}}, eligible=(STORM, GPTR), turn_deadline_s=0.5,
                                  timeouts={ODR: 30, STORM: 30, GPTR: 30})
    t0 = time.monotonic()
    with pytest.raises(RuntimeError, match="timeout"):
        await drive(router)
    assert time.monotonic() - t0 < 2
    assert [a["status"] for a in store.ordered()] == ["timeout"] and created[0].cancelled  # no second attempt started


def test_effective_deadline_never_reaches_the_arq_job_timeout():
    from types import SimpleNamespace
    from app.core.config import effective_turn_deadline_s

    assert effective_turn_deadline_s(SimpleNamespace(ROUTER_TURN_DEADLINE_S=1500, ARQ_JOB_TIMEOUT_S=1800, ROUTER_FINALIZE_MARGIN_S=180)) == 1500
    # A misconfigured (too long) deadline is clipped so ARQ cannot kill the job before finalization.
    assert effective_turn_deadline_s(SimpleNamespace(ROUTER_TURN_DEADLINE_S=2400, ARQ_JOB_TIMEOUT_S=1800, ROUTER_FINALIZE_MARGIN_S=180)) == 1620
    from app.workers.settings import WorkerSettings
    from app.core.config import settings
    assert WorkerSettings.job_timeout == settings.ARQ_JOB_TIMEOUT_S
    assert effective_turn_deadline_s() + settings.ROUTER_FINALIZE_MARGIN_S <= WorkerSettings.job_timeout


@pytest.mark.asyncio
async def test_specialist_setup_failure_keeps_the_initial_answer():
    store = FakeStore()

    def factory(name, redis, profile, token_ceiling=None):
        if name == STORM:
            raise ImportError("knowledge_storm missing")
        return FakeEngine(name, store, text="Short answer [1].", evidence=GOOD_EVIDENCE)

    router = EngineRouter(routing_mode="auto", engine_factory=factory, store=store, readiness=readiness_for(STORM),
                          prerequisites=all_prereqs_ok)
    events = await drive(router)
    routing = events[-1]["routing"]
    assert routing["answered_by"] == ODR and "engine setup failed" in routing["escalation"]["specialist_failed"]
    assert [a["status"] for a in store.ordered()] == ["answered", "failed"]


def test_router_rejects_bad_modes():
    with pytest.raises(ValueError):
        EngineRouter(routing_mode="smart")
    with pytest.raises(ValueError):
        EngineRouter(routing_mode="explicit", engine="auto")


def test_router_has_no_parallel_dispatch():
    import inspect

    src = inspect.getsource(router_module)
    assert "gather(" not in src and "TaskGroup" not in src
