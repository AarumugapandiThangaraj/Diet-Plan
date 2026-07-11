import asyncio
import asyncpg
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))
from config.settings import settings

async def main():
    url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    print(f"Connecting to {url}")
    conn = await asyncpg.connect(url)
    
    print("\n--- Schemas ---")
    schemas = await conn.fetch("SELECT schema_name FROM information_schema.schemata;")
    for s in schemas:
        print(s['schema_name'])
        
    print("\n--- Tables in 'Twellr_Nutri' ---")
    try:
        tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'Twellr_Nutri';")
        for t in tables:
            print(t['table_name'])
    except Exception as e:
        print(f"Error: {e}")
        
    print("\n--- Tables in 'wellness_platform' ---")
    try:
        tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'wellness_platform';")
        for t in tables:
            print(t['table_name'])
    except Exception as e:
        print(f"Error: {e}")
        
    print("\n--- Tables in 'public' ---")
    try:
        tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        for t in tables:
            print(t['table_name'])
    except Exception as e:
        print(f"Error: {e}")

    await conn.close()

asyncio.run(main())
