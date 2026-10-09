"""
StudyReportCompiler: turns a whole study session (one conversation) into a cited, paper-style document.

Invoked ONLY on an explicit user request (the `POST .../study-report` endpoint, or a turn whose message is an explicit
compile request, see `is_study_report_request`). Ordinary Ground/Research turns never create reports.

Policy:
  * Authorization is enforced here (service layer): the conversation must belong to the workspace AND the requesting owner.
  * Reads only material already in that conversation: ordered completed turns, the canonical workspace sources its Ground
    turns cited (with relevant passages), the ResearchEvidence its research runs collected, and its scratchpad notes.
    It never launches research or calls a research engine.
  * ONE bounded LLM call returns the paper as structured claims: each statement has a kind (finding, hypothesis,
    interpretation, calculation, disagreement, open_question, framing) and the catalog numbers that support it.
  * Every claim is validated mechanically: cited numbers must exist in the catalog (fabricated ones are dropped) and must
    be lexically relevant to the claim against the STORED evidence text (irrelevant ones are dropped). A finding left
    without support is rendered as explicitly unsupported - a citation is never removed in a way that leaves its claim
    looking authoritative. Hypotheses/interpretations/calculations are labelled, disagreements need two sources.
  * References are generated from the catalog (stored titles/URLs/ids), never written by the model.
  * Persists a versioned study-session ResearchReport plus one `pending_review` memory candidate. Nothing is promoted.
"""
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

MAX_TURNS = 40
MAX_CATALOG = 80
TURN_USER_CHARS = 1500
TURN_ANSWER_CHARS = 3000
EXCERPT_CHARS = 500
CHECK_CHARS = 4000
MAX_NOTES = 40
NOTE_CHARS = 300

_VERB = re.compile(r"\b(compile|create|write|generate|produce|make|draft|turn|put together|assemble|build)\b", re.I)
_DOC = re.compile(r"\b(research paper|paper|report|write-?up|article|manuscript)\b", re.I)
_SCOPE = re.compile(
    r"\b(study session|this session|our session|the session|session|everything we(?:'ve| have)? (?:discussed|covered|talked about|found|learned)"
    r"|what we(?:'ve| have)? (?:discussed|covered|found|learned)|we(?:'ve| have) discussed|discussed so far|so far"
    r"|this (?:chat|conversation)|our (?:chat|conversation|discussion)|the (?:conversation|discussion))\b",
    re.I,
)


def is_study_report_request(message: str) -> bool:
    """An explicit request to compile the session into a paper: a compile verb, a document noun and a session scope."""
    text = message or ""
    return bool(_VERB.search(text) and _DOC.search(text) and _SCOPE.search(text))


class StudySessionEmpty(Exception):
    pass


class StudySessionNotFound(Exception):
    """The conversation does not exist in this workspace or does not belong to the requester."""


@dataclass
class CatalogEntry:
    n: int
    kind: str  # "workspace_source" | "research_evidence"
    ref_id: str
    title: str
    excerpt: str  # shown to the model
    url: Optional[str] = None
    turn_sequences: list[int] = field(default_factory=list)
    check_text: str = ""  # stored text used to validate claim relevance (not sent to the model)

    def reference_line(self) -> str:
        if self.kind == "workspace_source":
            return f"[{self.n}] {self.title} (uploaded workspace source {self.ref_id}). Passage: \"{self.excerpt[:200]}\""
        return f"[{self.n}] {self.title or self.url} - {self.url} (research evidence {self.ref_id})"

    def public(self) -> dict:
        return {"n": self.n, "kind": self.kind, "ref_id": self.ref_id, "title": self.title, "url": self.url,
                "excerpt": self.excerpt[:300], "turn_sequences": self.turn_sequences}


@dataclass
class StudyMaterial:
    turns: list[dict]
    catalog: list[CatalogEntry]
    notes: list[dict]
    run_ids: list[str]


@dataclass
class CompiledPaper:
    content: str
    cited: list[CatalogEntry]
    invalid_markers: list[str]
    removed_links: list[str]
    warnings: list[str]
    claims: dict = field(default_factory=dict)  # counts by validation outcome
    structured: bool = False


# --------------------------------------------------------------------------- #
# Gathering (DB, scoped to workspace + conversation)
# --------------------------------------------------------------------------- #
def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]{4,}", (text or "").lower())}


def _ground_source_ids(refs: Any) -> list[str]:
    out = []
    for r in refs or []:
        if isinstance(r, dict):
            r = r.get("source_id") or r.get("id")
        if r:
            out.append(str(r))
    return out


async def gather_study_material(session: Any, workspace_id: UUID, conversation_id: UUID) -> StudyMaterial:
    from sqlalchemy import select

    from app.models.block import DocumentBlock
    from app.models.conversation import ConversationTurn
    from app.models.research import ResearchEvidence, ResearchRun
    from app.models.source import Source, SourceSnapshot
    from app.repositories.scratchpad import ScratchpadRepository

    rows = (await session.execute(
        select(ConversationTurn)
        .where(ConversationTurn.workspace_id == workspace_id, ConversationTurn.conversation_id == conversation_id,
               ConversationTurn.status.in_(("completed", "partial")))
        .order_by(ConversationTurn.sequence)
    )).scalars().all()
    rows = [t for t in rows if not (isinstance(t.context_version, dict) and t.context_version.get("study_report"))]
    rows = rows[-MAX_TURNS:]

    turns = [{
        "turn_id": str(t.turn_id), "sequence": int(t.sequence), "mode": t.mode,
        "user": (t.user_message or "")[:TURN_USER_CHARS], "assistant": (t.assistant_message or "")[:TURN_ANSWER_CHARS],
        "research_run_id": str(t.research_run_id) if t.research_run_id else None,
    } for t in rows]

    catalog: list[CatalogEntry] = []

    # Canonical workspace sources cited by Ground turns, with the passages most relevant to the questions asked.
    cited_by: dict[str, list[int]] = {}
    question_words: dict[str, set[str]] = {}
    for t in rows:
        if t.mode != "ground":
            continue
        for sid in _ground_source_ids(t.ground_evidence_refs):
            cited_by.setdefault(sid, []).append(int(t.sequence))
            question_words.setdefault(sid, set()).update(_words(t.user_message) | _words(t.assistant_message))
    for sid, seqs in cited_by.items():
        try:
            source_uuid = UUID(sid)
        except ValueError:
            continue
        source = (await session.execute(
            select(Source).where(Source.source_id == source_uuid, Source.workspace_id == workspace_id)
        )).scalars().first()
        if source is None:  # not a canonical source of THIS workspace: never citable
            continue
        snap = (await session.execute(
            select(SourceSnapshot).where(SourceSnapshot.source_id == source_uuid).order_by(SourceSnapshot.created_at.desc())
        )).scalars().first()
        blocks = (await session.execute(
            select(DocumentBlock).where(DocumentBlock.source_id == source_uuid).order_by(DocumentBlock.sequence).limit(400)
        )).scalars().all()
        wanted = question_words.get(sid, set())
        ranked = sorted(blocks, key=lambda b: len(_words(b.text_or_ref) & wanted), reverse=True)
        passage = " ... ".join((b.text_or_ref or "").strip() for b in ranked[:2])[:EXCERPT_CHARS]
        check = " ".join((b.text_or_ref or "") for b in ranked[:12])[:CHECK_CHARS]
        catalog.append(CatalogEntry(n=0, kind="workspace_source", ref_id=sid, title=snap.filename if snap else f"Source {sid}",
                                    excerpt=passage, turn_sequences=seqs, check_text=check))

    # ResearchEvidence collected by this conversation's research runs (deduplicated by URL).
    run_rows = (await session.execute(
        select(ResearchRun.run_id, ResearchRun.turn_id)
        .where(ResearchRun.workspace_id == workspace_id, ResearchRun.conversation_id == conversation_id)
    )).all()
    run_ids = [r[0] for r in run_rows]
    seq_by_turn = {t["turn_id"]: t["sequence"] for t in turns}
    seq_by_run = {str(r[0]): seq_by_turn.get(str(r[1])) for r in run_rows}
    if run_ids:
        evidence = (await session.execute(
            select(ResearchEvidence).where(ResearchEvidence.run_id.in_(run_ids))
            .order_by(ResearchEvidence.retrieved_at, ResearchEvidence.evidence_id)
        )).scalars().all()
        seen: dict[str, CatalogEntry] = {}
        for ev in evidence:
            prov = ev.provenance or {}
            url = prov.get("url") or ev.locator
            if not url:
                continue
            seq = seq_by_run.get(str(ev.run_id))
            if url in seen:
                if seq is not None and seq not in seen[url].turn_sequences:
                    seen[url].turn_sequences.append(seq)
                continue
            entry = CatalogEntry(n=0, kind="research_evidence", ref_id=str(ev.evidence_id), title=prov.get("title") or url,
                                 url=url, excerpt=(ev.content or "")[:EXCERPT_CHARS],
                                 turn_sequences=[seq] if seq is not None else [], check_text=(ev.content or "")[:CHECK_CHARS])
            seen[url] = entry
            catalog.append(entry)

    catalog = catalog[:MAX_CATALOG]
    for i, entry in enumerate(catalog, start=1):
        entry.n = i

    entries, _ = await ScratchpadRepository(session).list_entries(
        workspace_id=workspace_id, conversation_id=conversation_id, include_workspace_pinned=False, limit=MAX_NOTES
    )
    notes = [{"entry_id": str(e.entry_id), "type": e.entry_type, "content": (e.content or "")[:NOTE_CHARS]}
             for e in reversed(entries)]

    return StudyMaterial(turns=turns, catalog=catalog, notes=notes, run_ids=[str(r) for r in run_ids])


# --------------------------------------------------------------------------- #
# Composition (pure; one LLM call)
# --------------------------------------------------------------------------- #
CLAIM_KINDS = ("finding", "hypothesis", "interpretation", "calculation", "disagreement", "open_question", "framing")


def build_prompt(request: str, material: StudyMaterial) -> str:
    turns = "\n\n".join(
        f"--- Turn {t['sequence']} ({t['mode']}) ---\nUser: {t['user']}\nAssistant: {t['assistant']}" for t in material.turns
    )
    catalog = "\n".join(
        f"[{c.n}] ({'uploaded source' if c.kind == 'workspace_source' else 'web evidence'}) {c.title}"
        + (f" <{c.url}>" if c.url else "") + f"\n    excerpt: {c.excerpt}"
        for c in material.catalog
    ) or "(no citable evidence was collected in this session)"
    notes = "\n".join(f"- ({n['type']}) {n['content']}" for n in material.notes) or "(none)"
    return f"""You are compiling a study session into a research-paper-style document.

User request: {request}

Write the paper ONLY from the material below. Do not add facts, sources or URLs that are not in it.
Return ONE JSON object and nothing else, with this shape:
{{"title": "...", "sections": [{{"heading": "...", "statements": [{{"text": "...", "kind": "finding", "citations": [3],
  "support": [{{"n": 3, "quote": "exact words copied from excerpt [3] that support the statement"}}]}}]}}]}}
Sections, in order: Abstract; Introduction and research questions; Background; Findings (one section per theme);
Discussion; Open questions and limitations; Conclusion.
Statement kinds:
- "finding": a factual claim. It MUST list the catalog numbers whose excerpt supports it, and for each one a "support"
  entry quoting 5-30 words copied EXACTLY (verbatim) from that excerpt. Quotes are checked against the stored evidence;
  a claim whose quote is not found verbatim, or does not match the claim, is marked as not verified.
- "hypothesis": a conjecture raised in the session (citations optional).
- "interpretation": your reading of the evidence (cite what it rests on).
- "calculation": a number derived during the session (it will be labelled as not externally verified).
- "disagreement": sources conflict - cite at least two catalog numbers on different sides.
- "open_question": an unresolved question.
- "framing": a non-factual connecting sentence (no facts, no numbers).
Use ONLY numbers listed in the EVIDENCE CATALOG. If a claim from the conversation has no supporting catalog entry, keep it
as a finding with an empty citations list (it will be marked unsupported) or leave it out. Do not write a references list.

=== CONVERSATION (ordered) ===
{turns}

=== SCRATCHPAD (findings, hypotheses, notes) ===
{notes}

=== EVIDENCE CATALOG ===
{catalog}
"""


_STOP = set("""
that this with from have been were what when where which their there they them into over than then also such
these those will would could should about after before because between while being other more most some only
very each both does used using uses based through within without across among make made many much
""".split())


def _claim_terms(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z][a-z0-9\-]{3,}", (text or "").lower()):
        if w in _STOP:
            continue
        for suf in ("ies", "ing", "es", "s", "ed"):
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                w = w[: -len(suf)]
                break
        if w.endswith("e") and len(w) > 4:  # reduce / reduces / reduced -> reduc
            w = w[:-1]
        out.add(w)
    return out


def is_relevant(claim: str, entry: CatalogEntry) -> bool:
    """Lexical support check: the cited stored text must share enough distinctive terms with the claim."""
    terms = _claim_terms(claim)
    if not terms:
        return True
    shared = terms & _claim_terms(f"{entry.title} {entry.check_text or entry.excerpt}")
    need = 1 if len(terms) <= 3 else 2
    return len(shared) >= need


def _extract_json(raw: str) -> Optional[dict]:
    text = (raw or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        return None
    return data if isinstance(data, dict) and isinstance(data.get("sections"), list) else None


_FACTUAL = re.compile(r"\d|%|\baccording to\b", re.I)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%./\- ]", " ", (text or "").lower())).strip()


def verify_quote(claim: str, quote: str, entry: CatalogEntry) -> bool:
    """
    Deterministic passage check: the quote must be at least 5 words, appear verbatim (after whitespace/punctuation
    normalisation) in the STORED evidence text of the cited entry, and share distinctive terms with the claim.
    It proves the cited passage exists and is about the claim; it does not prove logical entailment.
    """
    q = _norm(quote)
    if len(q.split()) < 5:
        return False
    if q not in _norm(f"{entry.check_text} {entry.excerpt}"):
        return False
    claim_terms, quote_terms = _claim_terms(claim), _claim_terms(quote)
    need = 1 if len(claim_terms) <= 3 else 2
    return len(claim_terms & quote_terms) >= need


def render_structured(data: dict, catalog: list[CatalogEntry]) -> CompiledPaper:
    by_n = {c.n: c for c in catalog}
    cited: dict[int, CatalogEntry] = {}
    fabricated: list[str] = []
    irrelevant: list[dict] = []
    unverified_quotes: list[dict] = []
    claim_records: list[dict] = []
    counts = {k: 0 for k in ("supported", "weakly_supported", "unsupported", "hypothesis", "interpretation", "calculation",
                             "disagreement", "open_question", "framing")}
    lines = [f"# {str(data.get('title') or 'Study Session Report').strip()}", ""]

    for section in data.get("sections") or []:
        if not isinstance(section, dict):
            continue
        lines += [f"## {str(section.get('heading') or 'Section').strip()}", ""]
        for st in section.get("statements") or []:
            if not isinstance(st, dict) or not str(st.get("text") or "").strip():
                continue
            text = str(st["text"]).strip()
            kind = st.get("kind") if st.get("kind") in CLAIM_KINDS else "finding"
            quotes: dict[int, str] = {}
            for sup in st.get("support") or []:
                if isinstance(sup, dict):
                    try:
                        quotes[int(sup.get("n"))] = str(sup.get("quote") or "")
                    except (TypeError, ValueError):
                        fabricated.append(str(sup.get("n")))
            nums = []
            for raw in list(st.get("citations") or []) + list(quotes):
                try:
                    nums.append(int(raw))
                except (TypeError, ValueError):
                    fabricated.append(str(raw))
            kept, verified = [], []
            for n in dict.fromkeys(nums):
                if n not in by_n:  # 1. existence: the id must belong to THIS session's gathered evidence
                    fabricated.append(str(n))
                    continue
                if n in quotes and quotes[n].strip():
                    if verify_quote(text, quotes[n], by_n[n]):  # 2a. passage check against stored text
                        kept.append(n)
                        verified.append(n)
                        continue
                    unverified_quotes.append({"claim": text[:160], "citation": n})
                if is_relevant(text, by_n[n]):  # 2b. weaker: the cited source is at least about the claim
                    kept.append(n)
                else:
                    irrelevant.append({"claim": text[:160], "citation": n})
            for n in kept:
                cited[n] = by_n[n]
            marker = f" [{', '.join(map(str, kept))}]" if kept else ""

            if kind == "framing" and _FACTUAL.search(text):
                kind = "finding"  # a "framing" sentence carrying facts must be supported like a finding
            support_level = "verified_passage" if verified else ("related_source" if kept else "none")
            claim_records.append({"text": text[:300], "kind": kind, "support_level": support_level,
                                  "citations": [{"n": n, "ref_id": by_n[n].ref_id, "quote_verified": n in verified,
                                                 # only a quote that was found verbatim in stored evidence is kept
                                                 "quote": quotes[n] if n in verified else None} for n in kept]})
            if kind == "finding":
                if verified:
                    counts["supported"] += 1
                    lines.append(f"{text}{marker}")
                elif kept:
                    counts["weakly_supported"] += 1
                    lines.append(f"*[Related source cited; no supporting passage verified]* {text}{marker}")
                else:
                    counts["unsupported"] += 1
                    lines.append(f"*[Unsupported by the collected evidence]* {text}")
            elif kind == "disagreement":
                if len(kept) >= 2:
                    counts["disagreement"] += 1
                    lines.append(f"*Sources disagree:* {text}{marker}")
                else:
                    counts["unsupported"] += 1
                    lines.append(f"*[Unsupported - a disagreement needs two supporting sources]* {text}{marker}")
            elif kind == "hypothesis":
                counts["hypothesis"] += 1
                lines.append(f"*Hypothesis (not established):* {text}{marker}")
            elif kind == "interpretation":
                counts["interpretation"] += 1
                lines.append(f"*Interpretation:* {text}{marker}")
            elif kind == "calculation":
                counts["calculation"] += 1
                lines.append(f"{text}{marker} *(computed during the session; not externally verified)*")
            elif kind == "open_question":
                counts["open_question"] += 1
                lines.append(f"*Open question:* {text}{marker}")
            else:
                counts["framing"] += 1
                lines.append(text)
            lines.append("")

    ordered = [cited[n] for n in sorted(cited)]
    references = "\n".join(c.reference_line() for c in ordered) or "No collected evidence was cited."
    content = "\n".join(lines).rstrip() + f"\n\n## References\n\n{references}\n"
    warnings = []
    if fabricated:
        warnings.append(f"Dropped {len(fabricated)} citation(s) to numbers not in the evidence catalog: {', '.join(sorted(set(fabricated)))}")
    if irrelevant:
        warnings.append(f"Dropped {len(irrelevant)} citation(s) whose stored evidence does not match the claim")
    if unverified_quotes:
        warnings.append(f"{len(unverified_quotes)} quoted passage(s) were not found verbatim in the cited stored evidence")
    if counts["weakly_supported"]:
        warnings.append(f"{counts['weakly_supported']} claim(s) cite a related source without a verified supporting passage")
    if counts["unsupported"]:
        warnings.append(f"{counts['unsupported']} claim(s) are marked unsupported by the collected evidence")
    if not catalog:
        warnings.append("The session has no citable evidence; every factual claim is marked unsupported.")
    return CompiledPaper(content=content, cited=ordered, invalid_markers=sorted(set(fabricated)), removed_links=[],
                         warnings=warnings, claims={**counts, "irrelevant_citations": irrelevant,
                                                    "unverified_quotes": unverified_quotes, "records": claim_records},
                         structured=True)


_MARKER = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_TRAILING_REFS = re.compile(r"\n#{1,6}\s*(references|bibliography|sources|works cited)\s*:?\s*(\n.*)?\Z", re.I | re.S)
_SENT = re.compile(r"(?<=[.!?])\s+")


def validate_citations(text: str, catalog: list[CatalogEntry]) -> CompiledPaper:
    """
    Fallback for a model that ignored the structured format: validates markdown sentence by sentence. A citation that is
    fabricated or irrelevant is removed AND its sentence is visibly marked unsupported if no valid citation remains.
    """
    by_n = {c.n: c for c in catalog}
    allowed_urls = {c.url for c in catalog if c.url}
    invalid: list[str] = []
    removed_links: list[str] = []
    irrelevant: list[dict] = []
    cited: dict[int, CatalogEntry] = {}
    unsupported = 0

    body = _TRAILING_REFS.sub("", text or "").rstrip()

    def fix_link(m: re.Match) -> str:
        if m.group(2) in allowed_urls:
            return m.group(0)
        removed_links.append(m.group(2))
        return m.group(1)

    body = _LINK.sub(fix_link, body)

    out_paragraphs = []
    for para in body.split("\n"):
        sentences = _SENT.split(para) if para and not para.lstrip().startswith("#") else [para]
        fixed = []
        for sentence in sentences:
            markers = list(_MARKER.finditer(sentence))
            if not markers:
                fixed.append(sentence)
                continue
            claim = _MARKER.sub("", sentence)
            kept_any = False

            def fix_marker(m: re.Match) -> str:
                nonlocal kept_any
                good = []
                for n in (int(x) for x in re.split(r"\s*,\s*", m.group(1))):
                    if n not in by_n:
                        invalid.append(str(n))
                    elif not is_relevant(claim, by_n[n]):
                        irrelevant.append({"claim": claim[:160], "citation": n})
                    else:
                        good.append(n)
                        cited[n] = by_n[n]
                kept_any = kept_any or bool(good)
                return f"[{', '.join(map(str, good))}]" if good else ""

            new = _MARKER.sub(fix_marker, sentence)
            if not kept_any:
                unsupported += 1
                new = f"*[Unsupported by the collected evidence]* {new.strip()}"
            fixed.append(new)
        out_paragraphs.append(" ".join(fixed))
    body = "\n".join(out_paragraphs)

    ordered = [cited[n] for n in sorted(cited)]
    references = "\n".join(c.reference_line() for c in ordered) or "No collected evidence was cited."
    content = f"{body}\n\n## References\n\n{references}\n"

    warnings = ["The model did not return structured claims; citations were validated sentence by sentence."]
    if invalid:
        warnings.append(f"Removed {len(invalid)} citation marker(s) not in the evidence catalog: {', '.join(sorted(set(invalid)))}")
    if irrelevant:
        warnings.append(f"Removed {len(irrelevant)} citation(s) whose stored evidence does not match the sentence")
    if removed_links:
        warnings.append(f"Removed {len(removed_links)} link(s) to URLs that are not in the collected evidence")
    if not catalog:
        warnings.append("The session has no citable evidence; the paper is uncited.")
    return CompiledPaper(content=content, cited=ordered, invalid_markers=invalid, removed_links=removed_links,
                         warnings=warnings, claims={"unsupported": unsupported, "irrelevant_citations": irrelevant})


def compose_paper(raw: str, catalog: list[CatalogEntry]) -> CompiledPaper:
    data = _extract_json(raw)
    return render_structured(data, catalog) if data is not None else validate_citations(raw, catalog)


# --------------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------------- #
class StudyReportCompiler:
    def __init__(self, session: Any, llm: Optional[Callable[[str], Awaitable[str]]] = None, llm_timeout_s: float = 300):
        self.session = session
        self._llm = llm
        self._llm_timeout_s = llm_timeout_s

    async def _call_llm(self, prompt: str) -> str:
        import asyncio

        if self._llm is not None:
            call = self._llm(prompt)
        else:
            from app.api.deps.llm import llm_call
            call = llm_call(prompt)
        return await asyncio.wait_for(call, timeout=self._llm_timeout_s)

    async def _authorize(self, workspace_id: UUID, conversation_id: UUID, owner_id: Optional[UUID]) -> None:
        from sqlalchemy import select

        from app.models.conversation import Conversation

        conv = (await self.session.execute(
            select(Conversation).where(Conversation.conversation_id == conversation_id, Conversation.workspace_id == workspace_id)
        )).scalars().first()
        if conv is None or (owner_id is not None and conv.owner_id != owner_id):
            raise StudySessionNotFound("study_session_not_found")

    async def compile(self, workspace_id: UUID, conversation_id: UUID, request: str, owner_id: Optional[UUID] = None) -> dict:
        from sqlalchemy import func, select

        from app.models.research import ResearchArtifact, ResearchReport

        await self._authorize(workspace_id, conversation_id, owner_id)
        material = await gather_study_material(self.session, workspace_id, conversation_id)
        if not material.turns:
            raise StudySessionEmpty("study_session_empty")

        raw = await self._call_llm(build_prompt(request, material))
        paper = compose_paper(raw if isinstance(raw, str) else str(raw), material.catalog)

        previous = (await self.session.execute(
            select(ResearchReport.report_id, func.count().over())
            .where(ResearchReport.scope == "study_session", ResearchReport.workspace_id == workspace_id,
                   ResearchReport.conversation_id == conversation_id)
            .order_by(ResearchReport.created_at.desc()).limit(1)
        )).first()
        version = (previous[1] + 1) if previous else 1

        limitations = (
            "Compiled only from this session's turns, cited workspace sources and collected research evidence; no new "
            "research was run. Every citation was checked to belong to this session's evidence. A finding counts as "
            "supported only when its quoted passage was found verbatim in the stored evidence and matches the claim's terms; "
            "findings citing a merely related source are labelled. This is a passage check, not proof that the source "
            "logically entails the claim, and the paper is not independently fact-checked."
        )
        source_summary = {
            "turn_ids": [t["turn_id"] for t in material.turns],
            "workspace_source_ids": [c.ref_id for c in material.catalog if c.kind == "workspace_source"],
            "research_evidence_ids": [c.ref_id for c in material.catalog if c.kind == "research_evidence"],
            "research_run_ids": material.run_ids,
            "scratchpad_entry_ids": [n["entry_id"] for n in material.notes],
            "previous_report_id": str(previous[0]) if previous else None,
        }
        report = ResearchReport(
            scope="study_session", workspace_id=workspace_id, conversation_id=conversation_id, run_id=None,
            objective=request, content=paper.content,
            citations={"cited": [c.public() for c in paper.cited], "invalid_markers": paper.invalid_markers,
                       "removed_links": paper.removed_links, "claims": paper.claims, "structured": paper.structured},
            source_summary=source_summary, limitations=limitations, warnings="\n".join(paper.warnings) or None,
            version=str(version), status="draft",
        )
        self.session.add(report)
        await self.session.flush()

        evidence_refs = [c.ref_id for c in paper.cited if c.kind == "research_evidence"]
        source_refs = (
            [{"ref_type": "research_evidence", "ref_id": c.ref_id} for c in paper.cited if c.kind == "research_evidence"]
            + [{"ref_type": "canonical_source", "ref_id": c.ref_id} for c in paper.cited if c.kind == "workspace_source"]
            + [{"ref_type": "conversation_turn", "ref_id": t["turn_id"]} for t in material.turns]
        )
        candidate = ResearchArtifact(
            run_id=None, workspace_id=workspace_id, conversation_id=conversation_id, type="memory_candidate",
            promotion_status="pending_review", tags=["study_session_report"],
            payload={
                "candidate_type": "memory_candidate", "content": paper.content, "text": paper.content,
                "report_id": str(report.report_id), "report_version": version, "evidence_refs": evidence_refs,
                "source_refs": source_refs,
                "provenance": {"source_refs": evidence_refs, "derived_from_refs": evidence_refs, "derived_from": source_refs},
                "proposed_memory_type": "research_memory", "provenance_version": "v2", "domain": "study_session",
                "metadata": {"source": "study_report_compiler", "conversation_id": str(conversation_id)},
            },
        )
        self.session.add(candidate)
        await self.session.commit()
        return {
            "report_id": str(report.report_id),
            "candidate_id": str(candidate.artifact_id),
            "version": version,
            "content": paper.content,
            "cited": [c.public() for c in paper.cited],
            "claims": paper.claims,
            "structured": paper.structured,
            "warnings": paper.warnings,
            "limitations": limitations,
            "source_summary": source_summary,
        }
