from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config.settings import settings

DATABASE_URL = settings.database_url
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)



engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

from sqlalchemy.exc import SQLAlchemyError
from exceptions.service import DatabaseException

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            try:
                await session.commit()
            except SQLAlchemyError as ex:
                await session.rollback()
                raise DatabaseException("Transaction commit failed") from ex
        except SQLAlchemyError as ex:
            try:
                await session.rollback()
            except Exception:
                pass
            raise DatabaseException("Database session transaction encountered an error") from ex

