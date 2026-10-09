"""
Canonical evidence for a Ground answer.

Open Notebook reports provenance in three ways: the answer's inline `[source:<id>]` citations, the chat response's
`evidence` list, and the hits of its (instance-wide) text search. Every upstream id is resolved to a canonical Neosis
`Source` ONLY through `OpenNotebookSourceBinding` rows of THIS workspace - never by title or similarity. The result:

  * resolved sources with stored metadata (file name, document reference, an excerpt from the stored document blocks);
  * citations the answer made that could not be resolved (no canonical source in this workspace, or outside the selected
    source scope) - exposed as unresolved, never presented as verified evidence;
  * a provenance status: full | partial | unresolved | none.

Search hits are retrieval candidates, not citations: hits from other workspaces (the Open Notebook search is not
notebook-scoped) are ignored rather than reported, and never fail the turn.
"""
import logging
import re
from typing import Any, Iterable, Optional
from uuid import UUID

from sqlalchemy import select

logger = logging.getLogger(__name__)

_INLINE_SOURCE_CITATION = re.compile(r"\[(source:[A-Za-z0-9]+)\]")
_WORD = re.compile(r"[a-z0-9]{4,}")


def inline_citation_ids(answer: str) -> list[str]:
    """Upstream source ids Open Notebook cited inline as `[source:<id>]`, in order, deduplicated."""
    return list(dict.fromkeys(_INLINE_SOURCE_CITATION.findall(answer or "")))


def _ids_from(items: Iterable[Any]) -> list[str]:
    out = []
    for e in items or []:
        if isinstance(e, dict):
            e = e.get("source_id") or e.get("id")
        if e:
            out.append(str(e))
    return out


async def upstream_to_canonical(upstream_ids: list[str], workspace_id: UUID, db: Any) -> dict[str, UUID]:
    """upstream id -> canonical source id, for bindings whose Source belongs to this workspace only."""
    from app.models.open_notebook_binding import OpenNotebookSourceBinding
    from app.models.source import Source

    if not upstream_ids:
        return {}
    rows = (await db.execute(
        select(OpenNotebookSourceBinding.open_notebook_source_id, OpenNotebookSourceBinding.source_id)
        .join(Source, Source.source_id == OpenNotebookSourceBinding.source_id)
        .where(Source.workspace_id == workspace_id,
               OpenNotebookSourceBinding.open_notebook_source_id.in_(list(set(upstream_ids))))
    )).all()
    return {str(u): s for u, s in rows}


async def _source_details(source_ids: list[UUID], workspace_id: UUID, answer: str, db: Any) -> dict[UUID, dict]:
    from app.models.block import DocumentBlock
    from app.models.source import Source, SourceSnapshot

    if not source_ids:
        return {}
    names = dict((await db.execute(
        select(SourceSnapshot.source_id, SourceSnapshot.filename)
        .join(Source, Source.source_id == SourceSnapshot.source_id)
        .where(Source.workspace_id == workspace_id, SourceSnapshot.source_id.in_(source_ids))
        .order_by(SourceSnapshot.created_at)
    )).all())
    wanted = set(_WORD.findall((answer or "").lower()))
    details = {}
    for sid in source_ids:
        blocks = (await db.execute(
            select(DocumentBlock.text_or_ref, DocumentBlock.page_number)
            .where(DocumentBlock.source_id == sid).order_by(DocumentBlock.sequence).limit(400)
        )).all()
        best = max(blocks, key=lambda b: len(set(_WORD.findall((b[0] or "").lower())) & wanted), default=None)
        details[sid] = {
            "source_id": str(sid),
            "title": names.get(sid),
            "document_ref": f"/api/v1/workspaces/{workspace_id}/sources/{sid}/download",
            "excerpt": (best[0] or "")[:400] if best else None,
            "page_number": best[1] if best else None,
        }
    return details


async def resolve_ground_evidence(
    *,
    answer: str,
    workspace_id: UUID,
    db: Any,
    search_hits: Optional[list] = None,
    chat_evidence: Optional[list] = None,
    source_scope: Optional[list] = None,
) -> dict:
    cited = list(dict.fromkeys(inline_citation_ids(answer) + _ids_from(chat_evidence)))
    retrieved = [str(h.get("id")) for h in (search_hits or []) if isinstance(h, dict) and h.get("id")]
    mapping = await upstream_to_canonical(cited + retrieved, workspace_id, db)
    scope = {UUID(str(s)) for s in source_scope} if source_scope else None

    resolved: dict[UUID, dict] = {}
    unresolved: list[dict] = []
    for uid in cited:
        sid = mapping.get(uid)
        if sid is None:
            unresolved.append({"upstream_id": uid, "reason": "no canonical source in this workspace"})
        elif scope is not None and sid not in scope:
            unresolved.append({"upstream_id": uid, "source_id": str(sid), "reason": "outside the selected source scope"})
        else:
            resolved.setdefault(sid, {"upstream_ids": [], "cited_inline": False, "retrieved": False})
            resolved[sid]["upstream_ids"].append(uid)
            resolved[sid]["cited_inline"] = True
    for uid in retrieved:
        sid = mapping.get(uid)
        if sid is None or (scope is not None and sid not in scope):
            continue  # another workspace's (or out-of-scope) search hit: not a citation of this answer
        resolved.setdefault(sid, {"upstream_ids": [], "cited_inline": False, "retrieved": False})
        if uid not in resolved[sid]["upstream_ids"]:
            resolved[sid]["upstream_ids"].append(uid)
        resolved[sid]["retrieved"] = True

    details = await _source_details(list(resolved), workspace_id, answer, db)
    evidence = [{**details[sid], **meta, "resolution": "resolved"} for sid, meta in resolved.items()]
    if resolved and not unresolved:
        status = "full"
    elif resolved:
        status = "partial"
    elif unresolved:
        status = "unresolved"
    else:
        status = "none"
    if unresolved:
        logger.warning("Ground answer has %d unresolved citation(s) in workspace %s", len(unresolved), workspace_id)
    return {"source_ids": list(resolved), "evidence": evidence, "unresolved": unresolved, "provenance_status": status}
