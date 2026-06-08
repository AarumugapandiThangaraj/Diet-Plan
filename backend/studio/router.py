"""
FastAPI Studio Router

Exposes REST API endpoints for the Plan Studio UI, covering daily target calculations, 
meal ranking, plan compilation, and swapping operations (meal/food/ingredient swaps).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from schemas import (
    StudioProfile,
    TargetsRequest,
    RankRequest,
    BuildPlanRequest,
    SubstitutesRequest,
    MealSwapOptionsRequest,
    MealSwapApplyRequest,
    FoodSwapOptionsRequest,
    FoodSwapApplyRequest,
    IngredientSwapOptionsRequest,
    IngredientSwapApplyRequest,
    StudioMetaResponse,
    DailyTargetsResponse,
    RankResponse,
    BuildPlanResponse,
    MealSwapOptionsResponse,
    SwapMealApplyResponse,
    SwapFoodOptionsResponse,
    SwapIngredientOptionsResponse,
    SubstitutesResponse
)
from services.planner_service import (
    fetch_daily_targets_service,
    fetch_ranked_meals_service,
    get_meal_swap_options_service,
    get_food_swap_options_service,
    get_ingredient_swap_options_service,
    apply_food_swap_service,
    apply_ingredient_swap_service
)
from config.constants import MEAL_TIME_ORDER, VALID_CUISINES
from repositories.meal_repository import load_master_meals, meal_index_by_id
from services.ranking_service import session_target_macros
from domain.scaling_formulas import ensure_macros, format_nutritive_values, scale_meal_to_targets
from domain.substitutes import suggest_for_ingredients_text
from domain.swap_engine import meal_for_plan_payload

router = APIRouter(prefix="/api/studio", tags=["diet-plan-studio"])

def _apply_cuisine(profile_dict: dict) -> dict:
    return profile_dict

def get_loaded_source_path(cuisine: str) -> str:
    return f"[{cuisine}] PostgreSQL Database (Authoritative Ingredient Cache)"

@router.get("/meta", response_model=StudioMetaResponse)
def studio_meta(cuisine: str = "north_indian"):
    meals = load_master_meals(cuisine)
    return {
        "mealTimes": MEAL_TIME_ORDER,
        "mealsCount": len(meals),
        "dataSource": get_loaded_source_path(cuisine),
        "validCuisines": VALID_CUISINES,
        "activeCuisine": cuisine,
    }

@router.post("/targets", response_model=DailyTargetsResponse)
def studio_targets(req: TargetsRequest):
    profile_dict = _apply_cuisine(req.profile.model_dump())
    return fetch_daily_targets_service(profile_dict)

@router.post("/rank", response_model=RankResponse)
def studio_rank(req: RankRequest):
    profile_dict = _apply_cuisine(req.profile.model_dump())
    meal_times = [t for t in req.mealTimes if t in MEAL_TIME_ORDER]
    if not meal_times:
        raise HTTPException(status_code=400, detail="mealTimes must include at least one valid meal time")
    return fetch_ranked_meals_service(profile_dict, meal_times, req.limit)

@router.post("/plan/build", response_model=BuildPlanResponse)
def studio_build_plan(req: BuildPlanRequest):
    profile = _apply_cuisine(req.profile.model_dump())
    days = max(1, min(21, int(req.days)))
    targets = fetch_daily_targets_service(profile)

    meal_times = [t for t in req.mealTimes if t in MEAL_TIME_ORDER]
    if not meal_times:
        raise HTTPException(status_code=400, detail="mealTimes must include at least one valid meal time")

    pools_by_time = req.poolsByTime or {}
    assignment_by_time = req.assignmentByTime or {}

    all_ids: set[str] = set()
    for mt in meal_times:
        ids = [str(x) for x in (pools_by_time.get(mt) or []) if str(x)]
        if not ids:
            raise HTTPException(status_code=400, detail=f"Please select at least 1 meal for {mt}.")
        if len(ids) > 7:
            raise HTTPException(status_code=400, detail=f"You can select up to 7 meals for {mt}.")
        for mid in ids:
            if mid in all_ids:
                raise HTTPException(
                    status_code=400,
                    detail="A meal was selected in more than one meal time. Please ensure selections are unique.",
                )
            all_ids.add(mid)

    cuisine = profile.get("cuisineType") or "north_indian"
    idx = meal_index_by_id(cuisine)

    plans: List[Dict[str, Any]] = []
    totals_by_day: List[Dict[str, float]] = []
    totals_all = {"caloriesKcal": 0.0, "proteinG": 0.0, "carbsG": 0.0, "fatG": 0.0, "fiberG": 0.0}

    for day_index in range(days):
        plan: Dict[str, Any] = {}
        totals = {"caloriesKcal": 0.0, "proteinG": 0.0, "carbsG": 0.0, "fatG": 0.0, "fiberG": 0.0}

        for mt in meal_times:
            assigned = assignment_by_time.get(mt) or []
            meal_id = str(assigned[day_index]) if day_index < len(assigned) else ""
            if not meal_id:
                continue

            meal = idx.get(meal_id)
            if not meal:
                continue

            target_macros = session_target_macros(targets, mt, meal_times)
            scale_info = scale_meal_to_targets(meal, target_macros)
            payload = meal_for_plan_payload(scale_info["scaledMeal"], scale_meta=scale_info)
            plan[mt] = payload

            macros = ensure_macros(payload.get("macros") or {})
            totals["caloriesKcal"] += macros["caloriesKcal"]
            totals["proteinG"] += macros["proteinG"]
            totals["carbsG"] += macros["carbsG"]
            totals["fatG"] += macros["fatG"]
            totals["fiberG"] += macros["fiberG"]

        plans.append(plan)
        totals_by_day.append(totals)
        for k in totals_all.keys():
            totals_all[k] += totals[k]

    if days == 1:
        return {
            "days": 1,
            "targets": targets,
            "plan": plans[0] if plans else {},
            "totals": totals_by_day[0] if totals_by_day else None,
            "mealTimes": meal_times,
        }

    return {
        "days": days,
        "targets": targets,
        "plans": plans,
        "totalsByDay": totals_by_day,
        "totalsAll": totals_all,
        "mealTimes": meal_times,
    }

@router.post("/swap/meal/options", response_model=MealSwapOptionsResponse)
def studio_swap_meal_options(req: MealSwapOptionsRequest):
    profile = _apply_cuisine(req.profile.model_dump())
    mt = str(req.mealTime or "")
    if mt not in MEAL_TIME_ORDER:
        raise HTTPException(status_code=400, detail="mealTime is invalid.")

    try:
        return get_meal_swap_options_service(
            profile=profile,
            meal_time=mt,
            current_meal_id=req.currentMealId,
            target_macros=req.targetMacros,
            exclude_meal_ids=req.excludeMealIds,
            allowed_meal_ids=req.allowedMealIds,
            top_n=req.topN,
            cuisine=profile.get("cuisineType") or "north_indian"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/swap/meal/apply", response_model=SwapMealApplyResponse)
def studio_swap_meal_apply(req: MealSwapApplyRequest):
    meal = dict(req.meal or {})
    if not meal:
        raise HTTPException(status_code=400, detail="Meal payload is required.")

    macros = ensure_macros(meal.get("macros") or meal.get("_macros") or {})
    meal["macros"] = macros
    meal["_macros"] = macros
    if not str(meal.get("nutritive_values") or "").strip():
        meal["nutritive_values"] = format_nutritive_values(macros)

    return {"meal": meal_for_plan_payload(meal)}

@router.post("/swap/food/options", response_model=SwapFoodOptionsResponse)
def studio_swap_food_options(req: FoodSwapOptionsRequest):
    try:
        cuisine = req.meal.get("cuisine_type") or "north_indian"
        if isinstance(cuisine, list) and len(cuisine) > 0:
            cuisine = cuisine[0]
        return get_food_swap_options_service(meal=req.meal, food_name=req.foodName, top_n=req.topN, cuisine=str(cuisine))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/swap/food/apply", response_model=SwapMealApplyResponse)
def studio_swap_food_apply(req: FoodSwapApplyRequest):
    try:
        cuisine = req.meal.get("cuisine_type") or "north_indian"
        if isinstance(cuisine, list) and len(cuisine) > 0:
            cuisine = cuisine[0]
        meal = apply_food_swap_service(meal=req.meal, option=req.option, cuisine=str(cuisine))
        return {"meal": meal}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/swap/ingredient/options", response_model=SwapIngredientOptionsResponse)
def studio_swap_ingredient_options(req: IngredientSwapOptionsRequest):
    try:
        cuisine = req.meal.get("cuisine_type") or "north_indian"
        if isinstance(cuisine, list) and len(cuisine) > 0:
            cuisine = cuisine[0]
        return get_ingredient_swap_options_service(meal=req.meal, ingredient_query=req.ingredientQuery, top_n=req.topN, cuisine=str(cuisine))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/swap/ingredient/apply", response_model=SwapMealApplyResponse)
def studio_swap_ingredient_apply(req: IngredientSwapApplyRequest):
    try:
        cuisine = req.meal.get("cuisine_type") or "north_indian"
        if isinstance(cuisine, list) and len(cuisine) > 0:
            cuisine = cuisine[0]
        meal = apply_ingredient_swap_service(meal=req.meal, option=req.option, cuisine=str(cuisine))
        return {"meal": meal}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/substitutes/from-ingredients", response_model=SubstitutesResponse)
def studio_substitutes(req: SubstitutesRequest):
    return suggest_for_ingredients_text(req.ingredients)
