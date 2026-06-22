import asyncio
from sqlalchemy import text
from database.session import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as session:
        stmt = text("""
            SELECT name_en, client_food_id 
            FROM "Twellr_Nutri".foods
            WHERE client_food_id LIKE 'FOOD_SEA_BT_%' OR client_food_id LIKE 'FOOD_SEA_MISC_%'
        """)
        res = await session.execute(stmt)
        print("Foods found:")
        for row in res.fetchall():
            print(f"  {row[0]} ({row[1]})")

asyncio.run(check())
