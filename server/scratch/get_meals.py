import asyncio
from database.session import AsyncSessionLocal
from sqlalchemy import select
from database.models import Meal

async def run():
    async with AsyncSessionLocal() as session:
        stmt = select(Meal).limit(10)
        res = await session.execute(stmt)
        meals = res.scalars().all()
        for m in meals:
            print(f"ID: {m.id}, Name: {m.recipe_name}, Time: {m.time}")

if __name__ == "__main__":
    asyncio.run(run())
