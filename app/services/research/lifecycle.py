import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.research import ResearchRun, ResearchTask, ResearchEvent
from app.repositories.research import ResearchRepository

class InvalidTransitionError(Exception):
    pass

class ResearchLifecycleService:
    """
    Acts as the sole authority for state transitions of ResearchRun and ResearchTask.
    Ensures invalid transitions are rejected and automatically records ResearchEvent rows.
    """

    RUN_TRANSITIONS = {
        "pending": ["planning", "failed", "cancelled"],
        "planning": ["researching", "failed", "cancelled", "partial"],
        "researching": ["synthesizing", "failed", "cancelled", "partial"],
        "synthesizing": ["finalizing", "failed", "cancelled", "partial"],
        "finalizing": ["completed", "partial", "failed", "cancelled"],
    }

    TASK_TRANSITIONS = {
        "pending": ["running", "cancelled", "skipped", "failed"],
        "running": ["completed", "partial", "failed", "cancelled", "skipped"],
    }

    TERMINAL_STATES = {"completed", "partial", "failed", "cancelled", "skipped"}

    def __init__(self, repository: ResearchRepository):
        self.repository = repository
        
    async def transition_run(
        self, 
        workspace_id: uuid.UUID, 
        run_id: uuid.UUID, 
        new_status: str, 
        payload: Optional[Dict[str, Any]] = None
    ) -> ResearchRun:
        """
        Transition a ResearchRun to a new status.
        Emits a ResearchEvent.
        """
        run = await self.repository.get_run(workspace_id, run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found in workspace {workspace_id}")
            
        current_status = run.status.lower()
        new_status = new_status.lower()
        
        # If already in the target state, just return or emit event? 
        # Typically we reject or no-op. Let's no-op but no event.
        if current_status == new_status:
            return run
            
        if current_status in self.TERMINAL_STATES:
            raise InvalidTransitionError(f"Run {run_id} is in terminal state '{current_status}'. Cannot transition to '{new_status}'.")
            
        allowed = self.RUN_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise InvalidTransitionError(f"Invalid transition for Run {run_id}: '{current_status}' -> '{new_status}'")
            
        # Perform transition
        run.status = new_status
        await self.repository.session.commit()
        await self.repository.session.refresh(run)
        
        # Emit event
        event_payload = {"from": current_status, "to": new_status}
        if payload:
            event_payload.update(payload)
            
        await self.repository.create_event(
            workspace_id=workspace_id,
            run_id=run_id,
            event_type="run.status_changed",
            payload=event_payload
        )
        
        return run

    async def transition_task(
        self, 
        workspace_id: uuid.UUID, 
        run_id: uuid.UUID, 
        task_id: uuid.UUID, 
        new_status: str, 
        payload: Optional[Dict[str, Any]] = None
    ) -> ResearchTask:
        """
        Transition a ResearchTask to a new status.
        Emits a ResearchEvent.
        """
        task = await self.repository.get_task(workspace_id, run_id, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found in run {run_id} (workspace {workspace_id})")
            
        current_status = task.status.lower()
        new_status = new_status.lower()
        
        if current_status == new_status:
            return task
            
        if current_status in self.TERMINAL_STATES:
            raise InvalidTransitionError(f"Task {task_id} is in terminal state '{current_status}'. Cannot transition to '{new_status}'.")
            
        allowed = self.TASK_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise InvalidTransitionError(f"Invalid transition for Task {task_id}: '{current_status}' -> '{new_status}'")
            
        # Perform transition
        task.status = new_status
        await self.repository.session.commit()
        await self.repository.session.refresh(task)
        
        # Emit event
        event_payload = {"from": current_status, "to": new_status}
        if payload:
            event_payload.update(payload)
            
        await self.repository.create_event(
            workspace_id=workspace_id,
            run_id=run_id,
            task_id=task_id,
            event_type="task.status_changed",
            payload=event_payload
        )
        
        return task
