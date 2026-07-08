import sys
from pathlib import Path
import json
import asyncio

# Setup path so we can import from server
server_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(server_dir))

from database.session import AsyncSessionLocal
from database.models.catalog import Cuisine, Food, Meal, MealFood, MasterIngredient, MealIngredient, MealSession
from sqlalchemy import select

async def run_import(data_dir: Path, cuisine_code: str):
    meal_file = data_dir / "meal.json"
    food_file = data_dir / "food.json"
    meal_food_file = data_dir / "meal_food.json"
    meal_ingredient_file = data_dir / "meal_ingredient.json"

    meals_data = json.loads(meal_file.read_text(encoding="utf-8"))
    foods_data = json.loads(food_file.read_text(encoding="utf-8"))
    meal_foods_data = json.loads(meal_food_file.read_text(encoding="utf-8"))
    meal_ingredients_data = json.loads(meal_ingredient_file.read_text(encoding="utf-8"))

    async with AsyncSessionLocal() as session:
        # Create new tables if they don't exist
        from database.base import Base
        async with session.bind.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        # Get or create cuisine
        stmt = select(Cuisine).where(Cuisine.code == cuisine_code)
        res = await session.execute(stmt)
        cuisine = res.scalar_one_or_none()
        if not cuisine:
            cuisine = Cuisine(code=cuisine_code, name_en=cuisine_code.replace("_", " ").title())
            session.add(cuisine)
            await session.flush()

        # Get or create default session
        stmt = select(MealSession).where(MealSession.code == "lunch")
        res = await session.execute(stmt)
        default_session = res.scalar_one_or_none()
        if not default_session:
            default_session = MealSession(code="lunch", name_en="Lunch")
            session.add(default_session)
            await session.flush()

        # Process foods
        food_db_map = {}
        for f in foods_data:
            client_id = f["food_id"]
            name = f["food_name"]
            stmt = select(Food).where(Food.id == client_id, Food.cuisine_id == cuisine.id)
            res = await session.execute(stmt)
            food = res.scalar()

            if not food:
                food = Food(
                    id=client_id,
                    cuisine_id=cuisine.id,
                    food_name=name
                )
                session.add(food)
                await session.flush()
            food_db_map[client_id] = food.id

        # Process ingredients
        ingredient_db_map = {}
        # Collect unique ingredient names
        unique_ing_names = set(i["ingredient_name"] for i in meal_ingredients_data)
        for name in unique_ing_names:
            stmt = select(MasterIngredient).where(MasterIngredient.name_en == name)
            res = await session.execute(stmt)
            ing = res.scalar_one_or_none()
            if not ing:
                ing = MasterIngredient(
                    name_en=name,
                    default_unit="g",
                    calories_kcal=0.0, # Data doesn't provide macros for ingredients
                    protein_g=0.0,
                    carbs_g=0.0,
                    fat_g=0.0,
                    fiber_g=0.0
                )
                session.add(ing)
                await session.flush()
            ingredient_db_map[name] = ing.id

        # Process meals
        meal_db_map = {}
        for m in meals_data:
            client_id = m["meal_id"]
            name = m["recipe_name"]
            # Simplified meal session matching
            
            stmt = select(Meal).where(Meal.id == client_id, Meal.cuisine_id == cuisine.id)
            res = await session.execute(stmt)
            meal = res.scalar_one_or_none()
            if not meal:
                meal = Meal(
                    id=client_id,
                    cuisine_id=cuisine.id,
                    recipe_name=m["meal_name"],
                    session=m["session"],
                    time=m.get("time", ""),
                    description=m.get("method", ""),
                    image=m.get("image_ID", "")
                )
                session.add(meal)
                await session.flush()
            meal_db_map[client_id] = meal.id
            
            # Remove old meal foods & ingredients to recreate
            await session.execute(MealFood.__table__.delete().where(MealFood.meal_id == meal.id))
            await session.execute(MealIngredient.__table__.delete().where(MealIngredient.meal_id == meal.id))

        # Process MealFood junctions
        for mf in meal_foods_data:
            m_id = meal_db_map.get(mf["meal_id"])
            f_id = food_db_map.get(mf["food_id"])
            if m_id and f_id:
                # Assuming quantity defaults to 1.0 or parsing serving_size
                qty_str = mf.get("serving_size", "1")
                try:
                    qty = float(''.join(c for c in qty_str if c.isdigit() or c == '.'))
                except ValueError:
                    qty = 1.0
                session.add(MealFood(meal_id=m_id, food_id=f_id, quantity=qty, is_replaceable=True))

        # Process MealIngredient junctions
        mi_aggregated = {}
        for mi in meal_ingredients_data:
            m_id = meal_db_map.get(mi["meal_id"])
            i_id = ingredient_db_map.get(mi["ingredient_name"])
            if m_id and i_id:
                qty = float(mi.get("quantity") or 0.0)
                unit = mi.get("unit") or "g"
                key = (m_id, i_id)
                if key not in mi_aggregated:
                    mi_aggregated[key] = {"quantity": qty, "unit": unit}
                else:
                    mi_aggregated[key]["quantity"] += qty

        for (m_id, i_id), data in mi_aggregated.items():
            session.add(MealIngredient(meal_id=m_id, ingredient_id=i_id, quantity=data["quantity"], unit=data["unit"]))

        await session.commit()
        print("Import successful!")

if __name__ == "__main__":
    import_dir = Path(__file__).resolve().parents[2] / "new core models" / "data" / "south indian cuisine"
    asyncio.run(run_import(import_dir, "south_indian"))
