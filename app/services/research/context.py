"""
Engine-agnostic formatting of Neosis research context for upstream research engines.

Neosis owns context assembly (Chapter 4). Adapters receive plain data and decide how the
upstream engine consumes it; nothing here knows about a specific engine.
"""
from typing import Any, Iterable, Optional


def build_prior_evidence_context(
    evidence_items: Optional[Iterable[Any]],
    max_items: int = 10,
    max_chars: int = 1500,
) -> str:
    """
    Bounded "PREVIOUS RESEARCH FINDINGS" block for a retried run, built from the evidence already
    persisted for the same run_id. Returns an empty string when there is nothing to inject.
    """
    items = list(evidence_items or [])
    if not items:
        return ""
    texts = []
    for ev in items[-max_items:]:
        source = getattr(ev, "locator", None) or "Unknown Source"
        content = getattr(ev, "content", None) or ""
        snippet = (content[:max_chars] + "...") if len(content) > max_chars else content
        texts.append(f"Source: {source}\n{snippet}")
    return "PREVIOUS RESEARCH FINDINGS (Do not duplicate this work):\n\n" + "\n\n---\n\n".join(texts)


def format_research_context(research_context: Optional[dict]) -> str:
    """
    Formats a canonical ResearchContext snapshot (as produced by
    build_research_context / ConversationTurn.context_version) into an
    authoritative RESEARCH CONTEXT AND WORKING STATE system block.

    This is the ONLY mechanism by which Chapter 4 context reaches an upstream engine.
    Engine adapters decide how to inject the returned block (ODR prepends it to the objective).
    Upstream engine nodes, supervisors, researcher graphs, and prompts
    remain 100% untouched.

    Returns an empty string when no research_context is provided so callers
    can conditionally prepend the block.
    """
    if not research_context:
        return ""

    def _summarize_entries(entries, key="content", max_chars=200):
        if not entries:
            return "  (none)"
        lines = []
        for entry in entries:
            if isinstance(entry, dict):
                if key == "user_message" and ("user_message" in entry or "assistant_message" in entry):
                    u = entry.get("user_message", "")
                    a = entry.get("assistant_message", "")
                    if u and a:
                        value = f"User: {u} | Assistant: {a}"
                    elif u:
                        value = f"User: {u}"
                    elif a:
                        value = f"Assistant: {a}"
                    else:
                        value = entry.get("content") or ""
                elif "role" in entry and "content" in entry:
                    value = f"{entry.get('role').capitalize()}: {entry.get('content')}"
                elif "entry_type" in entry and "content" in entry:
                    value = f"[{entry.get('entry_type')}] {entry.get('content')}"
                elif "knowledge_type" in entry and "content" in entry:
                    value = f"[{entry.get('knowledge_type')}] {entry.get('content')}"
                elif "retriever" in entry and "content" in entry:
                    value = f"[{entry.get('retriever')}] {entry.get('content')}"
                else:
                    value = entry.get(key) or entry.get("content") or entry.get("text") or ""
            else:
                value = str(entry)
            if value:
                snippet = str(value).strip().replace("\n", " ")
                if len(snippet) > max_chars:
                    snippet = snippet[:max_chars] + "..."
                lines.append(f"  - {snippet}")
        return "\n".join(lines) if lines else "  (none)"

    # Accept either a pydantic model_dump dict or a plain dict.
    ctx = research_context
    if not isinstance(ctx, dict):
        # Pydantic models expose model_dump(); fall back to dict() otherwise.
        ctx = ctx.model_dump() if hasattr(ctx, "model_dump") else dict(ctx)

    workspace_id = ctx.get("workspace_id")
    conversation_id = ctx.get("conversation_id")
    query = ctx.get("query", "")
    context_version = ctx.get("context_version") or {}
    working_memory = ctx.get("working_memory") or {}
    scratchpad_entries = ctx.get("scratchpad_entries") or []
    turn_history = ctx.get("turn_history") or []
    knowledge_memories = ctx.get("knowledge_memories") or []
    research_evidence = ctx.get("research_evidence") or []
    output_graph = ctx.get("output_graph")

    budget = context_version.get("budget") if isinstance(context_version, dict) else None
    total_tokens = context_version.get("total_tokens") if isinstance(context_version, dict) else None
    version = context_version.get("version") if isinstance(context_version, dict) else None

    if budget is None and "budget" in ctx:
        budget = ctx.get("budget")
    if total_tokens is None and "total_tokens" in ctx:
        total_tokens = ctx.get("total_tokens")
    if version is None and "version" in ctx:
        version = ctx.get("version")

    lines = ["=== RESEARCH CONTEXT AND WORKING STATE ==="]
    if workspace_id is not None:
        lines.append(f"- Workspace: {workspace_id}")
    if conversation_id is not None:
        lines.append(f"- Conversation: {conversation_id}")
    if version is not None:
        lines.append(f"- Context Version: {version}")
    if budget is not None and total_tokens is not None:
        lines.append(f"- Token Budget: {total_tokens}/{budget}")
    elif budget is not None:
        lines.append(f"- Token Budget: {budget}")

    lines.append("")
    lines.append("Bounded Prior Turns:")
    lines.append(_summarize_entries(turn_history, key="user_message"))

    lines.append("")
    lines.append("Working Memory State:")
    if working_memory:
        wm_lines = [f"  - {k}: {v}" for k, v in working_memory.items()]
        lines.append("\n".join(wm_lines))
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append("Active Scratchpad Hypotheses:")
    lines.append(_summarize_entries(scratchpad_entries, key="content"))

    lines.append("")
    lines.append("Accepted Knowledge Memories:")
    lines.append(_summarize_entries(knowledge_memories, key="content"))

    lines.append("")
    lines.append("Prior Research Evidence & Graph Summary:")
    lines.append(_summarize_entries(research_evidence, key="content"))
    if output_graph:
        node_count = len(output_graph.get("nodes", [])) if isinstance(output_graph, dict) and "nodes" in output_graph else None
        edge_count = len(output_graph.get("edges", [])) if isinstance(output_graph, dict) and "edges" in output_graph else None
        if node_count is not None and edge_count is not None:
            lines.append(f"  Output Graph: present ({node_count} nodes, {edge_count} edges)")
        else:
            lines.append("  Output Graph: present (projected workspace graph)")
    else:
        lines.append("  Output Graph: (none)")

    lines.append("")
    lines.append(f"Current Objective: {query}")
    lines.append("=== END RESEARCH CONTEXT AND WORKING STATE ===")

    return "\n".join(lines)
