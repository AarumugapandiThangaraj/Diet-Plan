import asyncio
import asyncpg
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))
from config.config import build_database_url

async def main():
    url = build_database_url()
    conn = await asyncpg.connect(url)
    
    # Query check constraint definition
    query = """
    SELECT pg_get_constraintdef(c.oid) AS consrc
    FROM pg_constraint c
    JOIN pg_namespace n ON n.oid = c.connamespace
    WHERE c.conname = 'chk_activity';
    """
    res = await conn.fetch(query)
    for r in res:
        print(r['consrc'])
        
    await conn.close()

asyncio.run(main())
