import asyncio
import asyncpg
import sys
import os
from urllib.parse import quote_plus

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))
from config.config import build_database_url

async def main():
    url = build_database_url()
    print(f"Connecting to AWS RDS: {url.split('@')[1]}")
    conn = await asyncpg.connect(url)
    
    print("\n--- Schemas on AWS RDS ---")
    schemas = await conn.fetch("SELECT schema_name FROM information_schema.schemata;")
    for s in schemas:
        print(s['schema_name'])
        
    print("\n--- Tables in 'Twellr_Nutri' on AWS ---")
    try:
        tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'Twellr_Nutri';")
        for t in tables:
            print(t['table_name'])
    except Exception as e:
        print(f"Error: {e}")
        
    print("\n--- Tables in 'wellness_platform' on AWS ---")
    try:
        tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'wellness_platform';")
        for t in tables:
            print(t['table_name'])
    except Exception as e:
        print(f"Error: {e}")

    await conn.close()

asyncio.run(main())
