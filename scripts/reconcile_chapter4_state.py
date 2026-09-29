#!/usr/bin/env python3
"""
scripts/reconcile_chapter4_state.py

Historical State Reconciliation Engine for Chapter 4.
Reconciles pre-Chapter 4 and Phase 1-4 state into the canonical Chapter 4 data model:
1. Reconciles legacy GroundConversation records to canonical Conversation records, preserving UUIDs.
2. Reconciles OpenNotebookConversationBinding records to ensure valid canonical Conversation FKs.
3. Quarantines legacy Ground KnowledgeMemory records in place with provenance metadata without deleting data.
4. Links unlinked historical ResearchRun records to conversation turns when references exist.
5. Emits structured JSON reconciliation audit report.
6. Strictly idempotent: running multiple times produces 0 additional mutations.
"""

import os
import sys
import json
import logging
import argparse
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set
from uuid import UUID

# Ensure repository root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import app.models  # noqa: F401
from app.models.conversation import GroundConversation, Conversation, ConversationTurn
from app.models.open_notebook_binding import OpenNotebookConversationBinding
from app.models.knowledge import KnowledgeMemory
from app.models.research import ResearchRun

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("reconcile_chapter4_state")


class StateReconciliationEngine:
    """
    Idempotent engine for reconciling legacy pre-Chapter 4 state to canonical schemas.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def reconcile(
        self,
        workspace_id: Optional[UUID] = None,
        apply: bool = False
    ) -> Dict[str, Any]:
        """
        Executes the full reconciliation process.
        If apply is False (dry-run), inspects state and plans mutations without committing.
        If apply is True, applies mutations atomically and commits.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        counts = {
            "ground_conversations_processed": 0,
            "canonical_conversations_created": 0,
            "open_notebook_bindings_reconciled": 0,
            "legacy_ground_memories_quarantined": 0,
            "research_runs_linked": 0,
            "skipped": 0,
            "errors": 0,
        }
        details: List[str] = []

        try:
            # 1. Reconcile Ground Conversations to Canonical Conversations
            newly_created_conv_ids = await self._reconcile_ground_conversations(
                workspace_id=workspace_id,
                counts=counts,
                details=details,
                now_iso=now_iso
            )

            # 2. Reconcile Open Notebook Conversation Bindings
            await self._reconcile_open_notebook_bindings(
                workspace_id=workspace_id,
                newly_created_conv_ids=newly_created_conv_ids,
                counts=counts,
                details=details,
                now_iso=now_iso
            )

            # 3. Quarantine Legacy Ground KnowledgeMemory Records In-Place
            await self._quarantine_legacy_ground_memories(
                workspace_id=workspace_id,
                counts=counts,
                details=details,
                now_iso=now_iso
            )

            # 4. Link Historical Research Runs
            await self._link_historical_research_runs(
                workspace_id=workspace_id,
                counts=counts,
                details=details
            )

            if apply:
                await self.session.commit()
                mode = "apply"
                logger.info("Reconciliation changes committed successfully.")
            else:
                await self.session.rollback()
                mode = "dry-run"
                logger.info("Dry-run complete. All changes rolled back.")

        except Exception as e:
            await self.session.rollback()
            counts["errors"] += 1
            details.append(f"Fatal reconciliation error: {str(e)}")
            logger.error(f"Reconciliation error: {e}", exc_info=True)
            mode = "failed"

        return {
            "mode": mode,
            "timestamp": now_iso,
            "workspace_id": str(workspace_id) if workspace_id else "all",
            "counts": counts,
            "details": details,
        }

    async def _reconcile_ground_conversations(
        self,
        workspace_id: Optional[UUID],
        counts: Dict[str, int],
        details: List[str],
        now_iso: str
    ) -> Set[UUID]:
        """Finds legacy GroundConversation records lacking a canonical Conversation record."""
        stmt = select(GroundConversation)
        if workspace_id:
            stmt = stmt.where(GroundConversation.workspace_id == workspace_id)
        res = await self.session.execute(stmt)
        ground_convs = list(res.scalars().all())
        created_conv_ids: Set[UUID] = set()

        for gc in ground_convs:
            counts["ground_conversations_processed"] += 1
            # Check if canonical Conversation already exists with matching conversation_id
            c_stmt = select(Conversation).where(Conversation.conversation_id == gc.conversation_id)
            c_res = await self.session.execute(c_stmt)
            existing_c = c_res.scalars().first()

            if existing_c is not None:
                counts["skipped"] += 1
                continue

            # Create canonical Conversation with preserved UUID
            canonical = Conversation(
                conversation_id=gc.conversation_id,
                workspace_id=gc.workspace_id,
                owner_id=gc.owner_id,
                title="Reconciled Ground Conversation",
                status="active",
                last_turn_sequence=0,
                metadata_={
                    "legacy_origin": "ground_conversation",
                    "reconciled_at": now_iso
                },
                created_at=gc.created_at,
                updated_at=gc.updated_at or gc.created_at
            )
            self.session.add(canonical)
            created_conv_ids.add(gc.conversation_id)
            counts["canonical_conversations_created"] += 1
            details.append(f"Created canonical Conversation for GroundConversation {gc.conversation_id}")

        return created_conv_ids

    async def _reconcile_open_notebook_bindings(
        self,
        workspace_id: Optional[UUID],
        newly_created_conv_ids: Set[UUID],
        counts: Dict[str, int],
        details: List[str],
        now_iso: str
    ) -> None:
        """Ensures all OpenNotebookConversationBinding records reference a valid canonical Conversation."""
        stmt = select(OpenNotebookConversationBinding)
        res = await self.session.execute(stmt)
        bindings = list(res.scalars().all())

        for binding in bindings:
            if binding.conversation_id in newly_created_conv_ids:
                counts["open_notebook_bindings_reconciled"] += 1
                details.append(f"Reconciled OpenNotebookConversationBinding {binding.conversation_id} to canonical Conversation")
                continue

            # Check if canonical conversation exists
            c_stmt = select(Conversation).where(Conversation.conversation_id == binding.conversation_id)
            if workspace_id:
                c_stmt = c_stmt.where(Conversation.workspace_id == workspace_id)
            c_res = await self.session.execute(c_stmt)
            existing_c = c_res.scalars().first()

            if existing_c is not None:
                counts["skipped"] += 1
                continue

            # Check if matching GroundConversation exists to construct the missing canonical Conversation
            gc_stmt = select(GroundConversation).where(GroundConversation.conversation_id == binding.conversation_id)
            gc_res = await self.session.execute(gc_stmt)
            gc = gc_res.scalars().first()

            if gc is not None:
                canonical = Conversation(
                    conversation_id=gc.conversation_id,
                    workspace_id=gc.workspace_id,
                    owner_id=gc.owner_id,
                    title="Reconciled Open Notebook Conversation",
                    status="active",
                    last_turn_sequence=0,
                    metadata_={
                        "legacy_origin": "open_notebook_binding",
                        "reconciled_at": now_iso
                    },
                    created_at=gc.created_at,
                    updated_at=gc.updated_at or gc.created_at
                )
                self.session.add(canonical)
                counts["canonical_conversations_created"] += 1
                counts["open_notebook_bindings_reconciled"] += 1
                details.append(f"Reconciled OpenNotebookConversationBinding {binding.conversation_id} via GroundConversation")
            else:
                counts["skipped"] += 1
                details.append(f"Binding {binding.conversation_id} has no matching GroundConversation; skipping")

    async def _quarantine_legacy_ground_memories(
        self,
        workspace_id: Optional[UUID],
        counts: Dict[str, int],
        details: List[str],
        now_iso: str
    ) -> None:
        """
        Quarantines legacy Ground KnowledgeMemory records in place.
        Historical data is NEVER deleted. Provenance is updated with:
        {"legacy_origin": "ground_mode_pre_ch4", "quarantined_from_ground": True, "reconciled_at": now_iso}
        """
        stmt = select(KnowledgeMemory)
        if workspace_id:
            stmt = stmt.where(KnowledgeMemory.workspace_id == workspace_id)
        res = await self.session.execute(stmt)
        memories = list(res.scalars().all())

        legacy_types = {"ground_mode", "conversation_turn", "ground_evidence", "ground"}

        for km in memories:
            prov = dict(km.provenance or {})
            is_legacy = (
                km.knowledge_type in legacy_types or
                prov.get("origin") == "ground_mode" or
                prov.get("mode") == "ground" or
                prov.get("source") == "ground_turn"
            )

            if not is_legacy:
                counts["skipped"] += 1
                continue

            # Idempotency check: already quarantined?
            if prov.get("quarantined_from_ground") is True:
                counts["skipped"] += 1
                continue

            # In-place quarantine: update provenance & status without deletion
            prov["legacy_origin"] = "ground_mode_pre_ch4"
            prov["quarantined_from_ground"] = True
            prov["reconciled_at"] = now_iso

            km.provenance = prov
            km.status = "quarantined"
            counts["legacy_ground_memories_quarantined"] += 1
            details.append(f"Quarantined in-place legacy Ground KnowledgeMemory {km.knowledge_id}")

    async def _link_historical_research_runs(
        self,
        workspace_id: Optional[UUID],
        counts: Dict[str, int],
        details: List[str]
    ) -> None:
        """
        Links unlinked historical ResearchRun records to conversation turns when references exist.
        """
        stmt = select(ResearchRun).where(
            or_(ResearchRun.conversation_id.is_(None), ResearchRun.turn_id.is_(None))
        )
        if workspace_id:
            stmt = stmt.where(ResearchRun.workspace_id == workspace_id)
        res = await self.session.execute(stmt)
        unlinked_runs = list(res.scalars().all())

        for run in unlinked_runs:
            # Check if there is a ConversationTurn referencing this run_id
            turn_stmt = select(ConversationTurn).where(
                ConversationTurn.research_run_id == run.run_id
            )
            turn_res = await self.session.execute(turn_stmt)
            matching_turn = turn_res.scalars().first()

            if matching_turn is not None:
                run.turn_id = matching_turn.turn_id
                run.conversation_id = matching_turn.conversation_id
                counts["research_runs_linked"] += 1
                details.append(f"Linked ResearchRun {run.run_id} to Turn {matching_turn.turn_id}")
            else:
                counts["skipped"] += 1


async def run_cli(args: argparse.Namespace) -> int:
    from app.core.config import settings

    db_url = args.database_url or settings.DATABASE_URL
    connect_args = {"timeout": 5} if "asyncpg" in db_url else {"connect_timeout": 5}
    engine = create_async_engine(db_url, connect_args=connect_args)

    target_ws = None
    if args.workspace_id:
        try:
            target_ws = UUID(args.workspace_id)
        except ValueError:
            logger.error(f"Invalid workspace_id UUID: {args.workspace_id}")
            return 1

    async with AsyncSession(engine) as session:
        reconciler = StateReconciliationEngine(session)
        result = await reconciler.reconcile(
            workspace_id=target_ws,
            apply=args.apply
        )

    await engine.dispose()

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"=== Reconciliation Report ({result['mode'].upper()}) ===")
        print(f"Timestamp: {result['timestamp']}")
        print(f"Workspace: {result['workspace_id']}")
        print("Counts:")
        for k, v in result["counts"].items():
            print(f"  {k}: {v}")
        if result["details"]:
            print(f"Details ({len(result['details'])} items):")
            for d in result["details"][:20]:
                print(f"  - {d}")
            if len(result["details"]) > 20:
                print(f"  ... and {len(result['details']) - 20} more")

    return 0 if result["counts"]["errors"] == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Chapter 4 Historical State Reconciliation Engine")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Audit and plan reconciliation without committing")
    group.add_argument("--apply", action="store_true", help="Apply reconciliation mutations atomically to database")
    
    parser.add_argument("--workspace-id", type=str, default=None, help="Filter to specific workspace UUID")
    parser.add_argument("--format", choices=["json", "text"], default="json", help="Output format")
    parser.add_argument("--database-url", type=str, default=None, help="Override database URL")
    
    args = parser.parse_args()
    return asyncio.run(run_cli(args))


if __name__ == "__main__":
    sys.exit(main())
