from typing import AsyncGenerator, Any, Optional, TypedDict
import abc
from uuid import UUID

# Concrete engines Neosis can run. The single allow-list used by admission, the factory and the router.
SUPPORTED_ENGINES = ("open_deep_research", "storm", "gpt_researcher")

# How a run picks its engine. Kept separate from engine identity: "auto" is never an engine name.
ROUTING_MODES = ("auto", "explicit")

# The one event through which an engine hands its answer for a turn to the worker.
TURN_RESPONSE = "turn_response"

# Passed through an upstream engine's own input/prompt controls so that ordinary turns read like a study partner's
# answer rather than a formal paper. Upstream prompts and algorithms are not modified.
CONVERSATIONAL_STYLE = (
    "Response style: answer the question directly and conversationally, the way a knowledgeable study partner would. "
    "Use whatever form fits the question (paragraphs, a short list, a table, code or mathematics). Do not write an "
    "abstract, methodology, formal report sections or a long bibliography unless the user explicitly asks for a report. "
    "Cite sources inline (for example [Title](URL)) for factual claims."
)


class TurnResponse(TypedDict, total=False):
    status: str
    text: str  # the direct answer shown in chat
    format: str  # "conversational", or "article" when an engine produced no shorter direct answer
    evidence_refs: list[str]
    details: str  # optional longer upstream output (e.g. STORM's full article) kept alongside the answer


def turn_response(text: str, format: str = "conversational", evidence_refs: Optional[list[str]] = None,
                  details: Optional[str] = None) -> TurnResponse:
    response: TurnResponse = {"status": TURN_RESPONSE, "text": text or "", "format": format,
                              "evidence_refs": list(evidence_refs or [])}
    if details:
        response["details"] = details
    return response


class ResearchEngine(abc.ABC):
    """
    Abstract interface for all research engines in Neosis.

    Contract: yield progress events (`starting`, `planning`, `executing`, `synthesizing`, ...) and exactly one
    `turn_response` event; never yield a terminal status; signal failure by raising.
    """

    @abc.abstractmethod
    async def astream_events(
        self,
        run_id: UUID,
        workspace_id: UUID,
        objective: str,
        research_context: Any = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream progress events, then exactly one `turn_response`."""
        pass

    @abc.abstractmethod
    async def cancel(self) -> None:
        """
        Trigger cooperative cancellation of the running execution.
        """
        pass
