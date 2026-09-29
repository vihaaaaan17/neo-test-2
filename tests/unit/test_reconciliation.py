"""
tests/unit/test_reconciliation.py

Unit tests for Chapter 4 Historical State Reconciliation Engine:
- In-place legacy Ground KnowledgeMemory quarantine without deleting data.
- Reconciliation of legacy GroundConversation and OpenNotebookConversationBinding to canonical Conversation.
- Linking historical unlinked ResearchRun records to conversation turns.
- Strict idempotency (second run produces zero mutations).
- Dry-run mode non-commit safety and workspace scoping.
"""

from datetime import datetime, timezone
from uuid import uuid4
import pytest

from app.models.conversation import GroundConversation, Conversation, ConversationTurn
from app.models.open_notebook_binding import OpenNotebookConversationBinding
from app.models.knowledge import KnowledgeMemory
from app.models.research import ResearchRun
from scripts.reconcile_chapter4_state import StateReconciliationEngine


class MockScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items

    def first(self):
        return self._items[0] if self._items else None


class MockResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return MockScalars(self._items)


class FakeReconciliationSession:
    """
    In-memory async session tracking entities, mutations, and transactional commits/rollbacks.
    """

    def __init__(
        self,
        ground_conversations=None,
        conversations=None,
        bindings=None,
        memories=None,
        runs=None,
        turns=None,
        fail_on_execute=False,
    ):
        self.ground_conversations = list(ground_conversations or [])
        self.conversations = list(conversations or [])
        self.bindings = list(bindings or [])
        self.memories = list(memories or [])
        self.runs = list(runs or [])
        self.turns = list(turns or [])

        self.added = []
        self.deleted = []
        self.committed = False
        self.rolled_back = False
        self.fail_on_execute = fail_on_execute

    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, Conversation):
            self.conversations.append(obj)
        elif isinstance(obj, KnowledgeMemory):
            self.memories.append(obj)
        elif isinstance(obj, ResearchRun):
            self.runs.append(obj)

    def delete(self, obj):
        self.deleted.append(obj)

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def execute(self, stmt):
        if self.fail_on_execute:
            raise RuntimeError("Simulated database failure during query execution")

        entity_cls = stmt.column_descriptions[0]["type"]
        params = stmt.compile().params

        if entity_cls == GroundConversation:
            ws_id = next((v for k, v in params.items() if "workspace_id" in k), None)
            res = [gc for gc in self.ground_conversations if gc.workspace_id == ws_id] if ws_id else self.ground_conversations
            return MockResult(res)

        elif entity_cls == Conversation:
            cid = next((v for k, v in params.items() if "conversation_id" in k), None)
            res = [c for c in self.conversations if c.conversation_id == cid] if cid else self.conversations
            return MockResult(res)

        elif entity_cls == OpenNotebookConversationBinding:
            return MockResult(self.bindings)

        elif entity_cls == KnowledgeMemory:
            ws_id = next((v for k, v in params.items() if "workspace_id" in k), None)
            res = [m for m in self.memories if m.workspace_id == ws_id] if ws_id else self.memories
            return MockResult(res)

        elif entity_cls == ResearchRun:
            ws_id = next((v for k, v in params.items() if "workspace_id" in k), None)
            res = [r for r in self.runs if (r.conversation_id is None or r.turn_id is None)]
            if ws_id:
                res = [r for r in res if r.workspace_id == ws_id]
            return MockResult(res)

        elif entity_cls == ConversationTurn:
            run_id = next((v for k, v in params.items() if "research_run_id" in k), None)
            res = [t for t in self.turns if t.research_run_id == run_id] if run_id else self.turns
            return MockResult(res)

        return MockResult([])


@pytest.mark.asyncio
async def test_legacy_ground_memory_quarantine_in_place():
    """
    Quarantines legacy Ground KnowledgeMemory records in place with metadata
    without deleting data.
    """
    workspace_id = uuid4()
    owner_id = uuid4()
    mem_id = uuid4()

    legacy_memory = KnowledgeMemory(
        knowledge_id=mem_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        knowledge_type="ground_mode",
        content="Legacy ground observation text",
        status="active",
        provenance={"origin": "ground_mode", "sources": ["s1"]},
        confidence=0.85,
        tags=["physics", "quantum"]
    )

    session = FakeReconciliationSession(memories=[legacy_memory])
    engine = StateReconciliationEngine(session)

    result = await engine.reconcile(apply=True)

    assert result["mode"] == "apply"
    assert result["counts"]["legacy_ground_memories_quarantined"] == 1
    assert result["counts"]["errors"] == 0

    # Verify in-place mutation without deletion
    assert len(session.deleted) == 0  # CRITICAL: zero deletes
    assert session.committed is True

    # Check updated metadata on the original record
    assert legacy_memory.status == "quarantined"
    assert legacy_memory.provenance["legacy_origin"] == "ground_mode_pre_ch4"
    assert legacy_memory.provenance["quarantined_from_ground"] is True
    assert "reconciled_at" in legacy_memory.provenance
    assert legacy_memory.knowledge_id == mem_id
    assert legacy_memory.content == "Legacy ground observation text"
    assert legacy_memory.confidence == 0.85


@pytest.mark.asyncio
async def test_reconcile_ground_conversations_and_bindings():
    """
    Reconciles orphaned GroundConversation and OpenNotebookConversationBinding
    records by creating canonical Conversation records with preserved UUIDs.
    """
    workspace_id = uuid4()
    owner_id = uuid4()
    conv_id = uuid4()

    gc = GroundConversation(
        conversation_id=conv_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    binding = OpenNotebookConversationBinding(
        conversation_id=conv_id,
        open_notebook_session_id="on-session-987"
    )

    session = FakeReconciliationSession(
        ground_conversations=[gc],
        bindings=[binding]
    )
    engine = StateReconciliationEngine(session)

    result = await engine.reconcile(apply=True)

    assert result["counts"]["canonical_conversations_created"] == 1
    assert result["counts"]["open_notebook_bindings_reconciled"] == 1
    assert session.committed is True

    # Verify newly created canonical conversation
    created_conv = session.conversations[0]
    assert created_conv.conversation_id == conv_id
    assert created_conv.workspace_id == workspace_id
    assert created_conv.owner_id == owner_id
    assert created_conv.metadata_["legacy_origin"] == "ground_conversation"
    assert "reconciled_at" in created_conv.metadata_


@pytest.mark.asyncio
async def test_reconcile_unlinked_research_runs():
    """
    Links unlinked historical ResearchRun records to conversation turns when references exist.
    """
    workspace_id = uuid4()
    run_id = uuid4()
    conv_id = uuid4()
    turn_id = uuid4()

    unlinked_run = ResearchRun(
        run_id=run_id,
        workspace_id=workspace_id,
        owner_id=uuid4(),
        objective="Analyze topological insulators",
        engine="open_deep_research",
        status="completed",
        conversation_id=None,
        turn_id=None
    )

    turn = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conv_id,
        workspace_id=workspace_id,
        owner_id=uuid4(),
        sequence=1,
        mode="research",
        user_message="Run research on topological insulators",
        status="completed",
        research_run_id=run_id
    )

    session = FakeReconciliationSession(
        runs=[unlinked_run],
        turns=[turn]
    )
    engine = StateReconciliationEngine(session)

    result = await engine.reconcile(apply=True)

    assert result["counts"]["research_runs_linked"] == 1
    assert unlinked_run.turn_id == turn_id
    assert unlinked_run.conversation_id == conv_id


@pytest.mark.asyncio
async def test_reconciliation_is_strictly_idempotent():
    """
    Running the reconciliation engine twice produces 0 additional mutations on the second run.
    """
    workspace_id = uuid4()
    conv_id = uuid4()
    run_id = uuid4()

    gc = GroundConversation(
        conversation_id=conv_id,
        workspace_id=workspace_id,
        owner_id=uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    km = KnowledgeMemory(
        knowledge_id=uuid4(),
        workspace_id=workspace_id,
        owner_id=uuid4(),
        knowledge_type="ground_mode",
        content="Ground observation",
        status="active",
        provenance={"origin": "ground_mode"}
    )

    run = ResearchRun(
        run_id=run_id,
        workspace_id=workspace_id,
        owner_id=uuid4(),
        objective="Study phonons",
        engine="open_deep_research",
        status="completed",
        conversation_id=None,
        turn_id=None
    )

    turn = ConversationTurn(
        turn_id=uuid4(),
        conversation_id=conv_id,
        workspace_id=workspace_id,
        owner_id=uuid4(),
        sequence=1,
        mode="research",
        user_message="Study phonons",
        status="completed",
        research_run_id=run_id
    )

    session = FakeReconciliationSession(
        ground_conversations=[gc],
        memories=[km],
        runs=[run],
        turns=[turn]
    )
    engine = StateReconciliationEngine(session)

    # First run: mutates state
    res1 = await engine.reconcile(apply=True)
    assert res1["counts"]["canonical_conversations_created"] == 1
    assert res1["counts"]["legacy_ground_memories_quarantined"] == 1
    assert res1["counts"]["research_runs_linked"] == 1

    # Second run: strictly 0 new mutations
    res2 = await engine.reconcile(apply=True)
    assert res2["counts"]["canonical_conversations_created"] == 0
    assert res2["counts"]["open_notebook_bindings_reconciled"] == 0
    assert res2["counts"]["legacy_ground_memories_quarantined"] == 0
    assert res2["counts"]["research_runs_linked"] == 0
    assert res2["counts"]["skipped"] >= 2
    assert res2["counts"]["errors"] == 0
    assert len(session.deleted) == 0


@pytest.mark.asyncio
async def test_dry_run_mode_does_not_commit():
    """
    Dry-run mode plans mutations, logs actions, rolls back the transaction, and returns dry-run status.
    """
    session = FakeReconciliationSession(
        ground_conversations=[
            GroundConversation(
                conversation_id=uuid4(),
                workspace_id=uuid4(),
                owner_id=uuid4(),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        ]
    )
    engine = StateReconciliationEngine(session)

    result = await engine.reconcile(apply=False)

    assert result["mode"] == "dry-run"
    assert result["counts"]["canonical_conversations_created"] == 1
    assert session.committed is False
    assert session.rolled_back is True


@pytest.mark.asyncio
async def test_workspace_filtering_scope():
    """
    Reconciliation properly filters records by workspace_id and ignores other workspaces.
    """
    ws_target = uuid4()
    ws_other = uuid4()

    gc_target = GroundConversation(
        conversation_id=uuid4(),
        workspace_id=ws_target,
        owner_id=uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    gc_other = GroundConversation(
        conversation_id=uuid4(),
        workspace_id=ws_other,
        owner_id=uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    session = FakeReconciliationSession(ground_conversations=[gc_target, gc_other])
    engine = StateReconciliationEngine(session)

    result = await engine.reconcile(workspace_id=ws_target, apply=True)

    assert result["counts"]["ground_conversations_processed"] == 1
    assert result["counts"]["canonical_conversations_created"] == 1
    assert session.conversations[0].workspace_id == ws_target


@pytest.mark.asyncio
async def test_error_handling_and_rollback():
    """
    Exceptions during execution trigger transactional rollback and record errors.
    """
    session = FakeReconciliationSession(fail_on_execute=True)
    engine = StateReconciliationEngine(session)

    result = await engine.reconcile(apply=True)

    assert result["mode"] == "failed"
    assert result["counts"]["errors"] == 1
    assert session.committed is False
    assert session.rolled_back is True
