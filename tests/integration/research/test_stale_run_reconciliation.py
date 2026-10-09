"""A research run left pending/running long past any possible execution (dead worker) is finalized once; fresh runs are not."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

from app.models.conversation import ChatEvent, Conversation, ConversationTurn
from app.models.research import ResearchRun
from app.models.workspace import Workspace
from app.workers.tasks import reconcile_stale_research_runs_job

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_stale_runs_are_finalized_and_their_turns_closed(db_session):
    ws, owner = uuid.uuid4(), uuid.uuid4()
    db_session.add(Workspace(workspace_id=ws, owner_id=owner))
    await db_session.flush()
    conv = Conversation(workspace_id=ws, owner_id=owner)
    db_session.add(conv)
    await db_session.flush()
    turn = ConversationTurn(conversation_id=conv.conversation_id, workspace_id=ws, owner_id=owner, sequence=1, mode="research",
                            user_message="x", status="running")
    db_session.add(turn)
    await db_session.flush()
    stale = ResearchRun(workspace_id=ws, owner_id=owner, objective="x", engine=None, routing_mode="auto", status="pending",
                        conversation_id=conv.conversation_id, turn_id=turn.turn_id)
    fresh = ResearchRun(workspace_id=ws, owner_id=owner, objective="y", engine="open_deep_research", status="pending")
    db_session.add_all([stale, fresh])
    await db_session.commit()
    await db_session.execute(update(ResearchRun).where(ResearchRun.run_id == stale.run_id)
                             .values(updated_at=datetime.now(timezone.utc) - timedelta(hours=5)))
    await db_session.commit()
    stale_id, fresh_id, turn_id = stale.run_id, fresh.run_id, turn.turn_id

    result = await reconcile_stale_research_runs_job({"redis": None})
    assert result["reconciled"] >= 1

    db_session.expire_all()
    statuses = dict((await db_session.execute(select(ResearchRun.run_id, ResearchRun.status)
                                              .where(ResearchRun.run_id.in_([stale_id, fresh_id])))).all())
    assert statuses == {stale_id: "failed", fresh_id: "pending"}
    t = (await db_session.execute(select(ConversationTurn).where(ConversationTurn.turn_id == turn_id))).scalar_one()
    assert t.status == "failed" and t.error_code == "stale_run_reconciled"
    events = [e.event_type for e in (await db_session.execute(select(ChatEvent).where(ChatEvent.turn_id == turn_id))).scalars().all()]
    assert events.count("done") == 1 and events.count("turn.failed") == 1  # exactly one terminal outcome

    # Idempotent: a second sweep does nothing more to this run.
    await reconcile_stale_research_runs_job({"redis": None})
    events2 = [e.event_type for e in (await db_session.execute(select(ChatEvent).where(ChatEvent.turn_id == turn_id))).scalars().all()]
    assert events2 == events
