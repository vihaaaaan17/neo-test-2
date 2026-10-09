import asyncio
import json
import logging
import os
import tempfile
from typing import Any, AsyncGenerator, Callable, Optional
from uuid import UUID

from app.integrations.research_engine.engine import ResearchEngine
from app.integrations.research_engine.evidence import record_sources_as_evidence

logger = logging.getLogger(__name__)


class _QueueLogHandler:
    """GPT-Researcher's `log_handler` hook: forwards its own progress callbacks into an asyncio queue."""

    def __init__(self, queue: "asyncio.Queue[dict[str, Any]]"):
        self.queue = queue

    # GPT-Researcher invokes these as `handler.on_x(kwargs.get("x", ""), **kwargs)`, i.e. the name is passed both
    # positionally and as a keyword, so the signatures must tolerate that.
    async def on_tool_start(self, *args, **kwargs):
        tool_name = kwargs.get("tool_name") or (args[0] if args else "")
        self.queue.put_nowait({"status": "executing", "message": f"Running {tool_name}" if tool_name else "Running tool"})

    async def on_agent_action(self, *args, **kwargs):
        action = kwargs.get("action") or (args[0] if args else "")
        status = "planning" if action in ("choose_agent", "agent_selected") else "executing"
        self.queue.put_nowait({"status": status, "message": action or "Agent action"})

    async def on_research_step(self, *args, **kwargs):
        step = kwargs.get("step") or (args[0] if args else "")
        status = "synthesizing" if step in ("writing_report", "writing_conclusion", "conclusion_completed") else "executing"
        self.queue.put_nowait({"status": status, "message": step or "Research step"})


def _default_researcher_factory(**kwargs):
    from gpt_researcher import GPTResearcher  # imported lazily: only needed when this engine runs

    return GPTResearcher(**kwargs)


def build_config(provider_model: str, embedding_model: str) -> dict[str, Any]:
    """
    Models for GPT-Researcher via its supported JSON config mechanism (no environment mutation).
    The API key and base URL come from OPENAI_API_KEY / OPENAI_BASE_URL, which `app.core.config` exports once.
    """
    llm = f"openai:{provider_model}"
    return {
        "RETRIEVER": "tavily",
        "SMART_LLM": llm,
        "FAST_LLM": llm,
        "STRATEGIC_LLM": llm,
        "EMBEDDING": f"openai:{embedding_model}",
    }


def normalize_sources(researcher: Any) -> list[dict[str, Any]]:
    """Merge GPT-Researcher's collected source records with every URL it visited (deduplicated by URL)."""
    by_url: dict[str, dict[str, Any]] = {}
    for item in researcher.get_research_sources() or []:
        url = item.get("url")
        if not url or url in by_url:
            continue
        by_url[url] = {
            "url": url,
            "title": item.get("title"),
            "content": item.get("content") or item.get("raw_content") or "",
        }
    for url in researcher.get_source_urls() or []:
        by_url.setdefault(url, {"url": url, "title": None, "content": ""})
    return list(by_url.values())


class GPTResearcherEngine(ResearchEngine):
    """
    Thin adapter over the real upstream `GPTResearcher` runtime (a full engine, not a tool inside ODR).

    GPT-Researcher performs its own planning, search, crawl and report writing. The adapter only:
      1. passes the Neosis objective and the configured provider models through GPT-Researcher's JSON config;
      2. forwards its `log_handler` callbacks as Neosis progress events;
      3. routes the sources it collected into Neosis evidence persistence and records its estimated cost;
      4. yields exactly one `final_report` event; failures are raised;
      5. relies on task cancellation (the worker cancels the task consuming this generator).
    GPT-Researcher has no input for Neosis research context or prior evidence, so neither is passed.
    """

    def __init__(
        self,
        redis_client: Any = None,
        researcher_factory: Optional[Callable[..., Any]] = None,
        report_type: str = "research_report",
    ):
        self.redis_client = redis_client
        self._researcher_factory = researcher_factory or _default_researcher_factory
        self.report_type = report_type

    async def astream_events(
        self,
        run_id: UUID,
        workspace_id: UUID,
        objective: str,
        research_context: Optional[dict] = None,
        prior_evidence_context: str = "",
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        from app.core.config import resolve_llm_provider

        yield {"status": "starting", "message": "Initializing GPT-Researcher execution...", "run_id": str(run_id)}

        provider = resolve_llm_provider(require_key=True)
        embedding_model = os.environ.get("EMBEDDING_MODEL") or "text-embedding-3-small"

        fd, config_path = tempfile.mkstemp(prefix="neosis_gptr_", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(build_config(provider.model, embedding_model), f)

        queue: "asyncio.Queue[dict[str, Any]]" = asyncio.Queue()
        researcher = self._researcher_factory(
            query=objective,
            report_type=self.report_type,
            report_source="web",
            config_path=config_path,
            log_handler=_QueueLogHandler(queue),
            verbose=False,
        )

        async def run_upstream() -> str:
            await researcher.conduct_research()
            return await researcher.write_report()

        task = asyncio.create_task(run_upstream())
        getter: Optional[asyncio.Future] = None
        try:
            # Wait on "next progress event" and "upstream finished" together. (asyncio.wait_for in a loop can swallow a
            # cancellation on Python 3.11, which would let the research keep running after the worker cancelled us.)
            while True:
                if getter is None:
                    getter = asyncio.ensure_future(queue.get())
                done, _ = await asyncio.wait({getter, task}, return_when=asyncio.FIRST_COMPLETED)
                if getter in done:
                    event = getter.result()
                    getter = None
                    yield event
                    continue
                break  # upstream finished
            while not queue.empty():
                yield queue.get_nowait()

            report = task.result()  # re-raises any upstream failure

            sources = normalize_sources(researcher)
            stored = await record_sources_as_evidence(
                workspace_id=workspace_id,
                run_id=run_id,
                retriever="gpt_researcher",
                provider="gpt_researcher",
                sources=sources,
                query=objective,
            )
            logger.info("GPT-Researcher run %s produced %d sources (%d stored as evidence)", run_id, len(sources), stored)
            await self._record_usage(workspace_id, run_id, researcher)

            yield {"status": "synthesizing", "message": "Finalizing GPT-Researcher report"}
            yield {"status": "final_report", "report": report}
        finally:
            if getter is not None and not getter.done():
                getter.cancel()
            if not task.done():
                task.cancel()
                try:
                    await task
                except BaseException:
                    pass
            try:
                os.remove(config_path)
            except OSError:
                pass

    async def _record_usage(self, workspace_id: UUID, run_id: UUID, researcher: Any) -> None:
        try:
            from app.core.database import async_session_maker
            from app.repositories.research import ResearchRepository

            async with async_session_maker() as session:
                await ResearchRepository(session).create_usage(
                    workspace_id=workspace_id,
                    run_id=run_id,
                    cost=float(researcher.get_costs() or 0.0),
                    estimation_type="gpt_researcher_cost",
                )
        except Exception as exc:
            logger.error("Failed to persist GPT-Researcher usage for run %s: %s", run_id, exc)

    async def cancel(self) -> None:
        """GPT-Researcher has no cancellation API; the worker cancels the task consuming astream_events."""
        return None
