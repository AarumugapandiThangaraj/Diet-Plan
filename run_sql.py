import asyncio
import asyncpg
import sys
from pathlib import Path
import os

# Get DB URL from settings
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))
from server.config.settings import settings

async def run_sql_file(file_path: str):
    sql_path = Path(file_path)
    if not sql_path.exists():
        print(f"Error: File {file_path} not found.")
        return
        
    sql_text = sql_path.read_text(encoding="utf-8")
    
    # Extract connection info from URL
    # format: postgresql+asyncpg://user:pass@host:port/dbname
    url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    print(f"Connecting to {url}...")
    try:
        conn = await asyncpg.connect(url)
        # asyncpg conn.execute can run multiple statements!
        await conn.execute(sql_text)
        await conn.close()
        print("Successfully executed SQL script.")
    except Exception as e:
        print(f"Failed to execute SQL: {repr(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_sql.py <path_to_sql_file>")
        sys.exit(1)
    asyncio.run(run_sql_file(sys.argv[1]))
