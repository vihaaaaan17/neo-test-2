import asyncio, sys, os
sys.path.insert(0, os.path.abspath("."))
from app.core.database import async_session_maker
from sqlalchemy import select
from app.models.workspace import Workspace

async def main():
    async with async_session_maker() as s:
        res = (await s.execute(select(Workspace).order_by(Workspace.created_at.desc()))).scalars().all()
        print(f"Total workspaces: {len(res)}")
        for w in res:
            print(f"Workspace ID: {w.workspace_id} | Owner: {w.owner_id} | Status: {w.status}")

if __name__ == "__main__":
    asyncio.run(main())
