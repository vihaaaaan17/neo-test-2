"""
EngineRouter: picks one research engine per attempt and escalates at most once, sequentially.

    Worker -> EngineRouter -> one active adapter -> upstream engine

The router contains no research logic. It only:
  * classifies the request with deterministic rules (`classify_intent`) and picks a preferred engine;
  * checks that engine's readiness gate (config gate + runtime prerequisites + capacity slot);
  * judges an ODR answer with deterministic, explainable checks over the answer and this attempt's evidence
    (`assess_answer`) and, if insufficient, escalates to at most ONE specialist chosen by the diagnosed deficiency;
  * enforces one shared turn budget across every attempt (wall-clock deadline, measured-token ceiling, max attempts);
  * records every attempt (preferred vs actual engine, trigger, reason, outcome, timings, usage) in
    `research_engine_attempts`.

Attempts never overlap: each one is awaited to completion (or stopped) before the next starts. The router implements the
`ResearchEngine` contract itself, so the worker still sees progress events and exactly one `turn_response`, and still
owns terminal state. Cancellation and budget stops propagate to the worker unchanged.
"""
import asyncio
import importlib.util
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Awaitable, Callable, Optional
from urllib.parse import urlparse
from uuid import UUID

from app.integrations.research_engine.engine import (
    ResearchEngine,
    SUPPORTED_ENGINES,
    TURN_RESPONSE,
    turn_response,
)

logger = logging.getLogger(__name__)

ODR, STORM, GPTR = "open_deep_research", "storm", "gpt_researcher"
SPECIALISTS = (STORM, GPTR)
_TERMINAL = frozenset({"completed", "failed", "partial", "cancelled", "aborted_by_timeline_fence"})

BUDGET_ENFORCEMENT = {
    ODR: "enforced mid-run: model-call, token and search caps of the ODR budget profile, capped by the turn's token ceiling",
    STORM: "wall-clock and upstream-config bounded only (fewer perspectives/turns/queries); STORM has no token control - "
           "its LM usage is recorded after the run",
    GPTR: "wall-clock and upstream-config bounded only (iterations, results, scrapers, words); GPT-Researcher has no token "
          "control - its estimated cost is recorded after the run",
}
# Whether tokens / cost are measured by the engine, estimated, or not available at all.
USAGE_QUALITY = {
    ODR: {"tokens": "measured", "cost": "unavailable"},
    STORM: {"tokens": "measured", "cost": "unavailable"},
    GPTR: {"tokens": "unavailable", "cost": "estimated"},
}

# --------------------------------------------------------------------------- #
# Intent (deterministic)
# --------------------------------------------------------------------------- #
_BROAD = re.compile(
    r"\b(crawl\w*|source discovery|discover (new |more )?sources|find (as many|all|every|more)\b[^.?!]{0,40}\b(sources|websites|sites|papers|articles|references|vendors|companies|tools)"
    r"|gather (as many |all |more )?(sources|references)|list (of )?(all |the )?(sources|websites|papers|articles)"
    r"|(broad|wide|web[- ]wide) (search|sweep|crawl|scan|survey)|scan the web|search widely|as many sources as possible"
    r"|survey (the )?(web|literature|landscape|market)|landscape of)\b",
    re.I,
)
_DEEP = re.compile(
    r"\b(deep[- ]dive|in[- ]depth|exhaustive(ly)?|comprehensive (analysis|investigation|review|study|overview)"
    r"|multi[- ]hop|thorough(ly)? (investigat\w*|analy[sz]\w*|research\w*)|investigate (this )?thoroughly"
    r"|deep (research|investigation|analysis)|literature review|full (history|analysis)|leave no stone unturned"
    r"|trace (the )?(chain|causes|history))\b",
    re.I,
)
_SIMPLE_START = re.compile(
    r"^\s*(what|who|when|where|which|define|how (many|much|old|tall|long|far)|is|are|was|were|does|did|do|can)\b", re.I
)
_NOT_SIMPLE = re.compile(
    r"\b(why|explain|compare|comparison|versus|vs\.?|analy[sz]e|evaluate|pros and cons|trade-?offs?|latest|current|recent|today"
    r"|this (week|month|year)"
    # questions asking for several things need research even when short (live: "Which techniques extend ...?")
    r"|techniques|methods|approaches|ways|strategies|examples|options|alternatives|factors|causes|effects|benefits"
    r"|advantages|disadvantages|differences|types|kinds|challenges|risks|best practices)\b|^\s*what are\b",
    re.I,
)


def classify_intent(objective: str) -> tuple[str, str]:
    """Return (intent, matched_rule). Intents: simple | normal | deep | broad."""
    text = objective or ""
    if m := _BROAD.search(text):
        return "broad", f"broad-discovery phrase {m.group(0)!r}"
    if m := _DEEP.search(text):
        return "deep", f"deep-investigation phrase {m.group(0)!r}"
    words = len(text.split())
    if words <= 14 and _SIMPLE_START.search(text) and not _NOT_SIMPLE.search(text):
        return "simple", f"short factual question ({words} words)"
    return "normal", "default research question"


PREFERRED_ENGINE = {"simple": ODR, "normal": ODR, "deep": STORM, "broad": GPTR}
ODR_PROFILE_FOR = {"simple": "low", "normal": "balanced", "deep": "deep", "broad": "balanced"}

# --------------------------------------------------------------------------- #
# Sufficiency assessment (deterministic; no LLM evaluator)
# --------------------------------------------------------------------------- #
_STOP = set("""
what which whom whose when where while does doing done have having been being were will would could should shall might
must about above after again against before because between both during each from further here into more most other
over same some such than that their theirs them then there these they this those through under until very with within
without your yours also just like many much make made only really thing things explain describe tell give show please
using used uses work works cite current sources source source's answer question questions know find way ways well
compare comparison versus difference differences between relate related relationship affect affects impact impacts
""".split())
_WORD = re.compile(r"[a-z][a-z0-9\-]{3,}")


def _stem(w: str) -> str:
    for suf, rep in (("ies", "y"), ("ings", ""), ("ing", ""), ("es", ""), ("s", ""), ("ed", "")):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            w = w[: -len(suf)] + rep
            break
    return w[:-1] if w.endswith("e") and len(w) > 4 else w  # reduce / reduces / reduced -> reduc


def key_terms(text: str) -> set[str]:
    return {_stem(w) for w in _WORD.findall((text or "").lower()) if w not in _STOP}


_PART_SPLIT = re.compile(r"[?;]|\.\s|,?\s+and\s+(?=(?:how|why|what|when|where|which|who|whether)\b)", re.I)
_COMPARE = re.compile(r"(?:compare|comparing|difference(?:s)? between)\s+(.+?)\s+(?:and|with|to|vs\.?|versus)\s+(.+)", re.I)
_VERSUS = re.compile(r"(.+?)\s+(?:vs\.?|versus|compared (?:to|with))\s+(.+)", re.I)


_ANCHOR = re.compile(r"\b[A-Za-z]*[A-Z0-9][A-Za-z0-9\-]*\b")


def anchor_terms(part: str) -> list[str]:
    """Distinctive tokens of a sub-question (acronyms, names, tokens with digits; not its first word) - e.g. BM25, Dune."""
    tokens = _ANCHOR.findall(part)
    first = (part.split() or [""])[0].strip("?,.;:")
    return [t for t in tokens if len(t) >= 2 and t != first and not t.isdigit() or (t.isdigit() and len(t) == 4)]


def question_parts(objective: str) -> list[str]:
    """Sub-questions / compared items the answer must address (deterministic split)."""
    parts: list[str] = []
    for chunk in _PART_SPLIT.split(objective or ""):
        if not chunk or not chunk.strip():
            continue
        m = _COMPARE.search(chunk) or _VERSUS.search(chunk)
        parts.extend([m.group(1), m.group(2)] if m else [chunk])
    return [p.strip() for p in parts if key_terms(p)]


_RELATIONAL_Q = re.compile(
    r"\b(how (does|do|did|can|could|might)\b.+\b(affect|impact|influence|relate|lead|cause|reduce|increase|improve|change)\w*"
    r"|relationship between|impact of .+ on|effect of .+ on|influence of .+ on|why\b|caus(e|es|ed) of|compared? (to|with)|versus|vs\.?)",
    re.I,
)
_CONNECTIVE = re.compile(
    r"\b(because|due to|leads? to|led to|results? in|resulting in|caus(e|es|ed|ing)|therefore|thus|hence|as a result"
    r"|which means|compared (to|with)|whereas|unlike|in contrast|by contrast|however|so that|enabl(e|es|ing)|reduc(e|es|ing)"
    r"|increas(e|es|ing)|prevent(s|ing)?|allow(s|ing)?|by (grounding|retrieving|providing|adding))\b",
    re.I,
)
_UNSUPPORTED = re.compile(
    r"(could not|couldn't|was unable to|unable to|did not|didn't) (find|locate|verify|confirm|identify)"
    r"|no (reliable |relevant |specific |credible |public )?(information|sources|evidence|data|records) (was |were |is |are )?(found|available)"
    r"|insufficient (evidence|information|data)|not enough (information|evidence|data)|remains? unclear|unknown at this time"
    r"|i (do not|don't) have (access|information)",
    re.I,
)
_CITATION = re.compile(r"\]\(https?://|\[\d+(?:\s*,\s*\d+)*\]|\(https?://|https?://")
_FACTUAL = re.compile(r"\d|%|\baccording to\b|\b(first|largest|smallest|most|least|record)\b", re.I)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")

THRESHOLDS: dict[str, dict[str, float]] = {
    # min_words: answer length; min_relevant_domains: distinct domains among evidence relevant to the question;
    # max_dup: allowed duplicate share (same URL or near-identical content), checked once there are >= 4 evidence rows.
    "simple": {"min_words": 12, "min_relevant_domains": 0, "max_dup": 1.0, "min_part_coverage": 0.34},
    "normal": {"min_words": 80, "min_relevant_domains": 2, "max_dup": 0.5, "min_part_coverage": 0.5},
    "deep": {"min_words": 250, "min_relevant_domains": 3, "max_dup": 0.5, "min_part_coverage": 0.5},
    "broad": {"min_words": 80, "min_relevant_domains": 4, "max_dup": 0.4, "min_part_coverage": 0.5},
}

# Deficiency -> specialist. Depth / unanswered / unresolved -> STORM; coverage / relevance / duplication / support -> GPT-R.
SPECIALIST_FOR = {
    "empty_answer": STORM,
    "unanswered_parts": STORM,
    "unresolved_relationship": STORM,
    "engine_reported_gap": STORM,
    "insufficient_depth": STORM,
    "no_usable_evidence": GPTR,
    "low_source_coverage": GPTR,
    "excessive_duplication": GPTR,
    "uncited_claims": GPTR,
}
# First matching deficiency decides the specialist.
_PRIORITY = ["empty_answer", "no_usable_evidence", "low_source_coverage", "excessive_duplication", "unanswered_parts",
             "unresolved_relationship", "engine_reported_gap", "uncited_claims", "insufficient_depth"]


@dataclass
class Assessment:
    sufficient: bool
    failure: Optional[str]
    diagnosis: list = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


def observed_usage_quality(engine: str, usage: dict, metrics: dict) -> dict:
    """
    The engine's nominal usage quality, downgraded to what was actually observed: an engine that should report tokens but
    reported none after making model calls (e.g. STORM's LiteLLM usage through a gateway that omits it) is "unavailable".
    """
    quality = dict(USAGE_QUALITY.get(engine, {"tokens": "unavailable", "cost": "unavailable"}))
    tokens = int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
    if quality["tokens"] == "measured" and tokens == 0 and int(metrics.get("model_calls") or 0) > 0:
        quality["tokens"] = "unavailable"
    if quality["cost"] == "estimated" and not float(usage.get("cost") or 0):
        quality["cost"] = "unavailable"
    return quality


def _domain(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host or None


def assess_answer(text: str, evidence: list[dict], intent: str, objective: str = "") -> Assessment:
    """Explainable sufficiency checks. `evidence` is this attempt's evidence views (url, title, excerpt)."""
    th = THRESHOLDS.get(intent, THRESHOLDS["normal"])
    answer = text or ""
    words = len(answer.split())
    answer_terms = key_terms(answer)
    q_terms = key_terms(objective)

    # Evidence relevance / diversity / duplication.
    need = 1 if len(q_terms) <= 3 else 2
    relevant = [e for e in evidence if len(q_terms & key_terms(f"{e.get('title') or ''} {e.get('excerpt') or ''}")) >= need]
    relevant_domains = {d for d in (_domain(e.get("url")) for e in relevant) if d}
    keys = []
    for e in evidence:
        snippet = re.sub(r"\s+", " ", (e.get("excerpt") or "").lower())[:120]
        keys.append((e.get("url"), snippet))
    unique_urls = {k[0] for k in keys if k[0]}
    unique_content = {k[1] for k in keys if k[1]}
    dup_ratio = round(1 - min(len(unique_urls) or len(keys), len(unique_content) or len(keys)) / len(keys), 3) if keys else 0.0

    # Question parts and relationships.
    parts = question_parts(objective)
    coverage = {p: round(len(key_terms(p) & answer_terms) / len(key_terms(p)), 2) for p in parts}
    answer_lower = answer.lower()
    missing_anchors = {p: [a for a in anchor_terms(p) if not re.search(rf"\b{re.escape(a.lower())}\b", answer_lower)]
                       for p in parts}
    unanswered = [p for p, c in coverage.items() if c < th["min_part_coverage"] or missing_anchors.get(p)]
    relational = bool(_RELATIONAL_Q.search(objective or ""))
    resolved = bool(_CONNECTIVE.search(answer))

    # Claims and their support.
    sentences = [s for s in _SENTENCE.split(answer) if len(s.split()) >= 5 and not s.lstrip().startswith(("#", "[", "-   http"))]
    factual = [s for s in sentences if _FACTUAL.search(s)]
    uncited = [s for s in factual if not _CITATION.search(s)]
    has_citations_anywhere = bool(_CITATION.search(answer))
    gap = len(_UNSUPPORTED.findall(answer))
    # URLs the answer cites that are NOT in this attempt's retrieved evidence (e.g. written from model memory).
    evidence_urls = {(e.get("url") or "").rstrip("/") for e in evidence}
    cited_urls = list(dict.fromkeys(u.rstrip(").,;]") for u in re.findall(r"https?://[^\s)\]>]+", answer)))
    unretrieved = [u for u in cited_urls if u.rstrip("/") not in evidence_urls]

    metrics = {
        "words": words, "evidence_count": len(evidence), "relevant_evidence": len(relevant),
        "relevant_domains": len(relevant_domains), "duplicate_ratio": dup_ratio,
        "question_parts": coverage, "missing_anchor_terms": {p: a for p, a in missing_anchors.items() if a},
        "relational_question": relational, "relationship_explained": resolved,
        "factual_sentences": len(factual), "uncited_factual_sentences": len(uncited), "engine_reported_gaps": gap,
        "cited_urls": len(cited_urls), "cited_urls_not_retrieved": unretrieved[:20],
        "thresholds": th,
    }

    problems = []
    if words == 0:
        problems.append("empty_answer")
    if intent == "simple":
        if unanswered and words:
            problems.append("unanswered_parts")
        if gap and not relevant:
            problems.append("engine_reported_gap")
    else:
        if not relevant:
            problems.append("no_usable_evidence")
        elif len(relevant_domains) < th["min_relevant_domains"]:
            problems.append("low_source_coverage")
        if len(keys) >= 4 and dup_ratio > th["max_dup"]:
            problems.append("excessive_duplication")
        if unanswered and words:
            problems.append("unanswered_parts")
        if relational and words and not resolved:
            problems.append("unresolved_relationship")
        if gap:
            problems.append("engine_reported_gap")
        if len(factual) >= 3 and (not has_citations_anywhere or len(uncited) / len(factual) >= 0.75):
            problems.append("uncited_claims")
        if words and words < th["min_words"]:
            problems.append("insufficient_depth")
    problems = [p for p in _PRIORITY if p in problems]
    failure = problems[0] if problems else None
    return Assessment(sufficient=failure is None, failure=failure, diagnosis=problems, metrics=metrics)


# --------------------------------------------------------------------------- #
# Readiness gates (config gate + runtime prerequisites); capacity is checked separately when a slot is taken
# --------------------------------------------------------------------------- #
_PREREQ_CACHE: dict[str, tuple[float, dict]] = {}
_PREREQ_TTL_S = 300


async def _storm_importable(python: str) -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(python, "-c", "import knowledge_storm",
                                                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        return await asyncio.wait_for(proc.wait(), timeout=90) == 0
    except Exception:
        return False


async def check_prerequisites(engine: str) -> dict:
    """Runtime prerequisites for running `engine` at all (cached for a few minutes)."""
    cached = _PREREQ_CACHE.get(engine)
    if cached and time.monotonic() - cached[0] < _PREREQ_TTL_S:
        return cached[1]
    import os
    from app.core.config import resolve_llm_provider, settings

    try:
        llm_key = bool(resolve_llm_provider().api_key)
    except Exception:
        llm_key = False
    checks = {"llm_credentials": llm_key, "tavily_credentials": bool(settings.TAVILY_API_KEY or os.environ.get("TAVILY_API_KEY"))}
    if engine == STORM:
        from app.integrations.research_engine.storm.engine import default_storm_python

        python = default_storm_python()
        checks["storm_environment"] = Path(python).exists()
        checks["knowledge_storm_importable"] = checks["storm_environment"] and await _storm_importable(python)
    elif engine == GPTR:
        checks["gpt_researcher_importable"] = importlib.util.find_spec("gpt_researcher") is not None
    _PREREQ_CACHE[engine] = (time.monotonic(), checks)
    return checks


async def engine_readiness(engine: str) -> dict:
    """
    Whether `engine` may be chosen AUTOMATICALLY right now (explicit overrides skip the config gate, not the prerequisites).
    States: eligible | disabled (config gate off) | unavailable (a runtime prerequisite failed).
    """
    from app.core.config import settings

    if engine == ODR:
        gate = "on"
    else:
        gate = str(getattr(settings, "ROUTER_AUTO_STORM" if engine == STORM else "ROUTER_AUTO_GPT_RESEARCHER", "auto")).lower()
    checks = await check_prerequisites(engine)
    failed = [k for k, ok in checks.items() if not ok]
    if gate == "off":
        state, reason = "disabled", f"automatic routing turned off for {engine} (ROUTER_AUTO_{'STORM' if engine == STORM else 'GPT_RESEARCHER'}=off)"
    elif failed:
        state, reason = "unavailable", f"runtime prerequisites not met: {', '.join(failed)}"
    else:
        state, reason = "eligible", "gate on and runtime prerequisites met"
    return {"engine": engine, "state": state, "eligible": state == "eligible", "gate": gate, "checks": checks, "reason": reason}


class SpecialistSlots:
    """Deployment-wide concurrency limit per specialist (Redis counters; in-process fallback without Redis)."""

    _local: dict[str, int] = {}

    def __init__(self, redis_client: Any = None):
        self.redis = redis_client if (redis_client is not None and hasattr(redis_client, "incr")) else None

    @staticmethod
    def limit(engine: str) -> int:
        from app.core.config import settings
        return int(getattr(settings, "ROUTER_MAX_CONCURRENT_STORM" if engine == STORM else "ROUTER_MAX_CONCURRENT_GPT_RESEARCHER", 1))

    async def acquire(self, engine: str, ttl_s: int) -> bool:
        limit = self.limit(engine)
        if self.redis is not None:
            key = f"research_engine_slots:{engine}"
            try:
                n = await self.redis.incr(key)
                await self.redis.expire(key, max(60, int(ttl_s)))  # a crashed worker cannot hold a slot forever
                if n > limit:
                    await self.redis.decr(key)
                    return False
                return True
            except Exception as exc:
                logger.warning("Slot counter unavailable (%s); using the in-process limit", exc)
        if self._local.get(engine, 0) >= limit:
            return False
        self._local[engine] = self._local.get(engine, 0) + 1
        return True

    async def release(self, engine: str) -> None:
        if self.redis is not None:
            try:
                await self.redis.decr(f"research_engine_slots:{engine}")
                return
            except Exception:
                pass
        self._local[engine] = max(0, self._local.get(engine, 0) - 1)


# --------------------------------------------------------------------------- #
# Persistence of attempts (DB-backed; replaceable in tests)
# --------------------------------------------------------------------------- #
class RouterStore:
    async def list_evidence(self, workspace_id: UUID, run_id: UUID) -> list[dict]:
        from app.core.database import async_session_maker
        from app.repositories.research import ResearchRepository

        async with async_session_maker() as session:
            rows = await ResearchRepository(session).list_evidence_for_run(workspace_id, run_id) or []
        return [evidence_view(r) for r in rows]

    async def start_attempt(self, run_id: UUID, sequence: int, engine: str, profile: Optional[str], trigger: str,
                            reason: str, routing_mode: str = "explicit", preferred_engine: Optional[str] = None) -> UUID:
        from app.core.database import async_session_maker
        from app.models.research import ResearchEngineAttempt, ResearchRun

        async with async_session_maker() as session:
            attempt = ResearchEngineAttempt(run_id=run_id, sequence=sequence, engine=engine, budget_profile=profile,
                                            trigger=trigger, reason=reason, status="running", routing_mode=routing_mode,
                                            preferred_engine=preferred_engine, usage_quality=USAGE_QUALITY.get(engine))
            session.add(attempt)
            await session.flush()
            run = await session.get(ResearchRun, run_id)
            if run is not None:
                run.current_attempt_id = attempt.attempt_id
            await session.commit()
            return attempt.attempt_id

    async def usage_since(self, run_id: UUID, since: datetime) -> dict:
        """Usage the engine persisted during this attempt (ODR writes cumulative checkpoints, so take the max)."""
        from sqlalchemy import func, select

        from app.core.database import async_session_maker
        from app.models.research import ResearchUsage

        async with async_session_maker() as session:
            row = (await session.execute(
                select(func.max(ResearchUsage.input_tokens), func.max(ResearchUsage.output_tokens), func.max(ResearchUsage.cost))
                .where(ResearchUsage.run_id == run_id, ResearchUsage.created_at >= since)
            )).one()
        return {"input_tokens": int(row[0] or 0), "output_tokens": int(row[1] or 0), "cost": float(row[2] or 0.0)}

    async def finish_attempt(self, attempt_id: UUID, **fields: Any) -> None:
        from app.core.database import async_session_maker
        from app.models.research import ResearchEngineAttempt

        async with async_session_maker() as session:
            attempt = await session.get(ResearchEngineAttempt, attempt_id)
            if attempt is None:
                return
            for k, v in fields.items():
                setattr(attempt, k, v)
            if fields.get("status") != "running" and attempt.finished_at is None:
                attempt.finished_at = datetime.now(timezone.utc)
            await session.commit()

    async def record_answer(self, run_id: UUID, engine: str, attempt_id: UUID, set_engine: bool) -> None:
        from app.core.database import async_session_maker
        from app.models.research import ResearchRun

        async with async_session_maker() as session:
            run = await session.get(ResearchRun, run_id)
            if run is None:
                return
            run.current_attempt_id = attempt_id
            if set_engine:
                run.engine = engine
            await session.commit()


def evidence_view(row: Any) -> dict:
    """The evidence fields exposed with a turn response."""
    prov = getattr(row, "provenance", None) or {}
    content = getattr(row, "content", "") or ""
    return {
        "evidence_id": str(row.evidence_id),
        "url": prov.get("url") or getattr(row, "locator", None),
        "title": prov.get("title"),
        "excerpt": content[:400],
        "retriever": getattr(row, "retriever", None),
        "provenance": prov,
    }


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #
@dataclass
class Route:
    engine: str
    profile: Optional[str]
    trigger: str  # explicit | initial | intent | escalation | fallback
    reason: str


@dataclass
class AttemptOutcome:
    route: Route
    sequence: int
    status: str  # answered | failed | timeout
    text: str = ""
    format: str = "conversational"
    details: Optional[str] = None
    evidence: list = field(default_factory=list)
    error: Optional[str] = None
    latency_ms: int = 0
    usage: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    timings: dict = field(default_factory=dict)
    usage_quality: dict = field(default_factory=dict)
    assessment: Optional[Assessment] = None
    attempt_id: Optional[UUID] = None
    exception: Optional[BaseException] = None


@dataclass
class TurnBudget:
    """One budget for the whole turn: it never resets between the ODR attempt and a specialist."""
    deadline_s: float
    token_ceiling: int
    max_attempts: int = 2
    started: float = field(default_factory=time.monotonic)
    used_tokens: int = 0  # MEASURED tokens only
    attempts: int = 0
    unmetered: list = field(default_factory=list)  # attempts whose token usage is unavailable (not counted as zero usage)

    def token_accounting(self) -> str:
        return "complete" if not self.unmetered else "incomplete"

    def remaining_s(self) -> float:
        return self.deadline_s - (time.monotonic() - self.started)

    def remaining_tokens(self) -> int:
        return max(0, self.token_ceiling - self.used_tokens)

    def blocker(self, min_time_s: float) -> Optional[str]:
        if self.attempts >= self.max_attempts:
            return f"max attempts reached ({self.max_attempts})"
        if self.remaining_s() < min_time_s:
            return f"turn deadline nearly reached ({int(self.remaining_s())}s left, need {int(min_time_s)}s)"
        if self.remaining_tokens() <= 0:
            return f"turn token ceiling reached ({self.used_tokens} >= {self.token_ceiling})"
        return None


def _default_factory(engine: str, redis_client: Any, profile: Optional[str], token_ceiling: Optional[int] = None) -> ResearchEngine:
    from app.integrations.research_engine.factory import ResearchEngineFactory

    options: dict = {}
    if profile:
        options["budget_profile"] = profile
    if engine == ODR and token_ceiling is not None:
        options["token_ceiling"] = token_ceiling
    return ResearchEngineFactory.get_engine(engine, redis_client=redis_client, **options)


class EngineRouter(ResearchEngine):
    def __init__(
        self,
        routing_mode: str,
        engine: Optional[str] = None,
        redis_client: Any = None,
        engine_factory: Optional[Callable[..., ResearchEngine]] = None,
        store: Optional[RouterStore] = None,
        readiness: Optional[Callable[[str], Awaitable[dict]]] = None,
        slots: Optional[SpecialistSlots] = None,
        timeouts: Optional[dict[str, float]] = None,
        token_ceiling: Optional[int] = None,
        turn_deadline_s: Optional[float] = None,
        min_specialist_time_s: Optional[float] = None,
        max_specialist_escalations: Optional[int] = None,
        specialist_profiles: Optional[dict[str, str]] = None,
        prerequisites: Optional[Callable[[str], Awaitable[dict]]] = None,
    ):
        from app.core.config import settings

        if routing_mode not in ("auto", "explicit"):
            raise ValueError(f"Unknown routing mode: {routing_mode!r}")
        if routing_mode == "explicit" and engine not in SUPPORTED_ENGINES:
            raise ValueError(f"Explicit routing needs a supported engine, got {engine!r}")
        self.routing_mode = routing_mode
        self.requested_engine = engine
        self.redis_client = redis_client
        self._factory = engine_factory or _default_factory
        self._store = store or RouterStore()
        self._readiness = readiness or engine_readiness
        self._prerequisites = prerequisites or check_prerequisites
        self._slots = slots or SpecialistSlots(redis_client)
        self._timeouts = timeouts or {
            ODR: float(getattr(settings, "ROUTER_TIMEOUT_ODR_S", 600)),
            STORM: float(getattr(settings, "ROUTER_TIMEOUT_STORM_S", 900)),
            GPTR: float(getattr(settings, "ROUTER_TIMEOUT_GPT_RESEARCHER_S", 900)),
        }
        self._token_ceiling = token_ceiling if token_ceiling is not None else int(getattr(settings, "ROUTER_TURN_TOKEN_CEILING", 1_200_000))
        from app.core.config import effective_turn_deadline_s

        self._deadline_s = turn_deadline_s if turn_deadline_s is not None else effective_turn_deadline_s()
        self._min_specialist_s = (min_specialist_time_s if min_specialist_time_s is not None
                                  else float(getattr(settings, "ROUTER_MIN_SPECIALIST_TIME_S", 180)))
        self._max_escalations = (max_specialist_escalations if max_specialist_escalations is not None
                                 else int(getattr(settings, "ROUTER_MAX_SPECIALIST_ESCALATIONS", 1)))
        self._specialist_profiles = specialist_profiles or {
            STORM: str(getattr(settings, "ROUTER_STORM_PROFILE", "bounded")),
            GPTR: str(getattr(settings, "ROUTER_GPT_RESEARCHER_PROFILE", "bounded")),
        }
        self._active: Optional[ResearchEngine] = None
        self.summary: dict = {}

    def _profile_for(self, engine: str, odr_profile: str = "balanced") -> str:
        return odr_profile if engine == ODR else self._specialist_profiles[engine]

    # -- one attempt ---------------------------------------------------------
    async def _attempt(self, route: Route, sequence: int, ctx: dict, budget: TurnBudget,
                       timeout_s: float) -> AsyncGenerator[Any, None]:
        """Run ONE engine to completion or stop it. Yields its progress events, then one AttemptOutcome."""
        from app.integrations.research_engine.budget import ResearchBudgetExceeded

        run_id, workspace_id = ctx["run_id"], ctx["workspace_id"]
        budget.attempts += 1
        before = {e["evidence_id"] for e in await self._store.list_evidence(workspace_id, run_id)}
        started_at = datetime.now(timezone.utc)
        t0 = time.monotonic()
        attempt_id = await self._store.start_attempt(run_id, sequence, route.engine, route.profile, route.trigger, route.reason,
                                                     routing_mode=self.routing_mode, preferred_engine=ctx.get("preferred_engine"))
        outcome = AttemptOutcome(route=route, sequence=sequence, status="failed", attempt_id=attempt_id)
        response: Optional[dict] = None
        status_for_db = "failed"
        timings: dict = {"timeout_s": int(timeout_s)}

        try:
            engine = self._factory(route.engine, self.redis_client, route.profile, budget.remaining_tokens())
        except Exception as exc:
            # Building the adapter is part of the attempt: a missing/broken engine is an attempt failure (so an
            # escalation keeps the initial answer, a direct route falls back) - never an unhandled turn failure.
            outcome.error, outcome.exception = f"engine setup failed: {type(exc).__name__}: {exc}", exc
            outcome.latency_ms = int((time.monotonic() - t0) * 1000)
            outcome.usage_quality = observed_usage_quality(route.engine, {}, {})
            budget.unmetered.append(f"{route.engine}#{sequence}")
            await self._store.finish_attempt(attempt_id, status="failed", error=outcome.error, latency_ms=outcome.latency_ms,
                                             usage_quality=outcome.usage_quality)
            yield outcome
            return
        timings["engine_init_ms"] = int((time.monotonic() - t0) * 1000)
        self._active = engine
        queue: asyncio.Queue = asyncio.Queue()

        async def pump() -> None:
            async for ev in engine.astream_events(run_id=run_id, workspace_id=workspace_id, objective=ctx["objective"],
                                                  **ctx["engine_kwargs"]):
                await queue.put(ev)

        task = asyncio.create_task(pump())
        getter: Optional[asyncio.Future] = None
        try:
            deadline = time.monotonic() + timeout_s
            while True:
                if getter is None:
                    getter = asyncio.ensure_future(queue.get())
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise asyncio.TimeoutError()
                done, _ = await asyncio.wait({getter, task}, timeout=remaining, return_when=asyncio.FIRST_COMPLETED)
                if not done:
                    raise asyncio.TimeoutError()
                events = []
                if getter in done:
                    events.append(getter.result())
                    getter = None
                # Snapshot "finished" BEFORE draining: the engine may finish while we are suspended at a yield below,
                # and anything it queued meanwhile must be read on the next iteration, not dropped.
                finished = task.done()
                if finished:
                    while not queue.empty():
                        events.append(queue.get_nowait())
                for ev in events:
                    st = ev.get("status")
                    if "first_event_ms" not in timings:
                        timings["first_event_ms"] = int((time.monotonic() - t0) * 1000)
                    if st == TURN_RESPONSE:
                        response = ev
                    elif st == "metrics":
                        outcome.metrics = {k: v for k, v in ev.items() if k != "status"}
                    elif st in _TERMINAL:
                        logger.warning("Engine %s yielded terminal status %r; ignored", route.engine, st)
                    else:
                        yield {**ev, "engine": route.engine}
                if finished:  # every event queued before completion was drained above
                    task.result()  # re-raise the engine's failure, if any
                    break
            if response is None:
                outcome.error = "engine_finished_without_response"
            elif not (response.get("text") or "").strip():
                outcome.error = "engine_returned_empty_answer"
            else:
                outcome.status, status_for_db = "answered", "answered"
                outcome.text = response.get("text") or ""
                outcome.format = response.get("format") or "conversational"
                outcome.details = response.get("details")
        except asyncio.TimeoutError:
            outcome.status, status_for_db, outcome.error = "timeout", "timeout", f"exceeded {int(timeout_s)}s"
        except asyncio.CancelledError:
            status_for_db = "cancelled"
            raise
        except ResearchBudgetExceeded as exc:
            status_for_db, outcome.error = "budget_exceeded", str(exc)
            raise
        except Exception as exc:  # engine failure: recorded; the caller decides whether it is fatal
            outcome.error = f"{type(exc).__name__}: {exc}"
            outcome.exception = exc
        finally:
            if getter is not None and not getter.done():
                getter.cancel()
            if not task.done():
                # Stop the underlying work: cancel the consuming task (closes the adapter generator, whose own cleanup
                # terminates subprocesses / cancels upstream tasks) and ask the adapter to cancel.
                task.cancel()
                try:
                    await engine.cancel()
                except Exception:
                    pass
                try:
                    await task
                except BaseException:
                    pass
            self._active = None
            timings["upstream_ms"] = int((time.monotonic() - t0) * 1000)
            t_ev = time.monotonic()
            try:
                outcome.evidence = [e for e in await self._store.list_evidence(workspace_id, run_id) if e["evidence_id"] not in before]
                stored = await self._store.usage_since(run_id, started_at)
                measured = {k: int(outcome.metrics.get(k) or 0) for k in ("input_tokens", "output_tokens")}
                outcome.usage = {
                    "input_tokens": measured["input_tokens"] or stored.get("input_tokens", 0),
                    "output_tokens": measured["output_tokens"] or stored.get("output_tokens", 0),
                    "cost": float(outcome.metrics.get("estimated_cost") or stored.get("cost", 0.0)),
                }
            except Exception as exc:
                logger.warning("Could not collect attempt metrics for run %s: %s", run_id, exc)
            timings["evidence_collection_ms"] = int((time.monotonic() - t_ev) * 1000)
            outcome.latency_ms = int((time.monotonic() - t0) * 1000)
            outcome.timings = timings
            outcome.usage_quality = observed_usage_quality(route.engine, outcome.usage, outcome.metrics)
            if outcome.usage_quality.get("tokens") == "measured":
                budget.used_tokens += int(outcome.usage.get("input_tokens", 0)) + int(outcome.usage.get("output_tokens", 0))
            else:
                # Unknown usage is recorded as unknown - never folded into the measured total as zero.
                budget.unmetered.append(f"{route.engine}#{sequence}")
            finished_rec = asyncio.ensure_future(self._store.finish_attempt(
                attempt_id, status=status_for_db, error=outcome.error, latency_ms=outcome.latency_ms,
                evidence_count=len(outcome.evidence), input_tokens=outcome.usage.get("input_tokens", 0),
                output_tokens=outcome.usage.get("output_tokens", 0), cost=outcome.usage.get("cost", 0.0),
                timings={"router": timings, "engine": outcome.metrics}, usage_quality=outcome.usage_quality,
            ))
            try:
                await asyncio.shield(finished_rec)
            except BaseException as exc:
                logger.warning("Could not record attempt %s: %s", attempt_id, exc)
        yield outcome

    async def _take_slot(self, engine: str, timeout_s: float) -> bool:
        if engine not in SPECIALISTS:
            return True
        return await self._slots.acquire(engine, ttl_s=int(timeout_s) + 120)

    # -- contract ------------------------------------------------------------
    async def astream_events(self, run_id: UUID, workspace_id: UUID, objective: str, research_context: Any = None,
                             **kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
        t_route = time.monotonic()
        budget = TurnBudget(deadline_s=self._deadline_s, token_ceiling=self._token_ceiling,
                            max_attempts=1 + max(0, self._max_escalations))
        ctx = {"run_id": run_id, "workspace_id": workspace_id, "objective": objective,
               "engine_kwargs": {"research_context": research_context, **kwargs}}
        outcomes: list[AttemptOutcome] = []
        readiness_log: list[dict] = []
        escalation: Optional[dict] = None
        intent, rule = None, None

        async def run_route(route: Route, timeout_s: float):
            # A specialist's capacity slot was taken by the caller; it is released here whatever happens.
            outcome = None
            try:
                async for item in self._attempt(route, len(outcomes) + 1, ctx, budget, timeout_s):
                    if isinstance(item, AttemptOutcome):
                        outcome = item
                    else:
                        yield item
            finally:
                if route.engine in SPECIALISTS:
                    await self._slots.release(route.engine)
            outcomes.append(outcome)

        def timeout_for(engine: str) -> float:
            return max(1.0, min(self._timeouts[engine], budget.remaining_s()))

        def fail(outcome: AttemptOutcome):
            return outcome.exception or RuntimeError(f"{outcome.route.engine} {outcome.status}: {outcome.error}")

        async def reject_unsourced_specialist(outcome: AttemptOutcome) -> None:
            """An automatically chosen specialist must return evidence; an answer with none is not used."""
            if outcome.status == "answered" and outcome.route.engine in SPECIALISTS and not outcome.evidence:
                outcome.status, outcome.error = "rejected", "answer without any persisted evidence"
                await self._store.finish_attempt(outcome.attempt_id, status="rejected", error=outcome.error)

        if self.routing_mode == "explicit":
            engine = self.requested_engine
            ctx["preferred_engine"] = engine
            route = Route(engine, self._profile_for(engine), "explicit", "explicit engine override")
            # An explicit specialist must at least be installed; ODR's credentials are checked by ODR itself.
            prereq = await self._prerequisites(engine) if engine in SPECIALISTS else {}
            missing = [k for k, ok in prereq.items() if not ok]
            if missing:
                raise RuntimeError(f"{engine} cannot run: runtime prerequisites not met: {', '.join(missing)}")
            if not await self._take_slot(engine, timeout_for(engine)):
                raise RuntimeError(f"{engine} is at its concurrency limit ({SpecialistSlots.limit(engine)}); try again later")
            routing_ms = int((time.monotonic() - t_route) * 1000)
            yield {"status": "planning", "message": f"Running {engine} (explicit engine override, {route.profile} profile)",
                   "routing": asdict(route)}
            async for ev in run_route(route, timeout_for(engine)):
                yield ev
            final = outcomes[-1]
            if final.status != "answered":
                raise fail(final)
        else:
            intent, rule = classify_intent(objective)
            preferred = PREFERRED_ENGINE[intent]
            ctx["preferred_engine"] = preferred
            first = Route(ODR, ODR_PROFILE_FOR[intent], "initial", f"{intent} request ({rule})")
            if preferred in SPECIALISTS:
                ready = await self._readiness(preferred)
                readiness_log.append({"step": "intent_preference", **ready})
                if ready["eligible"] and await self._take_slot(preferred, timeout_for(preferred)):
                    first = Route(preferred, self._profile_for(preferred), "intent", f"{intent} request ({rule}); {preferred} preferred")
                else:
                    why = ready["reason"] if not ready["eligible"] else f"at concurrency limit ({SpecialistSlots.limit(preferred)})"
                    readiness_log[-1]["used"] = False
                    first = Route(ODR, ODR_PROFILE_FOR[intent], "initial", f"{intent} request ({rule}); {preferred} not used: {why}")
            routing_ms = int((time.monotonic() - t_route) * 1000)
            yield {"status": "planning", "message": f"Routing to {first.engine} ({first.profile} profile): {first.reason}",
                   "routing": asdict(first)}
            async for ev in run_route(first, timeout_for(first.engine)):
                yield ev
            final = outcomes[-1]
            await reject_unsourced_specialist(final)

            if first.engine != ODR:
                if final.status != "answered":
                    blocked = budget.blocker(min_time_s=60)
                    if blocked:
                        raise fail(final)
                    fallback = Route(ODR, ODR_PROFILE_FOR[intent], "fallback", f"{first.engine} {final.status} ({final.error}); falling back to ODR")
                    escalation = {"from": first.engine, "to": ODR, "reason": "specialist_failed", "detail": fallback.reason,
                                  "executed": True}
                    yield {"status": "planning", "message": fallback.reason, "routing": asdict(fallback)}
                    async for ev in run_route(fallback, timeout_for(ODR)):
                        yield ev
                    final = outcomes[-1]
                    if final.status != "answered":
                        raise fail(final)
            else:
                if final.status != "answered":
                    raise fail(final)
                t_assess = time.monotonic()
                final.assessment = assess_answer(final.text, final.evidence, intent, objective)
                final.timings["assessment_ms"] = int((time.monotonic() - t_assess) * 1000)
                decision: dict = {"sufficient": final.assessment.sufficient}
                if not final.assessment.sufficient:
                    failure = final.assessment.failure
                    specialist = SPECIALIST_FOR[failure]
                    escalation = {"from": ODR, "to": specialist, "reason": failure, "diagnosis": final.assessment.diagnosis,
                                  "executed": False}
                    blocked = None
                    if self._max_escalations < 1:
                        blocked = "specialist escalation disabled (ROUTER_MAX_SPECIALIST_ESCALATIONS=0)"
                    else:
                        ready = await self._readiness(specialist)
                        readiness_log.append({"step": "escalation", **ready})
                        if not ready["eligible"]:
                            blocked = ready["reason"]
                        else:
                            blocked = budget.blocker(min_time_s=self._min_specialist_s)
                            if not blocked and not await self._take_slot(specialist, timeout_for(specialist)):
                                blocked = f"{specialist} at concurrency limit ({SpecialistSlots.limit(specialist)})"
                    decision.update({"escalate_to": specialist, "reason": failure, "blocked": blocked})
                    if blocked:
                        escalation["blocked"] = blocked
                        yield {"status": "planning", "message": f"ODR answer: {failure}; escalation to {specialist} blocked: {blocked}"}
                    else:
                        route = Route(specialist, self._profile_for(specialist), "escalation", f"ODR answer insufficient: {failure}")
                        yield {"status": "planning", "message": f"Escalating to {specialist}: {failure}", "routing": asdict(route)}
                        escalation["executed"] = True
                        async for ev in run_route(route, timeout_for(specialist)):
                            yield ev
                        specialist_outcome = outcomes[-1]
                        await reject_unsourced_specialist(specialist_outcome)
                        if specialist_outcome.status == "answered":
                            final = specialist_outcome
                        else:
                            escalation["specialist_failed"] = f"{specialist_outcome.status}: {specialist_outcome.error}"
                            yield {"status": "planning", "message": f"{specialist} {specialist_outcome.status}; keeping the ODR answer"}
                first_assessment = {**asdict(outcomes[0].assessment), "decision": decision}
                await self._store.finish_attempt(outcomes[0].attempt_id, assessment=first_assessment)

        await self._store.record_answer(run_id, final.route.engine, final.attempt_id, set_engine=self.routing_mode == "auto")
        self.summary = {
            "mode": self.routing_mode,
            "intent": intent,
            "intent_rule": rule,
            "preferred_engine": ctx.get("preferred_engine"),
            "answered_by": final.route.engine,
            "answer_budget_profile": final.route.profile,
            "answer_format": final.format,
            "escalated": bool(escalation and escalation.get("executed")),
            "escalation": escalation,
            "attempts": [
                {"sequence": o.sequence, "engine": o.route.engine, "budget_profile": o.route.profile, "trigger": o.route.trigger,
                 "reason": o.route.reason, "status": o.status, "error": o.error, "latency_ms": o.latency_ms,
                 "evidence_count": len(o.evidence), **{k: o.usage.get(k, 0) for k in ("input_tokens", "output_tokens", "cost")},
                 "usage_quality": o.usage_quality or USAGE_QUALITY.get(o.route.engine), "timings": o.timings,
                 "engine_metrics": o.metrics,
                 "assessment": asdict(o.assessment) if o.assessment else None}
                for o in outcomes
            ],
            "readiness": readiness_log,
            "budget_enforced": final.route.engine == ODR,
            "budget_note": BUDGET_ENFORCEMENT[final.route.engine],
            "limits": {"turn_deadline_s": int(self._deadline_s), "turn_token_ceiling": self._token_ceiling,
                       "max_attempts": budget.max_attempts},
            "timings": {"routing_ms": routing_ms, "total_ms": int((time.monotonic() - t_route) * 1000),
                        "turn_tokens_used": budget.used_tokens},
            "budget": {"attempts_used": budget.attempts, "max_attempts": budget.max_attempts,
                       "deadline_s": int(self._deadline_s), "remaining_s": int(max(0, budget.remaining_s())),
                       "measured_tokens": budget.used_tokens, "token_ceiling": self._token_ceiling,
                       "token_accounting": budget.token_accounting(), "unmetered_attempts": list(budget.unmetered)},
        }
        response = turn_response(final.text, format=final.format, evidence_refs=[e["evidence_id"] for e in final.evidence],
                                 details=final.details)
        response["evidence"] = final.evidence
        response["routing"] = self.summary
        yield response

    async def cancel(self) -> None:
        if self._active is not None:
            await self._active.cancel()
