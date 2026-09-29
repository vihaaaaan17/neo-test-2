import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.workspace import Workspace
from app.models.conversation import Conversation, ConversationTurn
from app.models.knowledge import KnowledgeMemory
from app.models.research import ResearchEvidence, ResearchRun
from app.models.scratchpad import ScratchpadEntry
from app.models.open_notebook_binding import OpenNotebookWorkspaceBinding, OpenNotebookConversationBinding
from app.services.chat.context import build_ground_context, GroundContext
from app.services.chat.service import ChatService
from app.schemas.chat import TurnCreate

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

DISTINCTIVE_RESEARCH_FACT = "RESEARCH_FACT_UNVERIFIED_ROOM_TEMP_SUPERCONDUCTOR_DISCOVERY_XYZ99"
DISTINCTIVE_GRAPH_FACT = "GRAPH_FACT_PROJECTION_CLUSTER_ALPHA_7749"
DISTINCTIVE_SCRATCHPAD_NOTE = "SCRATCHPAD_HYPOTHESIS_SECRET_CATALYST_42"


@pytest_asyncio.fixture
async def db_session():
    async with async_session_maker() as session:
        yield session


async def test_integration_critical_ground_isolation(db_session: AsyncSession):
    """
    Integration verification of the invariant:
    'Ground is source-grounded. Research is state-aware. Research-derived knowledge must never become Ground evidence.'
    """
    user_id = uuid.uuid4()
    ws = Workspace(workspace_id=uuid.uuid4(), owner_id=user_id, research_engine="open_deep_research")
    db_session.add(ws)

    ws_binding = OpenNotebookWorkspaceBinding(
        workspace_id=ws.workspace_id,
        open_notebook_notebook_id=f"notebook:{uuid.uuid4()}",
        status="ACTIVE"
    )
    db_session.add(ws_binding)

    conv = Conversation(
        conversation_id=uuid.uuid4(),
        workspace_id=ws.workspace_id,
        owner_id=user_id,
        status="active"
    )
    db_session.add(conv)

    conv_binding = OpenNotebookConversationBinding(
        conversation_id=conv.conversation_id,
        open_notebook_session_id=f"session:{uuid.uuid4()}"
    )
    db_session.add(conv_binding)

    # Add ground turn
    turn1 = ConversationTurn(
        turn_id=uuid.uuid4(),
        conversation_id=conv.conversation_id,
        workspace_id=ws.workspace_id,
        owner_id=user_id,
        sequence=1,
        mode="ground",
        user_message="What is the boiling point of pure water?",
        assistant_message="100 degrees Celsius at 1 atm.",
        status="completed"
    )
    # Add research turn with distinctive fact
    turn2 = ConversationTurn(
        turn_id=uuid.uuid4(),
        conversation_id=conv.conversation_id,
        workspace_id=ws.workspace_id,
        owner_id=user_id,
        sequence=2,
        mode="research",
        user_message="Speculate on unverified superconductors.",
        assistant_message=f"Possible discovery: {DISTINCTIVE_RESEARCH_FACT}. Also see {DISTINCTIVE_GRAPH_FACT}.",
        status="completed"
    )
    db_session.add_all([turn1, turn2])

    # Add scratchpad note
    sp = ScratchpadEntry(
        entry_id=uuid.uuid4(),
        workspace_id=ws.workspace_id,
        conversation_id=conv.conversation_id,
        entry_type="hypothesis",
        lifecycle="active",
        content=DISTINCTIVE_SCRATCHPAD_NOTE
    )
    db_session.add(sp)
    await db_session.commit()

    ctx = await build_ground_context(
        session=db_session,
        workspace_id=ws.workspace_id,
        conversation_id=conv.conversation_id,
        query="What is the freezing point of water?"
    )

    ctx_json = ctx.model_dump_json()
    assert DISTINCTIVE_RESEARCH_FACT not in ctx_json
    assert DISTINCTIVE_GRAPH_FACT not in ctx_json
    assert DISTINCTIVE_SCRATCHPAD_NOTE not in ctx_json
    assert "What is the boiling point of pure water?" in ctx_json
