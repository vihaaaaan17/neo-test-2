from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Production-grade connection pool settings.
# Supabase free tier allows 60 direct connections.
# pool_size + max_overflow = 50 — leaves 10 for admin tools and Alembic.
# pool_pre_ping detects dead connections before using them (guards against
# Supabase killing idle connections after ~60s).
# pool_recycle=1800 recycles connections every 30min as a secondary guard.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG_SQL,
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with async_session_maker() as session:
        yield session
