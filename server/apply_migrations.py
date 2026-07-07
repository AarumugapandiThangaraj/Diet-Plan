import asyncio
import sys
from pathlib import Path
from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parent))

from database.session import engine
from database.base import Base
import database.models
from database.create_tables import create_tables

async def migrate():
    async with engine.begin() as conn:
        try:
            statements = [
                "ALTER TABLE \"Twellr_Nutri\".diet_plans ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;",
                "ALTER TABLE \"Twellr_Nutri\".diet_plans ADD COLUMN IF NOT EXISTS is_dirty BOOLEAN NOT NULL DEFAULT true;",
                "ALTER TABLE \"Twellr_Nutri\".diet_plans ADD COLUMN IF NOT EXISTS generated_by VARCHAR(100);",
                "ALTER TABLE \"Twellr_Nutri\".diet_plans ADD COLUMN IF NOT EXISTS last_modified_by VARCHAR(100);"
            ]
            
            for stmt in statements:
                try:
                    await conn.execute(text(stmt))
                    print(f"Executed: {stmt}")
                except Exception as e:
                    print(f"Failed to execute {stmt}: {e}")
            
        except Exception as e:
            print(f"Error during migration: {e}")
            
    # Now run create_tables to create the new diet_plan_events table
    await create_tables()

if __name__ == "__main__":
    asyncio.run(migrate())
