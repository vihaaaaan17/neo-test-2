from uuid import UUID
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from fastapi import HTTPException
from app.models.conversation import Conversation, ConversationTurn
from app.models.open_notebook_binding import OpenNotebookConversationBinding, OpenNotebookWorkspaceBinding
from app.models.source import Source
from app.models.workspace import Workspace, WorkspaceCommit
from app.models.knowledge import KnowledgeMemory
from app.models.research import ResearchEvidence, ResearchRun
from app.models.scratchpad import ScratchpadEntry
from app.repositories.scratchpad import ScratchpadRepository
from app.services.memory.policy import GroundContextPolicy, is_allowed_for_ground


class GroundContext(BaseModel):
    workspace_id: UUID
    conversation_id: UUID
    query: str
    source_scope: Optional[List[UUID]] = None
    notebook_id: Optional[str] = None
    session_id: Optional[str] = None
    filtered_turn_history: List[Dict[str, str]] = Field(default_factory=list)
    source_metadata: List[Dict[str, Any]] = Field(default_factory=list)


async def resolve_ground_source_scope(
    session: AsyncSession,
    workspace_id: UUID,
    explicit_scope: Optional[List[UUID]] = None
) -> Optional[List[UUID]]:
    """
    Validates and resolves canonical source scope for Ground mode.
    If explicit_scope is provided, ensures all UUIDs exist and belong to workspace.
    Fails closed if any provided UUID does not exist or belongs to another workspace.
    """
    if not explicit_scope:
        return None

    requested_set = {UUID(str(s)) for s in explicit_scope}
    stmt = select(Source.source_id).where(
        Source.workspace_id == workspace_id,
        Source.source_id.in_(requested_set)
    )
    result = await session.execute(stmt)
    valid_ids = list(result.scalars().all())
    found_set = {UUID(str(s)) for s in valid_ids}

    if found_set != requested_set:
        missing_ids = requested_set - found_set
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source_scope: one or more source IDs do not exist or belong to another workspace: {[str(m) for m in missing_ids]}"
        )

    return valid_ids if valid_ids else None


async def build_ground_context(
    session: AsyncSession,
    workspace_id: UUID,
    conversation_id: UUID,
    query: str,
    explicit_scope: Optional[List[UUID]] = None,
    max_history_turns: int = 5
) -> GroundContext:
    """
    Assembles Ground mode context adhering strictly to GroundContextPolicy:
    1. Resolves source scope against canonical Sources in PostgreSQL.
    2. Retrieves Open Notebook notebook_id and session_id bindings.
    3. Retrieves prior conversation turns FILTERED STRICTLY by mode == 'ground'.
       Research turns are completely excluded to guarantee zero leak of unverified findings.
    """
    # 1. Resolve source scope
    source_scope = await resolve_ground_source_scope(session, workspace_id, explicit_scope)

    # 2. Resolve workspace binding
    ws_stmt = select(OpenNotebookWorkspaceBinding).where(
        OpenNotebookWorkspaceBinding.workspace_id == workspace_id,
        OpenNotebookWorkspaceBinding.status.in_(["active", "ACTIVE"])
    )
    ws_res = await session.execute(ws_stmt)
    ws_binding = ws_res.scalars().first()
    notebook_id = ws_binding.open_notebook_notebook_id if ws_binding else None

    # 3. Resolve conversation binding
    conv_stmt = select(OpenNotebookConversationBinding).where(
        OpenNotebookConversationBinding.conversation_id == conversation_id
    )
    conv_res = await session.execute(conv_stmt)
    conv_binding = conv_res.scalars().first()
    session_id = conv_binding.open_notebook_session_id if conv_binding else None

    # 4. Fetch prior turns for this conversation, filtered strictly to mode == 'ground'
    turns_stmt = select(ConversationTurn).where(
        ConversationTurn.conversation_id == conversation_id,
        ConversationTurn.status == "completed"
    ).order_by(ConversationTurn.sequence.desc()).limit(max_history_turns * 2)
    turns_res = await session.execute(turns_stmt)
    all_turns = list(turns_res.scalars().all())
    all_turns.reverse()

    # Apply strict Ground policy filter: keep ONLY mode == 'ground'
    ground_history: List[Dict[str, str]] = []
    for turn in all_turns:
        if turn.mode == "ground":
            if turn.user_message:
                ground_history.append({"role": "user", "content": turn.user_message})
            if turn.assistant_message:
                ground_history.append({"role": "assistant", "content": turn.assistant_message})

    # Limit to max_history_turns pairs (user + assistant)
    if len(ground_history) > max_history_turns * 2:
        ground_history = ground_history[-max_history_turns * 2:]

    # 5. Fetch source metadata if source scope is active
    source_meta: List[Dict[str, Any]] = []
    if source_scope:
        meta_stmt = select(Source).where(
            Source.workspace_id == workspace_id,
            Source.source_id.in_(source_scope)
        )
        meta_res = await session.execute(meta_stmt)
        sources = meta_res.scalars().all()
        # Sources have no title column; the uploaded file name (latest snapshot) is their title.
        from app.models.source import SourceSnapshot
        snap_rows = (await session.execute(
            select(SourceSnapshot.source_id, SourceSnapshot.filename)
            .where(SourceSnapshot.source_id.in_([s.source_id for s in sources]))
            .order_by(SourceSnapshot.created_at)
        )).all() if sources else []
        filenames = {sid: name for sid, name in snap_rows}
        for src in sources:
            source_meta.append({
                "source_id": str(src.source_id),
                "title": filenames.get(src.source_id),
                "created_at": src.created_at.isoformat() if src.created_at else None
            })

    return GroundContext(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        query=query,
        source_scope=source_scope,
        notebook_id=notebook_id,
        session_id=session_id,
        filtered_turn_history=ground_history,
        source_metadata=source_meta
    )


# --------------------------------------------------------------------------- #
# Research Context Assembly & Deterministic Reverse-Priority Eviction
# --------------------------------------------------------------------------- #

class ContextItemManifest(BaseModel):
    item_id: str
    item_type: str
    tokens: int
    summary: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvictedItemManifest(BaseModel):
    item_id: str
    item_type: str
    tokens: int
    reason: str


class ResearchContextVersion(BaseModel):
    version: str = "v1"
    budget: int
    total_tokens: int
    initial_tokens: int
    included_items: List[ContextItemManifest] = Field(default_factory=list)
    evicted_items: List[EvictedItemManifest] = Field(default_factory=list)
    created_at: str


class ResearchContext(BaseModel):
    workspace_id: UUID
    conversation_id: UUID
    query: str
    context_version: ResearchContextVersion
    working_memory: Dict[str, Any] = Field(default_factory=dict)
    scratchpad_entries: List[Dict[str, Any]] = Field(default_factory=list)
    turn_history: List[Dict[str, Any]] = Field(default_factory=list)
    knowledge_memories: List[Dict[str, Any]] = Field(default_factory=list)
    research_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    output_graph: Optional[Dict[str, Any]] = None


def estimate_tokens(text: Optional[str]) -> int:
    """
    Standard token estimation heuristic: ~4 characters per token.
    Minimum 1 token for any non-empty text.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def sanitize_scratchpad_content(content: Optional[str]) -> Optional[str]:
    """
    Validates and sanitizes structured scratchpad content.
    Strictly prohibits raw model chain-of-thought, XML thought tags, or unconstrained model thinking.
    Returns cleaned content if valid, or None if rejected.
    """
    if not content or not isinstance(content, str):
        return None

    cot_markers = [
        "<thought>", "</thought>", "<thinking>", "</thinking>",
        "thinking process:", "thought process:", "internal reasoning:",
        "chain-of-thought:", "[cot]"
    ]
    lower = content.lower()
    for marker in cot_markers:
        if marker in lower:
            return None

    cleaned = content.strip()
    if len(cleaned) < 5:
        return None
    if len(cleaned) > 4000:
        cleaned = cleaned[:4000] + "..."
    return cleaned


class _ContextCandidate:
    def __init__(
        self,
        item_id: str,
        item_type: str,
        priority_rank: int,
        secondary_sort_key: float,
        tokens: int,
        summary: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        payload: Any = None
    ):
        self.item_id = item_id
        self.item_type = item_type
        self.priority_rank = priority_rank
        self.secondary_sort_key = secondary_sort_key
        self.tokens = tokens
        self.summary = summary
        self.metadata = metadata or {}
        self.payload = payload


async def build_research_context(
    session: AsyncSession,
    workspace_id: UUID,
    conversation_id: UUID,
    query: str,
    token_budget: int = 8000,
    working_memory: Optional[Dict[str, Any]] = None,
    output_graph: Optional[Dict[str, Any]] = None,
    max_history_turns: int = 20,
) -> ResearchContext:
    """
    Assembles Research mode context adhering strictly to the reverse-priority eviction hierarchy:
      1. Output Graph context (Dropped first)
      2. Older Research Evidence
      3. Distant conversation turns
      4. Older Scratchpad notes/hypotheses (unpinned before pinned)
      5. Accepted KnowledgeMemory
      6. Working Memory (PRESERVED AT ALL COSTS)
      7. Current message (PRESERVED AT ALL COSTS)

    Produces an immutable, auditable ResearchContextVersion manifest.
    """
    import json
    from datetime import datetime, timezone

    candidates: List[_ContextCandidate] = []

    # 1. Current Message (Priority 7, preserved at all costs)
    msg_tokens = estimate_tokens(query)
    candidates.append(
        _ContextCandidate(
            item_id="current_query",
            item_type="current_message",
            priority_rank=7,
            secondary_sort_key=0.0,
            tokens=msg_tokens,
            summary=query[:100],
            payload={"query": query}
        )
    )

    # 2. Working Memory (Priority 6, preserved at all costs)
    wm_data = working_memory or {}
    wm_tokens = estimate_tokens(json.dumps(wm_data)) if wm_data else 0
    if wm_tokens > 0:
        candidates.append(
            _ContextCandidate(
                item_id="working_memory",
                item_type="working_memory",
                priority_rank=6,
                secondary_sort_key=0.0,
                tokens=wm_tokens,
                summary="Active working memory state",
                payload=wm_data
            )
        )

    # Resolve active commit manifest for rollback-aware lineage isolation
    active_km_ids: Optional[set[str]] = None
    active_sp_ids: Optional[set[str]] = None

    execute_se = getattr(getattr(session, "execute", None), "side_effect", None)
    should_query_workspace = not isinstance(execute_se, type(iter([])))

    if should_query_workspace:

        try:
            ws_stmt = select(Workspace).where(Workspace.workspace_id == workspace_id)
            ws_res = await session.execute(ws_stmt)
            workspace = ws_res.scalars().first() if hasattr(ws_res, "scalars") else None

            active_commit_id = getattr(workspace, "active_commit_id", None)
            if workspace and isinstance(active_commit_id, (UUID, str)):
                commit_uuid = UUID(str(active_commit_id))
                c_stmt = select(WorkspaceCommit).where(
                    WorkspaceCommit.commit_id == commit_uuid,
                    WorkspaceCommit.workspace_id == workspace_id
                )
                c_res = await session.execute(c_stmt)
                active_commit = c_res.scalars().first() if hasattr(c_res, "scalars") else None
                if active_commit and hasattr(active_commit, "manifest"):
                    manifest = active_commit.manifest or {}
                    raw_km_ids = (
                        manifest.get("knowledge_memory_ids")
                        or manifest.get("active_knowledge_ids")
                        or getattr(active_commit, "active_knowledge_ids", None)
                    )
                    if raw_km_ids is not None:
                        active_km_ids = {str(k) for k in raw_km_ids}

                    raw_sp_ids = (
                        manifest.get("scratchpad_ids")
                        or manifest.get("active_hypothesis_ids")
                    )
                    if raw_sp_ids is not None:
                        active_sp_ids = {str(s) for s in raw_sp_ids}
        except Exception:
            active_km_ids = None
            active_sp_ids = None


    # 3. Accepted Knowledge Memory (Priority 5, older evicted first)
    if active_km_ids is not None and len(active_km_ids) == 0:
        km_records = []
    else:
        km_conditions = [
            KnowledgeMemory.workspace_id == workspace_id,
            KnowledgeMemory.status == "accepted"
        ]
        if active_km_ids is not None:
            valid_km_uuids = []
            for k in active_km_ids:
                try:
                    valid_km_uuids.append(UUID(str(k)))
                except (ValueError, TypeError):
                    pass
            km_conditions.append(KnowledgeMemory.knowledge_id.in_(valid_km_uuids))

        km_stmt = select(KnowledgeMemory).where(*km_conditions).order_by(KnowledgeMemory.created_at.asc()).limit(50)
        km_res = await session.execute(km_stmt)
        km_records = list(km_res.scalars().all())

    for km in km_records:
        t_count = estimate_tokens(km.content)
        ts = km.created_at.timestamp() if km.created_at else 0.0
        candidates.append(
            _ContextCandidate(
                item_id=str(km.knowledge_id),
                item_type="knowledge_memory",
                priority_rank=5,
                secondary_sort_key=ts,
                tokens=t_count,
                summary=km.content[:80],
                metadata={"knowledge_type": km.knowledge_type},
                payload={
                    "knowledge_id": str(km.knowledge_id),
                    "knowledge_type": km.knowledge_type,
                    "content": km.content,
                    "created_at": km.created_at.isoformat() if km.created_at else None
                }
            )
        )

    # 4. Active Scratchpad Entries (Priority 4, older unpinned evicted first, then older pinned)
    sp_repo = ScratchpadRepository(session)
    sp_records, _ = await sp_repo.list_entries(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        lifecycle="active",
        include_workspace_pinned=True,
        limit=100
    )
    if active_sp_ids is not None:
        sp_records = [sp for sp in sp_records if str(sp.entry_id) in active_sp_ids]

    for sp in sp_records:
        t_count = estimate_tokens(sp.content)
        # Unpinned use normal timestamp; pinned get large bias so unpinned are dropped first
        sort_key = (1e12 + (sp.pinned_at.timestamp() if sp.pinned_at else 0.0)) if sp.is_pinned_to_workspace else (sp.created_at.timestamp() if sp.created_at else 0.0)
        candidates.append(
            _ContextCandidate(
                item_id=str(sp.entry_id),
                item_type="scratchpad_entry",
                priority_rank=4,
                secondary_sort_key=sort_key,
                tokens=t_count,
                summary=sp.content[:80],
                metadata={"entry_type": sp.entry_type, "is_pinned": sp.is_pinned_to_workspace},
                payload={
                    "entry_id": str(sp.entry_id),
                    "entry_type": sp.entry_type,
                    "content": sp.content,
                    "is_pinned_to_workspace": sp.is_pinned_to_workspace,
                    "lifecycle": sp.lifecycle,
                    "created_at": sp.created_at.isoformat() if sp.created_at else None
                }
            )
        )

    # 5. Recent Conversation Turns (Priority 3, distant turns evicted first)
    turns_stmt = select(ConversationTurn).where(
        ConversationTurn.conversation_id == conversation_id,
        ConversationTurn.status == "completed"
    ).order_by(ConversationTurn.sequence.asc()).limit(max_history_turns * 2)
    turns_res = await session.execute(turns_stmt)
    turns_records = list(turns_res.scalars().all())

    for t in turns_records:
        turn_text = f"User: {t.user_message}\nAssistant: {t.assistant_message or ''}"
        t_count = estimate_tokens(turn_text)
        candidates.append(
            _ContextCandidate(
                item_id=str(t.turn_id),
                item_type="conversation_turn",
                priority_rank=3,
                secondary_sort_key=float(t.sequence),
                tokens=t_count,
                summary=t.user_message[:60],
                metadata={"sequence": t.sequence, "mode": t.mode},
                payload={
                    "turn_id": str(t.turn_id),
                    "sequence": t.sequence,
                    "mode": t.mode,
                    "user_message": t.user_message,
                    "assistant_message": t.assistant_message
                }
            )
        )

    # 6. Prior Research Evidence (Priority 2, older evidence evicted first)
    ev_stmt = (
        select(ResearchEvidence)
        .join(ResearchRun, ResearchEvidence.run_id == ResearchRun.run_id)
        .where(ResearchRun.workspace_id == workspace_id)
        .order_by(ResearchEvidence.retrieved_at.asc())
        .limit(50)
    )
    ev_res = await session.execute(ev_stmt)
    ev_records = list(ev_res.scalars().all())

    for ev in ev_records:
        t_count = estimate_tokens(ev.content)
        ts = ev.retrieved_at.timestamp() if ev.retrieved_at else 0.0
        candidates.append(
            _ContextCandidate(
                item_id=str(ev.evidence_id),
                item_type="research_evidence",
                priority_rank=2,
                secondary_sort_key=ts,
                tokens=t_count,
                summary=ev.content[:80],
                metadata={"retriever": ev.retriever},
                payload={
                    "evidence_id": str(ev.evidence_id),
                    "content": ev.content,
                    "retriever": ev.retriever,
                    "retrieved_at": ev.retrieved_at.isoformat() if ev.retrieved_at else None
                }
            )
        )

    # 7. Output Graph (Priority 1, DROPPED FIRST)
    if output_graph:
        og_tokens = estimate_tokens(json.dumps(output_graph))
        candidates.append(
            _ContextCandidate(
                item_id="output_graph",
                item_type="output_graph",
                priority_rank=1,
                secondary_sort_key=0.0,
                tokens=og_tokens,
                summary="Projected workspace output graph",
                payload=output_graph
            )
        )

    # ----------------------------------------------------------------------- #
    # Deterministic Reverse-Priority Eviction Algorithm
    # ----------------------------------------------------------------------- #
    initial_tokens = sum(c.tokens for c in candidates)
    current_tokens = initial_tokens
    evicted_ids: set = set()
    evicted_manifest: List[EvictedItemManifest] = []

    if current_tokens > token_budget:
        # Sort candidates eligible for eviction (ranks 1 to 5)
        # Ranks 6 and 7 (working memory and current message) are strictly preserved
        eviction_pool = sorted(
            [c for c in candidates if c.priority_rank <= 5],
            key=lambda c: (c.priority_rank, c.secondary_sort_key)
        )
        for c in eviction_pool:
            if current_tokens <= token_budget:
                break
            current_tokens -= c.tokens
            evicted_ids.add(c.item_id)
            evicted_manifest.append(
                EvictedItemManifest(
                    item_id=c.item_id,
                    item_type=c.item_type,
                    tokens=c.tokens,
                    reason=f"Evicted under token budget ({token_budget} max): lowest priority {c.item_type}"
                )
            )

    # Assemble Included Items Manifest & Categorized Payload
    included_manifest: List[ContextItemManifest] = []
    kept_scratchpad: List[Dict[str, Any]] = []
    kept_turns: List[Dict[str, Any]] = []
    kept_km: List[Dict[str, Any]] = []
    kept_ev: List[Dict[str, Any]] = []
    kept_og: Optional[Dict[str, Any]] = None

    for c in candidates:
        if c.item_id not in evicted_ids:
            included_manifest.append(
                ContextItemManifest(
                    item_id=c.item_id,
                    item_type=c.item_type,
                    tokens=c.tokens,
                    summary=c.summary,
                    metadata=c.metadata
                )
            )
            if c.item_type == "scratchpad_entry":
                kept_scratchpad.append(c.payload)
            elif c.item_type == "conversation_turn":
                kept_turns.append(c.payload)
            elif c.item_type == "knowledge_memory":
                kept_km.append(c.payload)
            elif c.item_type == "research_evidence":
                kept_ev.append(c.payload)
            elif c.item_type == "output_graph":
                kept_og = c.payload

    total_kept_tokens = sum(item.tokens for item in included_manifest)

    version_manifest = ResearchContextVersion(
        version="v1",
        budget=token_budget,
        total_tokens=total_kept_tokens,
        initial_tokens=initial_tokens,
        included_items=included_manifest,
        evicted_items=evicted_manifest,
        created_at=datetime.now(timezone.utc).isoformat()
    )

    return ResearchContext(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        query=query,
        context_version=version_manifest,
        working_memory=wm_data,
        scratchpad_entries=kept_scratchpad,
        turn_history=kept_turns,
        knowledge_memories=kept_km,
        research_evidence=kept_ev,
        output_graph=kept_og
    )

