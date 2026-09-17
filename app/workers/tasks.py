"""
Background job functions executed by the arq worker.

Design rules:
- Every job is IDEMPOTENT: if the same job is enqueued twice (e.g. after a
  worker crash), the second execution detects the source is no longer "pending"
  and exits without side effects.
- Jobs update processing_status on the Source row so the status endpoint
  always reflects real state.
- Jobs use their own DB session (obtained from async_session_maker directly)
  because arq workers run outside the FastAPI request cycle.
- The ctx dict is provided by arq and contains the arq Redis pool; we store
  additional shared resources (DB session factory, object store) in the worker
  startup context via WorkerSettings.on_startup.
"""
import logging
from uuid import UUID
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import async_session_maker
from app.models.source import Source, SourceSnapshot
from app.services.storage import get_object_store
from app.services.parsing import DocumentParser
from app.services.chunking import ChunkingService
from app.repositories.block import BlockRepository
from app.repositories.episodic import EpisodicRepository
from app.schemas.episodic import EpisodicMemoryCreate
from app.schemas.working_memory import WorkingMemoryState

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

async def _get_source_and_snapshot(
    session: AsyncSession, source_id: UUID
) -> tuple[Source | None, SourceSnapshot | None]:
    """Load the source + its first snapshot in a single query."""
    result = await session.execute(
        select(Source).where(Source.source_id == source_id)
    )
    source = result.scalars().first()
    if not source:
        return None, None
    snap_result = await session.execute(
        select(SourceSnapshot).where(SourceSnapshot.source_id == source_id)
        .order_by(SourceSnapshot.created_at)
        .limit(1)
    )
    snapshot = snap_result.scalars().first()
    return source, snapshot


# --------------------------------------------------------------------------- #
# parse_and_chunk_job
# --------------------------------------------------------------------------- #

async def parse_and_chunk_job(
    ctx: dict,
    *,
    source_id: str,
    workspace_id: str,
    owner_id: str,
) -> dict[str, Any]:
    """
    Background job: download from S3, parse with Docling, chunk, bulk-insert blocks.

    Idempotency contract:
    - Reads Source.processing_status on entry.
    - If status is NOT 'pending', this is a duplicate or stale enqueue — exits
      immediately without writing anything.
    - Status transitions: pending -> processing -> completed | failed
    """
    source_uuid = UUID(source_id)

    async with async_session_maker() as session:
        source, snapshot = await _get_source_and_snapshot(session, source_uuid)

        if not source:
            logger.error("parse_and_chunk_job: source %s not found — skipping", source_id)
            return {"status": "not_found", "source_id": source_id}

        # ---- Idempotency guard ---- #
        if source.processing_status != "pending":
            logger.info(
                "parse_and_chunk_job: source %s is already '%s' — skipping (idempotent)",
                source_id, source.processing_status
            )
            return {"status": "skipped", "reason": source.processing_status}

        if not snapshot:
            logger.error("parse_and_chunk_job: no snapshot for source %s — marking failed", source_id)
            source.processing_status = "failed"
            await session.commit()
            return {"status": "failed", "reason": "no_snapshot"}

        # ---- Mark processing ---- #
        source.processing_status = "processing"
        await session.commit()

    # ---- Do the heavy work OUTSIDE the session (may take 30-120s) ---- #
    try:
        storage = get_object_store()
        parser = DocumentParser(storage)
        chunking = ChunkingService()

        doc_dict = await parser.parse_document(snapshot.file_uri)
        blocks_in = chunking.process_docling_output(doc_dict)

        async with async_session_maker() as session:
            block_repo = BlockRepository(session)
            await block_repo.bulk_create_blocks(
                source_id=source_uuid,
                snapshot_id=snapshot.snapshot_id,
                blocks=blocks_in
            )
            # ---- Mark completed ---- #
            result = await session.execute(
                select(Source).where(Source.source_id == source_uuid)
            )
            source_row = result.scalars().first()
            source_row.processing_status = "completed"
            await session.commit()

        logger.info("parse_and_chunk_job: source %s completed (%d blocks)", source_id, len(blocks_in))
        return {"status": "completed", "source_id": source_id, "blocks": len(blocks_in)}

    except Exception as exc:
        logger.exception("parse_and_chunk_job: source %s failed: %s", source_id, exc)
        async with async_session_maker() as session:
            result = await session.execute(
                select(Source).where(Source.source_id == source_uuid)
            )
            source_row = result.scalars().first()
            if source_row:
                source_row.processing_status = "failed"
                await session.commit()
        return {"status": "failed", "source_id": source_id, "error": str(exc)}


# --------------------------------------------------------------------------- #
# compress_episodic_job
# --------------------------------------------------------------------------- #

async def compress_episodic_job(
    ctx: dict,
    *,
    owner_id: str,
    workspace_id: str,
    working_state: dict,
    run_id: str | None = None,
    llm_provider: str = "openai",
    llm_model: str = "gpt-4o-mini",
) -> dict[str, Any]:
    """
    Background job: summarise working memory state into an episodic memory record.

    Idempotency contract:
    - Uses run_id as the natural deduplication key.
    - If an episode with the same run_id already exists, exits without writing.
    - If run_id is None (fire-and-forget callers), the job always executes
      (caller is responsible for not over-enqueuing).
    """
    from app.services.episodic import EpisodicMemoryService

    owner_uuid = UUID(owner_id)
    workspace_uuid = UUID(workspace_id)
    run_uuid = UUID(run_id) if run_id else None

    async with async_session_maker() as session:
        episodic_repo = EpisodicRepository(session)

        # ---- Idempotency guard (run_id-based) ---- #
        if run_uuid is not None:
            existing = await episodic_repo.get_episode_by_run_id(
                workspace_id=workspace_uuid,
                run_id=run_uuid
            )
            if existing:
                logger.info(
                    "compress_episodic_job: episode for run %s already exists — skipping",
                    run_id
                )
                return {"status": "skipped", "reason": "already_exists", "run_id": run_id}

        # ---- Build a lightweight LLM gateway using the configured provider ---- #
        # This is intentionally simple: the gateway is a callable that takes a
        # prompt string and returns a summary string. Full LiteLLM integration
        # comes in Phase 3; for now we wire a direct openai call via arq ctx.
        async def llm_gateway(prompt: str) -> str:
            # ctx["llm_call"] is injected by WorkerSettings.on_startup if available.
            # If not present (testing), raise so the test can mock it.
            llm_fn = ctx.get("llm_call")
            if llm_fn is None:
                raise RuntimeError(
                    "compress_episodic_job: llm_call not in worker context. "
                    "Ensure WorkerSettings.on_startup populates ctx['llm_call']."
                )
            return await llm_fn(prompt, model=llm_model, provider=llm_provider)

        svc = EpisodicMemoryService(
            repository=episodic_repo,
            llm_gateway=llm_gateway,
        )

        try:
            episode = await svc.compress_working_memory(
                owner_id=owner_uuid,
                workspace_id=workspace_uuid,
                working_state=WorkingMemoryState(**working_state),
                run_id=run_uuid,
            )
            logger.info(
                "compress_episodic_job: created episode %s for workspace %s",
                episode.episode_id, workspace_id
            )
            return {
                "status": "completed",
                "episode_id": str(episode.episode_id),
                "workspace_id": workspace_id,
            }
        except Exception as exc:
            logger.exception(
                "compress_episodic_job: failed for workspace %s run %s: %s",
                workspace_id, run_id, exc
            )
            return {"status": "failed", "workspace_id": workspace_id, "error": str(exc)}
