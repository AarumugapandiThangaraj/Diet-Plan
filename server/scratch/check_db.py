import asyncio
from database.session import AsyncSessionLocal
from database.models.catalog import Food, Meal
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as session:
        # Check foods
        res = await session.execute(select(Food.id, Food.food_name).limit(10))
        print("Foods in DB:")
        for r in res:
            print(f"  id={r.id} (type={type(r.id)}), name={r.food_name}")
            
        # Check meals
        res_meal = await session.execute(select(Meal.id, Meal.recipe_name).limit(5))
        print("\nMeals in DB:")
        for r in res_meal:
            print(f"  id={r.id} (type={type(r.id)}), name={r.recipe_name}")

if __name__ == "__main__":
    asyncio.run(main())
