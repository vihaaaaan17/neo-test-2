"""
Read-only preflight for the Chapter 5 research-engine cutover (ODR-only).

Reports what the cutover will touch in whatever database it is pointed at:
  * workspaces grouped by research_engine
  * research_runs grouped by (engine, status)
  * non-terminal research_runs whose engine is not 'open_deep_research'

It never writes. Findings are informational; the script exits non-zero only when it
cannot connect or query.

Usage (dev):
    python scripts/preflight_engine_cutover.py

Usage (production) -- point DATABASE_URL at the production database (read-only credentials
are recommended) and have a human review the output BEFORE deploying the engine-cutover
migration. Do not assume production matches dev:
    DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/neosislm python scripts/preflight_engine_cutover.py
"""
import asyncio
import os
import sys

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import create_async_engine

TERMINAL_STATES = ("completed", "partial", "failed", "cancelled", "aborted_by_timeline_fence")
SUPPORTED_ENGINE = "open_deep_research"


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    from dotenv import load_dotenv

    load_dotenv(".env")
    url = os.environ.get("DATABASE_URL")
    if not url:
        from app.core.config import settings

        url = settings.DATABASE_URL
    return url


async def main() -> int:
    url = _database_url()
    engine = create_async_engine(url)
    attention = []
    try:
        async with engine.connect() as conn:
            # Make the session read-only so this script can never write.
            await conn.execute(text("SET TRANSACTION READ ONLY"))

            print("== workspaces by research_engine ==")
            rows = (await conn.execute(text(
                "SELECT research_engine, count(*) FROM workspaces GROUP BY 1 ORDER BY 2 DESC"
            ))).all()
            for engine_name, count in rows:
                print(f"  {engine_name!r}: {count}")
                if engine_name == "legacy":
                    print(f"      -> will be migrated to '{SUPPORTED_ENGINE}' by the cutover migration")
                elif engine_name != SUPPORTED_ENGINE:
                    attention.append(
                        f"{count} workspace(s) on '{engine_name}': the migration rewrites only 'legacy', "
                        "so these would be left on an unsupported engine"
                    )

            print("\n== research_runs by (engine, status) ==")
            rows = (await conn.execute(text(
                "SELECT engine, status, count(*) FROM research_runs GROUP BY 1, 2 ORDER BY 1, 2"
            ))).all()
            for engine_name, status, count in rows:
                print(f"  {engine_name!r:24} {status!r:30} {count}")

            print("\n== non-terminal runs on engines other than 'open_deep_research' ==")
            rows = (await conn.execute(
                text(
                    "SELECT run_id, workspace_id, engine, status, updated_at FROM research_runs "
                    "WHERE engine <> :supported AND status NOT IN :terminal ORDER BY updated_at"
                ).bindparams(bindparam("terminal", expanding=True)),
                {"supported": SUPPORTED_ENGINE, "terminal": list(TERMINAL_STATES)},
            )).all()
            if not rows:
                print("  none")
            for run_id, workspace_id, engine_name, status, updated_at in rows:
                print(f"  run={run_id} workspace={workspace_id} engine={engine_name!r} status={status!r} updated_at={updated_at}")
            if rows:
                attention.append(
                    f"{len(rows)} non-terminal run(s) on removed/unsupported engines; "
                    "let existing reconciliation handle them (or fail them explicitly) before deleting the legacy engine"
                )
    except Exception as exc:  # connection/query errors are the only non-zero exit
        print(f"PREFLIGHT ERROR: could not inspect database: {exc}", file=sys.stderr)
        return 2
    finally:
        await engine.dispose()

    print("\n== summary ==")
    if attention:
        print("ATTENTION:")
        for item in attention:
            print(f"  - {item}")
    else:
        print("PASS: nothing needs attention before the cutover.")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, os.getcwd())
    sys.exit(asyncio.run(main()))
