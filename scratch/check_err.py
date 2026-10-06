import sys, os, uuid, asyncio
sys.path.insert(0, os.path.abspath("."))
from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.conversation import ConversationTurn
from app.models.research import ResearchRun

async def main():
    async with async_session_maker() as s:
        turn = await s.get(ConversationTurn, uuid.UUID("02b9a07c-23a8-401b-bde0-ea7823b213b4"))
        if turn:
            print("Turn error_message:", turn.error_message)
            print("Turn error_code:", turn.error_code)
        from app.models.research import ResearchEvent
        from app.models.conversation import ChatEvent
        events = (await s.execute(select(ResearchEvent).where(ResearchEvent.run_id == uuid.UUID("0b9c9bce-abeb-42cc-9cfa-2e916df212c7")))).scalars().all()
        print("ResearchEvents count:", len(events))
        for e in events:
            print("  RE:", e.event_type, e.payload)
        
        c_events = (await s.execute(select(ChatEvent).where(ChatEvent.turn_id == uuid.UUID("02b9a07c-23a8-401b-bde0-ea7823b213b4")))).scalars().all()
        print("ChatEvents count:", len(c_events))
        for ce in c_events:
            print("  CE:", ce.sequence, ce.event_type, ce.payload)

if __name__ == "__main__":
    asyncio.run(main())
0