import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.session import AsyncSessionLocal
from database.models.catalog import Food, Meal, MealFood, MealSession, Cuisine
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from repositories.meal_repository import find_complementary_meals

# Simulating what the swap engine does after the frontend sends the payload
# and model_dump(by_alias=True) is called
meal_from_payload = {
    "Meal_ID": "110727f1-b550-4973-8c30-bedaee20c5ff",
    "meal_name": "Idli with Sambar, Drumstick Leaf Powder Green Shot and Slivered Almonds",
    "cuisine_type": "south_indian",
    "foods_struct": [
        {"name": "Idli", "id": "36", "quantity": 3},
        {"name": "Sambar", "id": "37", "quantity": 160},
        {"name": "Drumstick Leaf Green Shot", "id": "38", "quantity": 90},
        {"name": "Slivered Almonds", "id": "39", "quantity": 1},
    ]
}

food_to_swap = "Idli"
cuisine = "south_indian"

async def main():
    foods = meal_from_payload.get("foods_struct") or []

    # Identify the source food (what to swap)
    source_idx = -1
    source_food = None
    best_score = -1
    for i, f in enumerate(foods):
        fname = f.get("name", "")
        if food_to_swap.lower() in fname.lower() or fname.lower() in food_to_swap.lower():
            source_idx = i
            source_food = f
            best_score = 0.95
            break

    print(f"Source food: {source_food}, idx={source_idx}")

    source_food_id = str(source_food.get("id", ""))
    keep_food_ids = {str(f.get("id", "")) for i, f in enumerate(foods) if i != source_idx and f.get("id")}
    avoid_food_ids = {source_food_id} if source_food_id else set()

    print(f"keep_food_ids: {keep_food_ids}")
    print(f"avoid_food_ids: {avoid_food_ids}")

    session_name = meal_from_payload.get("session", "") or meal_from_payload.get("meal_time", "")
    print(f"session_name from payload: '{session_name}' (THIS IS THE BUG - it's empty!)")

    # What find_complementary_meals actually does:
    async with AsyncSessionLocal() as db_session:
        stmt = (
            select(Meal)
            .join(MealSession, Meal.meal_session_id == MealSession.id)
            .where(MealSession.code == session_name.lower())
        )
        res = await db_session.execute(stmt)
        meals = res.scalars().all()
        print(f"\nMeals found with empty session filter: {len(meals)} (should be 0 since session is '')")

        # Test with correct session
        stmt2 = (
            select(Meal)
            .join(MealSession, Meal.meal_session_id == MealSession.id)
            .where(MealSession.code == "breakfast")
        )
        res2 = await db_session.execute(stmt2)
        all_breakfast = res2.scalars().all()
        print(f"\nAll breakfast meals in DB: {len(all_breakfast)}")

        # Now simulate with keep_food_ids as ints
        print(f"\nSimulating find_complementary_meals with keep={keep_food_ids}, avoid={avoid_food_ids}")
        cands = await find_complementary_meals(
            session_db=db_session,
            session_name="breakfast",  # using hardcoded correct session
            keep_food_ids=keep_food_ids,
            avoid_food_ids=avoid_food_ids,
            cuisine=cuisine,
            limit=10
        )
        print(f"Candidates found: {len(cands)}")
        for c in cands:
            food_ids_in_cand = {str(mf.food.id) for mf in c.meal_foods if mf.food}
            print(f"  Meal id={c.id}, name={c.recipe_name}, food_ids={food_ids_in_cand}")
            diff = food_ids_in_cand - keep_food_ids
            print(f"    diff (new food): {diff}")

asyncio.run(main())
