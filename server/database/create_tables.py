import asyncio
import sys
from pathlib import Path

# Add backend directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from database.session import engine
from database.base import Base
import database.models  # Ensure models are imported

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables initialized successfully.")

if __name__ == "__main__":
    asyncio.run(create_tables())
