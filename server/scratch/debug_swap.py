import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.session import AsyncSessionLocal
from database.models.catalog import Food, Meal, MealFood, MealSession, Cuisine
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def main():
    async with AsyncSessionLocal() as session:
        # 1) Look up the specific foods from the payload by name
        food_names = ["Idli", "Sambar", "Drumstick Leaf Green Shot", "Slivered Almonds"]
        print("=== Food DB IDs by name ===")
        for name in food_names:
            res = await session.execute(select(Food.id, Food.food_name).filter(Food.food_name.ilike(f"%{name}%")))
            rows = res.all()
            print(f"  '{name}' => {rows}")

        print()

        # 2) What does the meal M036 / Idli with Sambar look like in DB?
        res = await session.execute(
            select(Meal)
            .options(
                selectinload(Meal.meal_foods).selectinload(MealFood.food),
                selectinload(Meal.meal_session),
            )
            .where(Meal.recipe_name.ilike("%Idli with Sambar%"))
        )
        meals = res.scalars().all()
        print(f"=== Meals matching 'Idli with Sambar' ({len(meals)} found) ===")
        for m in meals:
            print(f"  Meal id={m.id}, name={m.recipe_name}, session={m.meal_session.code if m.meal_session else 'None'}")
            for mf in m.meal_foods:
                if mf.food:
                    print(f"    Food id={mf.food.id}, name={mf.food.food_name}")

        print()

        # 3) What are sessions in DB?
        res = await session.execute(select(MealSession.id, MealSession.code, MealSession.name_en))
        print("=== Meal Sessions in DB ===")
        for r in res:
            print(f"  id={r.id}, code={r.code}, name={r.name_en}")

asyncio.run(main())
