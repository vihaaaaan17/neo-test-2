import asyncio
from uuid import UUID
from app.core.database import async_session_maker
from app.models.workspace import Workspace
from app.models.conversation import Conversation
from sqlalchemy import select

async def main():
    target_user = UUID("00000000-0000-0000-0000-000000000001")
    async with async_session_maker() as session:
        result = await session.execute(select(Workspace).where(Workspace.owner_id == target_user))
        workspaces = result.scalars().all()
        print(f"Workspaces for user {target_user}: {len(workspaces)}")
        for w in workspaces:
            print(f"\nWorkspace: id={w.workspace_id}, status={w.status}, created_at={w.created_at}")
            convs = (await session.execute(select(Conversation).where(Conversation.workspace_id == w.workspace_id))).scalars().all()
            print(f"  Conversations ({len(convs)}):")
            for c in convs:
                print(f"   - id={c.conversation_id}, title={c.title}")

if __name__ == "__main__":
    asyncio.run(main())
