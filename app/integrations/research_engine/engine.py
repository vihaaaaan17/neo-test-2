from typing import AsyncGenerator, Any
import abc
from uuid import UUID

class ResearchEngine(abc.ABC):
    """
    Abstract interface for all research engines in Neosis.
    """

    @abc.abstractmethod
    async def astream_events(self, run_id: UUID, workspace_id: UUID, objective: str) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream execution events from the research engine.
        
        Args:
            run_id: The canonical ResearchRun ID.
            workspace_id: The Workspace ID.
            objective: The research objective.
            
        Yields:
            A dictionary containing event data (e.g., status, message, payload).
            In later phases, these are mapped to canonical ResearchEvent schemas.
        """
        pass

    @abc.abstractmethod
    async def cancel(self) -> None:
        """
        Trigger cooperative cancellation of the running execution.
        """
        pass
