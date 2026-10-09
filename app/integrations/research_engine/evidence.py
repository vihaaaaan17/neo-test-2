"""
Neosis evidence boundary for engines that return their sources in bulk (STORM, GPT-Researcher).

ODR persists evidence incrementally through `neosis_web_search` as the upstream agent searches. Engines that
run their own retrieval internally hand their final source list back to the adapter instead; this helper
turns that list into canonical `ResearchEvidence` rows (workspace-scoped, fingerprinted, with provenance)
so research-derived material enters Neosis only through its evidence/provenance pipeline.
"""
import logging
from typing import Any, Iterable, Mapping
from uuid import UUID

from app.core.database import async_session_maker
from app.repositories.research import ResearchRepository
from app.services.research.normalization import ResearchNormalizationService

logger = logging.getLogger(__name__)


async def record_sources_as_evidence(
    *,
    workspace_id: UUID,
    run_id: UUID,
    retriever: str,
    provider: str,
    sources: Iterable[Mapping[str, Any]],
    query: str = "",
) -> int:
    """
    Persist upstream sources as ResearchEvidence for a run. Each source is a mapping with `url` and
    optionally `title`, `content` (or `snippets`), `description` and `score`. Returns how many were stored.
    Individual failures are logged and skipped so a bad source cannot fail the whole run.
    """
    stored = 0
    normalizer = ResearchNormalizationService()
    seen: set[str] = set()

    async with async_session_maker() as session:
        repo = ResearchRepository(session)
        await repo._verify_run_workspace(run_id, workspace_id)

        for source in sources:
            url = source.get("url")
            if not url or url in seen:
                continue
            seen.add(url)

            content = source.get("content")
            if not content:
                snippets = source.get("snippets") or []
                content = "\n\n".join(snippets) if snippets else (source.get("description") or "")
            title = source.get("title") or "Untitled"

            try:
                fingerprint = normalizer.normalize_evidence(
                    content=content, locator=url, retriever=retriever, query=query
                )
                await repo.create_evidence(
                    workspace_id=workspace_id,
                    run_id=run_id,
                    task_id=None,
                    source_id=None,
                    retriever=retriever,
                    query=query,
                    content=content,
                    locator=url,
                    fingerprint=fingerprint,
                    tags=["search_result"],
                    provenance={"title": title, "url": url},
                    source_resolution_status="unresolved_external",
                    provider=provider,
                    provider_reference={"raw_score": source.get("score")},
                )
                stored += 1
            except Exception as exc:
                logger.error("Failed to persist %s evidence for %s: %s", retriever, url, exc)

    return stored
