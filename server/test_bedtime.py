import asyncio
from sqlalchemy import text
from database.session import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as session:
        stmt = text("""
            SELECT m.name_en, m.client_meal_id, s.code
            FROM "Twellr_Nutri".meals m
            JOIN "Twellr_Nutri".meal_sessions s ON s.id = m.meal_session_id
            WHERE m.client_meal_id LIKE 'MEAL_SEA_BT%' OR m.client_meal_id LIKE 'MEAL_SEA_B_%'
        """)
        res = await session.execute(stmt)
        print('Southeast Asian BT meals:')
        for row in res.fetchall():
            print(f"  {row[0]} ({row[1]}) -> session: {row[2]}")

asyncio.run(check())
