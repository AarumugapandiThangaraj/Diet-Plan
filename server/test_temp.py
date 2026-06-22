import asyncio
from sqlalchemy import text
from database.session import AsyncSessionLocal
import json

async def run():
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("SELECT id, name_en, ingredients_struct FROM \"Twellr_Nutri\".foods WHERE name_en ILIKE '%nasi lemak%'"))
        row = res.fetchone()
        if row:
            print(row.id, row.name_en)
            print(json.dumps(row.ingredients_struct, indent=2))
        else:
            print('Not found')

asyncio.run(run())
