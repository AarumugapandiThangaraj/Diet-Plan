import asyncio
import asyncpg
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))
from config.config import build_database_url

async def main():
    url = build_database_url()
    conn = await asyncpg.connect(url)
    users = await conn.fetch("SELECT id FROM wellness_platform.users LIMIT 5;")
    for u in users:
        print(u['id'])
    await conn.close()

asyncio.run(main())
