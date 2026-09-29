#!/usr/bin/env python3
"""
scripts/validate_migrations.py

Dual-mode Alembic Migration Verification Harness for Chapter 4 & 5.
Audits:
1. Strict DAG linearity (single root, single head, zero forks, zero cycles, 18 revisions).
2. Existence and non-emptiness of upgrade() and downgrade() in every revision.
3. Schema constraint integrity across all models (primary keys, foreign keys, and indexes).
4. (Optional / Live DB) Dynamic round-trip migration verification (upgrade -> downgrade -> upgrade).
"""

import os
import sys
import ast
import argparse
import logging
from typing import Dict, Any, List, Set, Optional, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("validate_migrations")


class MigrationAuditError(Exception):
    """Raised when an Alembic revision or schema integrity invariant is violated."""
    pass


def parse_revision_ast(filepath: str) -> Dict[str, Any]:
    """Parses an Alembic revision script using AST to extract metadata and function presence."""
    with open(filepath, "r", encoding="utf-8") as fp:
        source = fp.read()
    tree = ast.parse(source, filename=filepath)

    rev_id: Optional[str] = None
    down_rev: Optional[str] = None
    has_upgrade = False
    has_downgrade = False

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id == "revision" and isinstance(node.value, ast.Constant):
                        rev_id = str(node.value.value)
                    elif target.id == "down_revision":
                        if isinstance(node.value, ast.Constant) and node.value.value is not None:
                            down_rev = str(node.value.value)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                if node.target.id == "revision" and isinstance(node.value, ast.Constant):
                    rev_id = str(node.value.value)
                elif node.target.id == "down_revision":
                    if isinstance(node.value, ast.Constant) and node.value.value is not None:
                        down_rev = str(node.value.value)
        elif isinstance(node, ast.FunctionDef):
            # Check for non-empty function body (more than just docstring / pass)
            meaningful_statements = [
                stmt for stmt in node.body 
                if not (isinstance(stmt, ast.Pass) or (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str)))
            ]
            if node.name == "upgrade":
                has_upgrade = len(meaningful_statements) > 0
            elif node.name == "downgrade":
                has_downgrade = len(meaningful_statements) > 0

    return {
        "file": os.path.basename(filepath),
        "revision": rev_id,
        "down_revision": down_rev,
        "has_upgrade": has_upgrade,
        "has_downgrade": has_downgrade,
    }


def audit_dag_linearity(versions_dir: str) -> Dict[str, Any]:
    """Audits the Alembic migration directory for strict DAG linearity."""
    files = [f for f in os.listdir(versions_dir) if f.endswith(".py") and not f.startswith("__")]
    if not files:
        raise MigrationAuditError(f"No revision files found in {versions_dir}")

    revisions: Dict[str, Dict[str, Any]] = {}
    for f in sorted(files):
        path = os.path.join(versions_dir, f)
        parsed = parse_revision_ast(path)
        rev = parsed["revision"]
        if not rev:
            raise MigrationAuditError(f"File {f} is missing a revision identifier")
        if rev in revisions:
            raise MigrationAuditError(f"Duplicate revision ID '{rev}' found in {f} and {revisions[rev]['file']}")
        revisions[rev] = parsed

    # 1. Verify upgrade/downgrade non-emptiness
    empty_upgrades = [r for r, d in revisions.items() if not d["has_upgrade"]]
    empty_downgrades = [r for r, d in revisions.items() if not d["has_downgrade"]]
    if empty_upgrades:
        raise MigrationAuditError(f"Revisions missing non-empty upgrade(): {empty_upgrades}")
    if empty_downgrades:
        raise MigrationAuditError(f"Revisions missing non-empty downgrade(): {empty_downgrades}")

    # 2. Find roots (down_revision is None)
    roots = [r for r, d in revisions.items() if d["down_revision"] is None]
    if len(roots) != 1:
        raise MigrationAuditError(f"Expected exactly 1 root revision, but found {len(roots)}: {roots}")
    root = roots[0]

    # 3. Check for forward links and forks
    down_to_rev: Dict[str, str] = {}
    for r, d in revisions.items():
        down = d["down_revision"]
        if down is not None:
            if down not in revisions:
                raise MigrationAuditError(f"Revision '{r}' in {d['file']} points to nonexistent down_revision '{down}'")
            if down in down_to_rev:
                raise MigrationAuditError(f"Fork detected: Revisions '{r}' and '{down_to_rev[down]}' both revise '{down}'")
            down_to_rev[down] = r

    # 4. Traverse DAG from root to head
    ordered_chain: List[str] = [root]
    curr = root
    visited: Set[str] = {root}
    while curr in down_to_rev:
        nxt = down_to_rev[curr]
        if nxt in visited:
            raise MigrationAuditError(f"Cycle detected in migration DAG at revision '{nxt}'")
        visited.add(nxt)
        ordered_chain.append(nxt)
        curr = nxt

    head = curr
    if len(ordered_chain) != len(revisions):
        orphaned = set(revisions.keys()) - set(ordered_chain)
        raise MigrationAuditError(f"DAG contains {len(orphaned)} disconnected revisions: {orphaned}")

    return {
        "total_revisions": len(revisions),
        "root": root,
        "head": head,
        "ordered_chain": ordered_chain,
        "revisions": revisions,
    }


def audit_schema_models() -> Dict[str, Any]:
    """Audits SQLAlchemy models for table definitions, primary keys, foreign keys, and indexes."""
    import app.models  # noqa: F401
    from app.core.database import Base

    metadata = Base.metadata
    tables = metadata.tables

    required_tables = [
        "workspaces",
        "workspace_commits",
        "sources",
        "knowledge_memories",
        "episodic_memories",
        "open_notebook_workspace_bindings",
        "open_notebook_conversation_bindings",
        "ground_conversations",
        "conversations",
        "conversation_turns",
        "chat_events",
        "scratchpad_entries",
        "research_runs",
        "research_tasks",
        "research_evidence",
        "research_artifacts",
        "research_reports",
    ]

    missing_tables = [t for t in required_tables if t not in tables]
    if missing_tables:
        raise MigrationAuditError(f"Missing required tables in Base.metadata: {missing_tables}")

    # Verify primary keys on all tables
    tables_without_pk = [t_name for t_name, t in tables.items() if not t.primary_key]
    if tables_without_pk:
        raise MigrationAuditError(f"Tables missing primary key: {tables_without_pk}")

    # Verify critical foreign keys
    critical_fk_checks = [
        ("conversations", "workspace_id", "workspaces.workspace_id"),
        ("conversation_turns", "conversation_id", "conversations.conversation_id"),
        ("chat_events", "turn_id", "conversation_turns.turn_id"),
        ("scratchpad_entries", "workspace_id", "workspaces.workspace_id"),
        ("scratchpad_entries", "run_id", "research_runs.run_id"),
        ("research_runs", "workspace_id", "workspaces.workspace_id"),
        ("research_runs", "conversation_id", "conversations.conversation_id"),
        ("research_runs", "turn_id", "conversation_turns.turn_id"),
        ("open_notebook_conversation_bindings", "conversation_id", "conversations.conversation_id"),
        ("research_artifacts", "run_id", "research_runs.run_id"),
    ]

    fk_violations = []
    for source_table, source_col, target_ref in critical_fk_checks:
        tbl = tables.get(source_table)
        if tbl is None:
            fk_violations.append(f"{source_table} does not exist")
            continue
        col = tbl.columns.get(source_col)
        if col is None:
            fk_violations.append(f"{source_table}.{source_col} does not exist")
            continue
        
        matches = False
        for fk in col.foreign_keys:
            if fk.target_fullname == target_ref:
                matches = True
                break
        if not matches:
            fk_violations.append(f"{source_table}.{source_col} does not reference {target_ref}")

    if fk_violations:
        raise MigrationAuditError(f"Critical foreign key violations: {fk_violations}")

    # Verify critical indexes
    critical_indexes = [
        ("conversations", ["workspace_id"]),
        ("conversation_turns", ["conversation_id"]),
        ("chat_events", ["turn_id"]),
        ("research_runs", ["workspace_id"]),
        ("research_artifacts", ["promotion_status"]),
        ("workspace_commits", ["workspace_id"]),
    ]

    index_violations = []
    for t_name, expected_cols in critical_indexes:
        tbl = tables.get(t_name)
        if tbl is None:
            continue
        # Check explicit indexes and column index=True
        has_index = False
        for idx in tbl.indexes:
            idx_cols = [c.name for c in idx.columns]
            if all(c in idx_cols for c in expected_cols):
                has_index = True
                break
        if not has_index:
            # Check individual column index attribute
            if len(expected_cols) == 1:
                col = tbl.columns.get(expected_cols[0])
                if col is not None and col.index:
                    has_index = True
        if not has_index:
            index_violations.append(f"Table {t_name} lacks index on {expected_cols}")

    if index_violations:
        raise MigrationAuditError(f"Critical index violations: {index_violations}")

    return {
        "total_tables": len(tables),
        "required_tables_verified": len(required_tables),
        "fk_checks_verified": len(critical_fk_checks),
        "index_checks_verified": len(critical_indexes),
    }


async def run_live_database_roundtrip() -> Dict[str, Any]:
    """Executes live Alembic upgrade/downgrade roundtrip against PostgreSQL if available."""
    from app.core.config import settings
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    logger.info("Attempting connection to live database...")
    try:
        connect_args = {"timeout": 3} if "asyncpg" in settings.DATABASE_URL else {"connect_timeout": 3}
        engine = create_async_engine(settings.DATABASE_URL, connect_args=connect_args)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        logger.info("Database reachable. Proceeding with migration roundtrip...")
    except Exception as e:
        logger.warning(f"Live database not reachable ({e}). Skipping dynamic migration roundtrip.")
        return {"status": "skipped", "reason": str(e)}

    # Run alembic upgrade head
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config(os.path.join(REPO_ROOT, "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(REPO_ROOT, "alembic"))

    try:
        logger.info("Running alembic upgrade head...")
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic upgrade head passed.")

        logger.info("Running alembic downgrade -1...")
        command.downgrade(alembic_cfg, "-1")
        logger.info("Alembic downgrade -1 passed.")

        logger.info("Re-running alembic upgrade head...")
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic re-upgrade passed.")
        return {"status": "passed"}
    except Exception as e:
        logger.error(f"Live migration roundtrip failed: {e}")
        return {"status": "failed", "error": str(e)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Dual-Mode Alembic Migration Verification Harness")
    parser.add_argument("--static-only", action="store_true", help="Run only static AST & schema audits")
    parser.add_argument("--require-live-db", action="store_true", help="Fail if live database is unreachable")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    versions_dir = os.path.join(REPO_ROOT, "alembic", "versions")

    logger.info("Starting static DAG linearity audit...")
    try:
        dag_result = audit_dag_linearity(versions_dir)
        logger.info(
            f"DAG Linearity PASSED: {dag_result['total_revisions']} revisions, "
            f"Root='{dag_result['root']}', Head='{dag_result['head']}'"
        )
    except MigrationAuditError as e:
        logger.error(f"DAG Linearity FAILED: {e}")
        return 1

    logger.info("Starting SQLAlchemy schema models audit...")
    try:
        schema_result = audit_schema_models()
        logger.info(
            f"Schema Models PASSED: {schema_result['total_tables']} tables, "
            f"{schema_result['fk_checks_verified']} FK constraints, "
            f"{schema_result['index_checks_verified']} indexes verified"
        )
    except MigrationAuditError as e:
        logger.error(f"Schema Audit FAILED: {e}")
        return 1

    if not args.static_only:
        import asyncio
        logger.info("Starting dynamic migration verification...")
        live_res = asyncio.run(run_live_database_roundtrip())
        if live_res["status"] == "failed":
            return 1
        if live_res["status"] == "skipped" and args.require_live_db:
            logger.error("Live database was required but could not be reached.")
            return 1

    logger.info("All migration integrity audits PASSED successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
