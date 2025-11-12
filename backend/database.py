from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .config import settings

# Create async engine for MariaDB
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=True,
    pool_pre_ping=True,      # Verify connections before using them
    pool_recycle=3600,       # Recycle connections after 1 hour
    pool_size=10,            # Maximum number of connections in the pool
    max_overflow=20,         # Maximum overflow connections beyond pool_size
)

# Create async session maker
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Async session dependency for FastAPI
async def get_session():
    async with async_session_maker() as session:
        yield session


# Initialize database tables
async def create_db_and_tables():
    """Create all database tables. Run this once during initialization."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


# Close database connections on shutdown
async def close_db():
    """Close all database connections. Call this on app shutdown."""
    await engine.dispose()
