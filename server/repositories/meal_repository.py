import asyncio
import threading
from typing import Any, Dict, List, Set, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.session import AsyncSessionLocal
from database.models.catalog import (
    Meal, MealFood, Food, PrimaryGoal, SecondaryGoal,
    MealPrimaryGoal, MealSecondaryGoal, Cuisine
)

_meals_cache: Dict[str, List[Dict[str, Any]]] = {}
_db_lock = threading.Lock()

_main_loop = None

def set_main_loop(loop):
    global _main_loop
    _main_loop = loop

def run_async(coro):
    global _main_loop
    import concurrent.futures
    if _main_loop is not None and _main_loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, _main_loop)
        return future.result()
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

async def _load_all_meals_db(cuisine_code: str = None) -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Meal)
            .options(
                selectinload(Meal.meal_foods).selectinload(MealFood.food),
                selectinload(Meal.meal_session),
                selectinload(Meal.primary_goals).selectinload(MealPrimaryGoal.primary_goal),
                selectinload(Meal.secondary_goals).selectinload(MealSecondaryGoal.secondary_goal),
                selectinload(Meal.cuisine)
            )
        )
        if cuisine_code:
            stmt = stmt.join(Meal.cuisine).filter(Cuisine.code == cuisine_code)
            
        res = await session.execute(stmt)
        meals = res.scalars().all()

        out = []
        for m in meals:
            foods_struct = []
            for mf in m.meal_foods:
                if mf.food:
                    foods_struct.append({
                        "id": str(mf.food.id),
                        "name": mf.food.food_name,
                        "serving_size": mf.serving_size,
                        "quantity": 1.0,
                        "unit": "serving"
                    })

            ingredients_struct = []

            meal_goals = []
            for pg in m.primary_goals:
                if pg.primary_goal:
                    meal_goals.append(pg.primary_goal.name_en)
            for sg in m.secondary_goals:
                if sg.secondary_goal:
                    meal_goals.append(sg.secondary_goal.name_en)

            totals = {
                "caloriesKcal": m.calories_kcal,
                "proteinG": m.protein_g,
                "carbsG": m.carbohydrates_g,
                "fatG": m.fat_g,
                "fiberG": m.dietary_fiber_g
            }

            out.append({
                "Meal_ID": str(m.id),
                "meal_name": m.recipe_name,
                "session": m.meal_session.name_en if m.meal_session else "",
                "goal": meal_goals,
                "time": "",
                "description": m.description or "",
                "allergens": [],
                "preparation_steps": [],
                "image_ID": "",
                "foods_struct": foods_struct,
                "ingredients_struct": ingredients_struct,
                "macros": totals,
                "_macros": totals,
                "cuisine_type": m.cuisine.code if m.cuisine else None
            })
        return out

def load_master_meals(cuisine: str = None, *args, **kwargs) -> List[Dict[str, Any]]:
    cache_key = cuisine or "global"
    if cache_key in _meals_cache:
        return _meals_cache[cache_key]
    with _db_lock:
        if cache_key in _meals_cache:
            return _meals_cache[cache_key]
        data = run_async(_load_all_meals_db(cuisine))
        _meals_cache[cache_key] = data
        return data

async def load_master_meals_async(cuisine: str = None, *args, **kwargs) -> List[Dict[str, Any]]:
    cache_key = cuisine or "global"
    if cache_key in _meals_cache:
        return _meals_cache[cache_key]
    data = await _load_all_meals_db(cuisine)
    _meals_cache[cache_key] = data
    return data

def meal_index_by_id(cuisine: str = None, *args, **kwargs) -> Dict[str, Dict[str, Any]]:
    return {str(m["Meal_ID"]): m for m in load_master_meals(cuisine) if m.get("Meal_ID")}

async def get_meal_index_by_id_async(cuisine: str = None, *args, **kwargs) -> Dict[str, Dict[str, Any]]:
    meals = await load_master_meals_async(cuisine)
    return {str(m["Meal_ID"]): m for m in meals if m.get("Meal_ID")}

async def find_complementary_meals(
    session_db,
    session_name: str,
    keep_food_ids: Set[str],
    avoid_food_ids: Set[str],
    cuisine: str = None,
    limit: int = 10
) -> List[Meal]:
    from database.models.catalog import Cuisine, MealSession
    stmt = (
        select(Meal)
        .join(MealSession, Meal.meal_session_id == MealSession.id)
        .where(MealSession.name_en == session_name)
    )
    if cuisine:
        stmt = stmt.join(Cuisine, Meal.cuisine_id == Cuisine.id).where(Cuisine.code == cuisine)
    
    stmt = stmt.options(
        selectinload(Meal.meal_foods).selectinload(MealFood.food)
    )
    res = await session_db.execute(stmt)
    all_session_meals = res.scalars().all()
    
    valid_meals = []
    for m in all_session_meals:
        meal_food_ids = {mf.food.id for mf in m.meal_foods if mf.food}
        if keep_food_ids and not keep_food_ids.issubset(meal_food_ids):
            continue
        if avoid_food_ids and not avoid_food_ids.isdisjoint(meal_food_ids):
            continue
        valid_meals.append(m)
        if len(valid_meals) >= limit:
            break
            
    return valid_meals
