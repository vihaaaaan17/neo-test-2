import asyncio
import collections
import json
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, AsyncGenerator, Optional
from uuid import UUID

from app.integrations.research_engine.engine import ResearchEngine, turn_response
from app.integrations.research_engine.evidence import record_sources_as_evidence

logger = logging.getLogger(__name__)

PROTOCOL_PREFIX = "@@NEOSIS@@"
# The runner sends its result (full article + every source with snippets) as ONE JSON line. asyncio's default 64 KiB
# stream-line limit was exceeded live by a bounded run with ~18 sources ("chunk is longer than limit"), so allow 32 MiB.
STREAM_LINE_LIMIT = 32 * 1024 * 1024
RUNNER_PATH = str(Path(__file__).with_name("runner.py"))
REPO_ROOT = Path(__file__).resolve().parents[4]

# STORM's own defaults (STORMWikiRunnerArguments). Override per instance via `runner_args`.
DEFAULT_RUNNER_ARGS: dict[str, int] = {
    "max_conv_turn": 3,
    "max_perspective": 3,
    "max_search_queries_per_turn": 3,
    "search_top_k": 3,
    "retrieve_top_k": 3,
    "max_thread_num": 3,
}

# Budget profiles expressed only through STORMWikiRunnerArguments (STORM has no token/cost control).
STORM_PROFILES: dict[str, dict[str, int]] = {
    "standard": dict(DEFAULT_RUNNER_ARGS),
    # Fewer perspectives/turns/queries and threads: bounds LM calls, searches and parallelism per run.
    "bounded": {"max_conv_turn": 2, "max_perspective": 2, "max_search_queries_per_turn": 2,
                "search_top_k": 3, "retrieve_top_k": 3, "max_thread_num": 2},
}


def split_storm_article(article: str) -> tuple[str, str]:
    """
    STORM's polish step writes `# summary` + a lead section summarizing the topic, then the article body
    (knowledge_storm ArticlePolishingModule). The lead is STORM's own direct answer; the body stays available as details.
    Returns (lead, body); lead is "" when the article has no summary section.
    """
    text = (article or "").strip()
    lines = text.splitlines()
    if not lines or lines[0].strip().lower() != "# summary":
        return "", text
    lead, rest = [], []
    for i, line in enumerate(lines[1:], start=1):
        if line.startswith("# "):
            rest = lines[i:]
            break
        lead.append(line)
    return "\n".join(lead).strip(), "\n".join(rest).strip()


def default_storm_python() -> str:
    """Interpreter of the isolated STORM environment (`venv-storm`), unless STORM_PYTHON overrides it."""
    from app.core.config import settings

    configured = getattr(settings, "STORM_PYTHON", None)
    if configured:
        return configured
    scripts = "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
    return str(REPO_ROOT / "venv-storm" / scripts)


def strip_unmatched_citations(text: str, sources: list[dict]) -> tuple[str, int]:
    """
    Remove [n] markers that match no source STORM actually returned (its writer can emit markers even when retrieval
    produced nothing). A citation must trace to stored evidence; an untraceable marker is dropped, not kept as decoration.
    """
    import re

    valid = {s.get("index") for s in sources if s.get("index") is not None}
    removed = 0

    def fix(m):
        nonlocal removed
        if int(m.group(1)) in valid:
            return m.group(0)
        removed += 1
        return ""

    return re.sub(r"\[(\d+)\]", fix, text or ""), removed


def format_storm_report(article: str, sources: list[dict], only_cited: bool = False) -> str:
    """STORM cites as [n] using its unified index; append the matching numbered source list."""
    import re

    cited = {int(n) for n in re.findall(r"\[(\d+)\]", article or "")}
    indexed = sorted((s for s in sources if s.get("index") is not None and (not only_cited or s["index"] in cited)),
                     key=lambda s: s["index"])
    if not indexed:
        return article
    lines = [f"[{s['index']}] {s.get('title') or s['url']}: {s['url']}" for s in indexed]
    return article.rstrip() + "\n\n### Sources\n\n" + "\n".join(lines) + "\n"


class StormResearchEngine(ResearchEngine):
    """
    Thin adapter over the real `knowledge_storm` runtime (`STORMWikiRunner`).

    STORM cannot be imported into the Neosis environment (it pins `dspy_ai==2.4.9` -> `openai<2.0.0`), so the adapter
    starts `runner.py` in a separate STORM virtualenv and talks to it over a small stdout line protocol. The adapter only:
      1. maps the Neosis objective and configured provider/credentials into the runner job;
      2. translates STORM's callbacks into Neosis progress events;
      3. routes STORM's sources into Neosis evidence persistence and records its LLM usage;
      4. yields exactly one `turn_response` (article + numbered sources, `format="article"`: STORM has no control
         for a conversational answer, so its article is returned as written); failures are raised;
      5. cancels by terminating the STORM process (the worker cancels the task consuming this generator).
    STORM's planning, perspective generation, multi-pass research, citation gathering and article writing all stay inside STORM.
    """

    def __init__(
        self,
        redis_client: Any = None,
        python_executable: Optional[str] = None,
        runner_args: Optional[dict] = None,
        runner_path: Optional[str] = None,
        budget_profile: str = "standard",
    ):
        if budget_profile not in STORM_PROFILES:
            raise ValueError(f"Unknown STORM budget profile: {budget_profile!r}")
        self.redis_client = redis_client
        self.budget_profile = budget_profile
        self.python_executable = python_executable or default_storm_python()
        self.runner_path = runner_path or RUNNER_PATH
        self.runner_args = {**STORM_PROFILES[budget_profile], **(runner_args or {})}
        self._proc: Optional[asyncio.subprocess.Process] = None

    def _build_job(self, objective: str, output_dir: str) -> dict:
        from app.core.config import resolve_llm_provider, settings

        provider = resolve_llm_provider(require_key=True)
        tavily_key = settings.TAVILY_API_KEY or os.environ.get("TAVILY_API_KEY")
        if not tavily_key:
            raise RuntimeError("TAVILY_API_KEY is required for STORM retrieval.")
        return {
            "topic": objective,
            "output_dir": output_dir,
            "llm": {"model": provider.model, "api_key": provider.api_key, "base_url": provider.base_url},
            "tavily_api_key": tavily_key,
            "args": self.runner_args,
        }

    async def astream_events(
        self,
        run_id: UUID,
        workspace_id: UUID,
        objective: str,
        research_context: Optional[dict] = None,
        prior_evidence_context: str = "",
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        # STORM takes only a topic: it has no input for Neosis research context or prior evidence, so those are not passed.
        yield {"status": "starting", "message": "Initializing STORM execution...", "run_id": str(run_id)}

        if not os.path.exists(self.python_executable):
            raise RuntimeError(
                f"STORM environment not found at {self.python_executable!r}. Create it with "
                "`python -m venv venv-storm` and `venv-storm/Scripts/pip install -r requirements-storm.txt`, "
                "or set STORM_PYTHON."
            )

        output_dir = tempfile.mkdtemp(prefix="neosis_storm_")
        job = self._build_job(objective, output_dir)
        stderr_tail: collections.deque[str] = collections.deque(maxlen=40)

        proc = await asyncio.create_subprocess_exec(
            self.python_executable, "-u", self.runner_path,
            limit=STREAM_LINE_LIMIT,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            # UTF-8 mode: STORM writes its output files with the platform default encoding (cp1252 on Windows) but
            # reads them back as UTF-8, which crashes article generation on any non-ASCII character.
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
        )
        self._proc = proc

        async def drain_stderr() -> None:
            assert proc.stderr is not None
            async for raw in proc.stderr:
                stderr_tail.append(raw.decode("utf-8", errors="replace").rstrip())

        stderr_task = asyncio.create_task(drain_stderr())
        result: Optional[dict] = None
        error_message: Optional[str] = None
        import time as _time
        phase_ms: dict[str, int] = {}
        t_last = _time.monotonic()
        t_start = t_last

        try:
            assert proc.stdin is not None and proc.stdout is not None
            proc.stdin.write((json.dumps(job) + "\n").encode("utf-8"))
            await proc.stdin.drain()
            proc.stdin.close()

            async for raw in proc.stdout:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith(PROTOCOL_PREFIX):
                    continue
                event = json.loads(line[len(PROTOCOL_PREFIX):])
                kind = event.get("type")
                if kind == "phase":
                    now_t = _time.monotonic()
                    phase_ms[event["phase"]] = phase_ms.get(event["phase"], 0) + int((now_t - t_last) * 1000)
                    t_last = now_t
                    yield {"status": event["phase"], "message": event.get("message", "")}
                elif kind == "result":
                    result = event
                elif kind == "error":
                    error_message = event.get("message")

            return_code = await proc.wait()
            await stderr_task

            if result is None or return_code != 0:
                detail = error_message or " | ".join(list(stderr_tail)[-8:]) or "no output"
                raise RuntimeError(f"STORM runner failed (exit code {return_code}): {detail}")

            sources = result.get("sources", [])
            stored = await record_sources_as_evidence(
                workspace_id=workspace_id,
                run_id=run_id,
                retriever="storm",
                provider="storm",
                sources=[
                    {"url": s["url"], "title": s.get("title"), "snippets": s.get("snippets"), "description": s.get("description")}
                    for s in sources
                ],
                query=objective,
            )
            logger.info("STORM run %s produced %d sources (%d stored as evidence)", run_id, len(sources), stored)
            await self._record_usage(workspace_id, run_id, result.get("usage") or {})

            usage = result.get("usage") or {}
            yield {"status": "synthesizing", "message": "Finalizing STORM answer"}
            yield {"status": "metrics", "budget_profile": self.budget_profile, "limits": dict(self.runner_args),
                   "phase_ms": phase_ms, "upstream_ms": int((_time.monotonic() - t_start) * 1000),
                   "model_calls": int(usage.get("model_calls", 0)), "input_tokens": int(usage.get("input_tokens", 0)),
                   "output_tokens": int(usage.get("output_tokens", 0))}
            article, removed = strip_unmatched_citations(result["article"], sources)
            if removed:
                logger.warning("STORM run %s: removed %d citation marker(s) with no returned source", run_id, removed)
                article = article.rstrip() + ("\n\n*STORM returned no retrievable sources for some citations; those markers "
                                              "were removed.*")
            lead, _ = split_storm_article(article)
            full = format_storm_report(article, sources)
            if lead:
                # STORM's own lead section is the direct answer; the full article is kept as details.
                yield turn_response(format_storm_report(lead, sources, only_cited=True), format="conversational", details=full)
            else:
                yield turn_response(full, format="article")
        finally:
            await self._terminate(proc)
            stderr_task.cancel()
            self._proc = None
            shutil.rmtree(output_dir, ignore_errors=True)

    async def _record_usage(self, workspace_id: UUID, run_id: UUID, usage: dict) -> None:
        try:
            from app.core.database import async_session_maker
            from app.repositories.research import ResearchRepository

            async with async_session_maker() as session:
                await ResearchRepository(session).create_usage(
                    workspace_id=workspace_id,
                    run_id=run_id,
                    model_calls=int(usage.get("model_calls", 0)),
                    input_tokens=int(usage.get("input_tokens", 0)),
                    output_tokens=int(usage.get("output_tokens", 0)),
                    estimation_type="storm_lm_history",
                )
        except Exception as exc:
            logger.error("Failed to persist STORM usage for run %s: %s", run_id, exc)

    @staticmethod
    async def _terminate(proc: asyncio.subprocess.Process) -> None:
        if proc.returncode is not None:
            return
        try:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
        except ProcessLookupError:
            pass

    async def cancel(self) -> None:
        """Terminate the STORM process if one is running (the worker also cancels the consuming task)."""
        if self._proc is not None:
            await self._terminate(self._proc)
