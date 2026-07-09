from typing import Any, Dict, List, Optional
from database.session import AsyncSessionLocal
from domain.swap_engine import _ratio, _macro_error
from repositories.meal_repository import (
    get_meal_index_by_id_async,
    find_complementary_meals,
    load_master_meals,
    meal_index_by_id
)

def format_nutritive_values(macros: Dict[str, float]) -> str:
    cal = macros.get('caloriesKcal', 0)
    pro = macros.get('proteinG', 0)
    car = macros.get('carbsG', 0)
    fat = macros.get('fatG', 0)
    fib = macros.get('fiberG', 0)
    return f"{cal:.0f} kcal (P: {pro:.1f}g, C: {car:.1f}g, F: {fat:.1f}g, Fib: {fib:.1f}g)"

def meal_for_plan_payload(meal: Dict[str, Any], *, scale_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = dict(meal)
    payload["nutritive_values"] = format_nutritive_values(meal.get("macros", {}))
    if scale_meta:
        payload["scale"] = {
            "requested": float(scale_meta.get("scaleFactorRequested", 1.0) or 1.0),
            "applied": float(scale_meta.get("scaleFactorApplied", 1.0) or 1.0),
        }
    return payload

async def get_meal_swap_options_async(
    *,
    profile: Dict[str, Any],
    meal_time: str,
    current_meal_id: str,
    target_macros: Optional[Dict[str, Any]] = None,
    exclude_meal_ids: Optional[List[str]] = None,
    allowed_meal_ids: Optional[List[str]] = None,
    top_n: int = 5,
) -> Dict[str, Any]:
    cuisine = profile.get("cuisineType") or "north_indian"
    idx = await get_meal_index_by_id_async(cuisine)
    base_meal = idx.get(str(current_meal_id))
    from utils.normalizers import _normalize_meal_time
    session_name = _normalize_meal_time(base_meal.get("session") if base_meal else meal_time)
    
    excluded = {str(current_meal_id or "").strip()}
    for x in exclude_meal_ids or []:
        if str(x or "").strip():
            excluded.add(str(x).strip())
            
    all_meals = await get_meal_index_by_id_async(cuisine)
    
    options = []
    target = target_macros or {}
    
    for mid, m in all_meals.items():
        if mid in excluded:
            continue
        if _normalize_meal_time(m.get("session")) != session_name:
            continue
            
        score = _macro_error(m.get("macros", {}), target)
        options.append({
            "mealId": mid,
            "score": score,
            "scaleFactorRequested": 1.0,
            "scaleFactorApplied": 1.0,
            "meal": meal_for_plan_payload(m)
        })
        
    options.sort(key=lambda x: x["score"])
    return {
        "targetMacros": target,
        "options": options[:max(1, int(top_n))]
    }

def get_meal_swap_options(*args, **kwargs) -> Dict[str, Any]:
    import asyncio
    return asyncio.run(get_meal_swap_options_async(*args, **kwargs))

async def get_food_swap_options_async(*, meal: Dict[str, Any], food_name: str, top_n: int = 5, cuisine: str = "") -> Dict[str, Any]:
    # 1. Identify the food to swap out
    foods = meal.get("foods_struct") or meal.get("foods") or []
    source_idx = -1
    source_food = None
    best_score = -1.0
    
    for i, f in enumerate(foods):
        fname = f.get("name", "")
        score = _ratio(fname, food_name)
        if food_name.lower() in fname.lower() or fname.lower() in food_name.lower():
            score = max(score, 0.92)
        if score > best_score:
            best_score = score
            source_idx = i
            source_food = f
            
    if not source_food or best_score < 0.35:
        raise ValueError(f"Could not find food '{food_name}' in this meal.")

    # Normalize food id: accept both "id" and "food_id" fields
    def get_food_id(food: Dict[str, Any]) -> str:
        return str(food.get("id") or food.get("food_id") or "").strip()
        
    source_food_id = get_food_id(source_food)
    
    # 2. Identify the foods we want to KEEP (exclude the one being swapped)
    keep_food_ids = {get_food_id(f) for i, f in enumerate(foods) if i != source_idx and get_food_id(f)}
    avoid_food_ids = {source_food_id} if source_food_id else set()

    # 3. Resolve session_name — try payload fields first, then fall back to DB lookup
    session_name = (
        meal.get("session") or
        meal.get("meal_time") or
        meal.get("session_name") or
        ""
    )

    options = []
    async with AsyncSessionLocal() as db_session:
        # 3a. If session is still empty, look it up from the DB using a food that's in the meal
        if not session_name:
            from database.models.catalog import Meal as MealModel, MealFood, MealSession
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            lookup_food_id = source_food_id or (next(iter(keep_food_ids), None))
            if lookup_food_id and lookup_food_id.isdigit():
                stmt = (
                    select(MealModel)
                    .join(MealFood, MealFood.meal_id == MealModel.id)
                    .options(selectinload(MealModel.meal_session))
                    .where(MealFood.food_id == int(lookup_food_id))
                )
                if cuisine:
                    from database.models.catalog import Cuisine as CuisineModel
                    stmt = stmt.join(CuisineModel, CuisineModel.id == MealModel.cuisine_id).where(CuisineModel.code == cuisine)
                res = await db_session.execute(stmt)
                ref_meal = res.scalars().first()
                if ref_meal and ref_meal.meal_session:
                    session_name = ref_meal.meal_session.code
                    
        # 4. Find candidate meals that share keep_food_ids but differ in the source food
        cand_meals = await find_complementary_meals(
            session_db=db_session,
            session_name=session_name,
            keep_food_ids=keep_food_ids,
            avoid_food_ids=avoid_food_ids,
            cuisine=cuisine,
            limit=50
        )
        
        for cand in cand_meals:
            # We want candidate meal to have exactly 1 extra food that replaces our source_food
            cand_food_ids = {str(mf.food.id) for mf in cand.meal_foods if mf.food}
            diff = cand_food_ids - keep_food_ids
            
            if len(diff) != 1:
                continue
                
            new_food_id = diff.pop()
            
            # Find the actual food dictionary in cand
            new_food_obj = next((mf.food for mf in cand.meal_foods if mf.food and str(mf.food.id) == new_food_id), None)
            if not new_food_obj:
                continue
                
            from domain.scaling_formulas import scale_meal_to_targets
            original_macros = meal.get("macros") or meal.get("_macros") or {}
            cand_meal_dict = {
                "macros": {
                    "caloriesKcal": cand.calories_kcal,
                    "proteinG": cand.protein_g,
                    "carbsG": cand.carbohydrates_g,
                    "fatG": cand.fat_g,
                    "fiberG": cand.dietary_fiber_g
                }
            }
            
            if original_macros and original_macros.get("caloriesKcal"):
                target_macros = {"caloriesKcal": original_macros.get("caloriesKcal", 0.0)}
                scale_info = scale_meal_to_targets(cand_meal_dict, target_macros)
                scale_factor = scale_info.get("scaleFactorApplied", 1.0)
            else:
                scale_factor = 1.0
                
            replacement = {
                "foodId": new_food_id,
                "name": new_food_obj.food_name,
                "quantity": 1.0 * scale_factor,
                "unit": "serving",
                "macros": {}
            }
            
            cand_macros = {
                "caloriesKcal": float(cand.calories_kcal or 0.0) * scale_factor,
                "proteinG": float(cand.protein_g or 0.0) * scale_factor,
                "carbsG": float(cand.carbohydrates_g or 0.0) * scale_factor,
                "fatG": float(cand.fat_g or 0.0) * scale_factor,
                "fiberG": float(cand.dietary_fiber_g or 0.0) * scale_factor
            }
            
            options.append({
                "sourceFoodIndex": source_idx,
                "sourceFoodName": source_food.get("name", ""),
                "score": 0.1, # All complementary matches are equally good conceptually
                "nutritionError": 0.0,
                "fuzzySimilarity": 1.0,
                "replacement": replacement,
                "replacementMealId": str(cand.id),
                "scaleFactorApplied": scale_factor,
                "projectedMealMacros": cand_macros,
                "projectedNutritiveValues": format_nutritive_values(cand_macros)
            })
            
    return {
        "matchedSource": {
            "name": source_food.get("name", ""),
            "index": source_idx,
            "matchScore": best_score,
            "macros": {}
        },
        "options": options[:max(1, int(top_n))]
    }

def get_food_swap_options(*args, **kwargs) -> Dict[str, Any]:
    import asyncio
    return asyncio.run(get_food_swap_options_async(*args, **kwargs))

def get_ingredient_swap_options(*args, **kwargs) -> Dict[str, Any]:
    # Unsupported in V2
    return {"options": []}

async def apply_food_swap_option(*, meal: Dict[str, Any], option: Dict[str, Any], cuisine: str = "") -> Dict[str, Any]:
    cand_id = option.get("replacementMealId")
    if not cand_id:
        return dict(meal)

    # Try with the provided cuisine first, then fall back to global (all cuisines)
    new_meal = None
    for search_cuisine in ([cuisine, None] if cuisine else [None]):
        idx = await get_meal_index_by_id_async(search_cuisine or None)
        new_meal = idx.get(str(cand_id))
        if new_meal:
            break

    if not new_meal:
        return dict(meal)

    original_macros = meal.get("macros") or meal.get("_macros") or {}
    payload = meal_for_plan_payload(new_meal)

    if original_macros and original_macros.get("caloriesKcal"):
        from domain.scaling_formulas import scale_meal_to_targets
        target_macros = {"caloriesKcal": original_macros.get("caloriesKcal", 0.0)}
        scale_info = scale_meal_to_targets(payload, target_macros)
        return scale_info.get("scaledMeal", payload)

    return payload

def apply_ingredient_swap_option(*, meal: Dict[str, Any], option: Dict[str, Any], cuisine: str = "") -> Dict[str, Any]:
    return dict(meal)
