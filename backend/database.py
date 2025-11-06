from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .config import settings

# Use the async database URL
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=True,
    connect_args={"check_same_thread": False}
)

# Create async session maker
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Async session dependency
async def get_session():
    async with async_session_maker() as session:
        yield session
