"""
Deterministic offline harness for the Open Deep Research adapter.

It runs the REAL vendored ODR graph (supervisor -> researcher -> compress -> final report) through
`OpenDeepResearchEngine`, but replaces the two external dependencies with test doubles:

  * ODR's module-level `configurable_model` (the only LLM entry point of the graph) -> `FakeODRModel`;
  * the Tavily client used inside the real `neosis_web_search` bridge -> `FakeTavilyClient`, and the
    bridge's evidence repository -> a recorder, so evidence persistence is observable without a database.

Nothing here touches production code: everything is applied with `unittest.mock.patch` for the duration
of `offline_odr()`. No network, no LLM key, no Postgres.
"""
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import Any, List
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, SystemMessage


def _tool_name(tool: Any) -> str:
    return getattr(tool, "name", None) or getattr(tool, "__name__", None) or str(tool)


@dataclass
class OfflineRecorder:
    """What the offline run did, for assertions."""
    topic: str = ""
    supervisor_calls: int = 0
    researcher_calls: int = 0
    search_queries: List[str] = field(default_factory=list)
    evidence: List[dict] = field(default_factory=list)


class FakeODRModel:
    """
    Stand-in for ODR's `configurable_model` (init_chat_model). Supports the call chain the graph uses:
    `.with_structured_output(...)`, `.bind_tools(...)`, `.with_retry(...)`, `.with_config(...)`, `.ainvoke(...)`.
    Behaviour is decided by role: structured output (research brief), supervisor (tools include ConductResearch),
    researcher (tools include neosis_web_search), or plain calls (compression / final report).
    """

    def __init__(self, recorder: OfflineRecorder, schema: Any = None, tool_names: tuple = ()):
        self.recorder = recorder
        self.schema = schema
        self.tool_names = tool_names

    def with_structured_output(self, schema, **_):
        return FakeODRModel(self.recorder, schema=schema)

    def bind_tools(self, tools, **_):
        return FakeODRModel(self.recorder, tool_names=tuple(_tool_name(t) for t in tools))

    def with_retry(self, *_, **__):
        return self

    def with_config(self, *_, **__):
        return self

    async def ainvoke(self, messages, *_, **__):
        r = self.recorder
        if self.schema is not None:
            name = self.schema.__name__
            if name == "ResearchQuestion":
                return self.schema(research_brief=f"Offline research brief: {r.topic}")
            if name == "ClarifyWithUser":
                return self.schema(need_clarification=False, question="", verification="Starting research.")
            raise AssertionError(f"Unexpected structured output schema in offline harness: {name}")

        if "ConductResearch" in self.tool_names:  # supervisor
            r.supervisor_calls += 1
            if r.supervisor_calls == 1:
                return AIMessage(content="", tool_calls=[
                    {"name": "ConductResearch", "args": {"research_topic": r.topic}, "id": "call_conduct_1"}
                ])
            return AIMessage(content="", tool_calls=[
                {"name": "ResearchComplete", "args": {}, "id": f"call_complete_{r.supervisor_calls}"}
            ])

        if "neosis_web_search" in self.tool_names:  # researcher
            r.researcher_calls += 1
            if r.researcher_calls == 1:
                return AIMessage(content="", tool_calls=[
                    {"name": "neosis_web_search", "args": {"queries": [r.topic]}, "id": "call_search_1"}
                ])
            return AIMessage(content="I have enough information.")

        if messages and isinstance(messages[0], SystemMessage):  # compress_research
            return AIMessage(content=f"Compressed findings for: {r.topic} [1] https://offline.example/1")
        # final_report_generation
        return AIMessage(content=f"# Offline report\n\n{r.topic}\n\n### Sources\n[1] Offline source: https://offline.example/1")


class FakeTavilyClient:
    def __init__(self, recorder: OfflineRecorder, *_, **__):
        self.recorder = recorder

    async def search(self, query, **_):
        self.recorder.search_queries.append(query)
        return {"results": [
            {"url": "https://offline.example/1", "title": "Offline source", "content": f"About {query}",
             "raw_content": f"Raw content about {query}", "score": 0.9},
        ]}


class _EvidenceRecorderRepo:
    def __init__(self, recorder: OfflineRecorder):
        self.recorder = recorder

    async def _verify_run_workspace(self, run_id, workspace_id):
        return None

    async def create_evidence(self, **kwargs):
        self.recorder.evidence.append(kwargs)


@asynccontextmanager
async def _null_session():
    yield MagicMock()


@contextmanager
def offline_odr(topic: str, monkeypatch=None):
    """Patch ODR's external dependencies for one offline run and yield the recorder."""
    import os

    from app.integrations.research_engine.tools import neosis_search_tools as tools_mod
    from app.integrations.research_engine.upstream.open_deep_research import deep_researcher as dr_mod

    recorder = OfflineRecorder(topic=topic)
    usage_repo = AsyncMock()
    previous_key = os.environ.get("TAVILY_API_KEY")
    os.environ["TAVILY_API_KEY"] = previous_key or "offline-test-key"
    try:
        with patch.object(dr_mod, "configurable_model", FakeODRModel(recorder)), \
             patch.object(tools_mod, "AsyncTavilyClient", lambda *a, **k: FakeTavilyClient(recorder)), \
             patch.object(tools_mod, "async_session_maker", _null_session), \
             patch.object(tools_mod, "ResearchRepository", lambda *_: _EvidenceRecorderRepo(recorder)), \
             patch("app.core.database.async_session_maker", _null_session), \
             patch("app.repositories.research.ResearchRepository", lambda *_: usage_repo):
            yield recorder
    finally:
        if previous_key is None:
            os.environ.pop("TAVILY_API_KEY", None)
        else:
            os.environ["TAVILY_API_KEY"] = previous_key
