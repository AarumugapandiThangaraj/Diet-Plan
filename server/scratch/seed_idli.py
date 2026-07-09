import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models.catalog import Meal, Food, MealFood, Cuisine, MealSession
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(db_url, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def seed_data():
    async with AsyncSessionLocal() as session:
        # 1. Ensure Foods exist
        foods_data = [
            {"food_name": "Idli"},
            {"food_name": "Sambar"},
            {"food_name": "Chuttney"}
        ]
        
        food_objs = {}
        for fd in foods_data:
            stmt = select(Food).where(Food.food_name == fd["food_name"])
            res = await session.execute(stmt)
            food = res.scalars().first()
            if not food:
                food = Food(
                    food_name=fd["food_name"]
                )
                session.add(food)
                await session.flush()
            food_objs[fd["food_name"]] = food
            
        # 2. Get south_indian cuisine and breakfast session
        stmt = select(Cuisine).where(Cuisine.code == "south_indian")
        res = await session.execute(stmt)
        cuisine = res.scalars().first()
        
        stmt = select(MealSession).where(MealSession.code == "breakfast")
        res = await session.execute(stmt)
        breakfast = res.scalars().first()
        
        # 3. Create Meals
        meals_data = [
            {"name": "Idli + Sambar", "foods": [("Idli", 2.0), ("Sambar", 1.0)]},
            {"name": "Idli + Chuttney", "foods": [("Idli", 2.0), ("Chuttney", 1.0)]}
        ]
        
        for md in meals_data:
            stmt = select(Meal).where(Meal.name_en == md["name"])
            res = await session.execute(stmt)
            meal = res.scalars().first()
            if not meal:
                meal = Meal(
                    name_en=md["name"],
                    cuisine_id=cuisine.id,
                    meal_session_id=breakfast.id,
                    is_active=True
                )
                session.add(meal)
                await session.flush()
                
                # Add MealFoods
                for fname, qty in md["foods"]:
                    mf = MealFood(
                        meal_id=meal.id,
                        food_id=food_objs[fname].id,
                        serving_size=qty
                    )
                    session.add(mf)
        
        await session.commit()
        print("Successfully seeded Idli + Sambar and Idli + Chuttney!")

if __name__ == "__main__":
    asyncio.run(seed_data())
