"""
Planner Service

High-level service orchestrator managing meal plans, swapping logic, and database
target lookups for the Plan Studio.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from copy import deepcopy

from services.nutrition_service import calculate_daily_targets
from services.ranking_service import rank_meals_for_meal_time
from services.swap_service import (
    get_meal_swap_options,
    get_food_swap_options,
    get_ingredient_swap_options,
    apply_food_swap_option,
    apply_ingredient_swap_option,
)

def fetch_daily_targets_service(profile: dict) -> dict:
    """
    Retrieves the target nutrient breakdown based on physical metrics inside the user profile.
    """
    return calculate_daily_targets(profile)

def fetch_ranked_meals_service(profile: dict, meal_times: List[str], limit: int) -> dict:
    """
    Ranks meals for each provided meal time session, matching the user profile requirements and macro targets.
    """
    targets = calculate_daily_targets(profile)
    ranked_by_time = {}
    for mt in meal_times:
        ranked_by_time[mt] = rank_meals_for_meal_time(
            profile=profile,
            meal_time=mt,
            targets=targets,
            limit=limit
        )["ranked"]
        
    return {
        "targets": targets,
        "rankedByTime": ranked_by_time
    }

def get_meal_swap_options_service(
    profile: dict,
    meal_time: str,
    current_meal_id: str,
    target_macros: Optional[dict],
    exclude_meal_ids: List[str],
    allowed_meal_ids: List[str],
    top_n: int,
    cuisine: str
) -> dict:
    """
    Generates suitable alternative meal choices to swap out a whole meal.
    """
    return get_meal_swap_options(
        profile=profile,
        meal_time=meal_time,
        current_meal_id=current_meal_id,
        target_macros=target_macros,
        exclude_meal_ids=exclude_meal_ids,
        allowed_meal_ids=allowed_meal_ids,
        top_n=top_n
    )

def get_food_swap_options_service(meal: dict, food_name: str, top_n: int, cuisine: str) -> dict:
    """
    Generates food swap options for replacing a specific food item within a meal.
    """
    return get_food_swap_options(meal=meal, food_name=food_name, top_n=top_n, cuisine=cuisine)

def get_ingredient_swap_options_service(meal: dict, ingredient_query: str, top_n: int, cuisine: str) -> dict:
    """
    Generates ingredient swap options for replacing a specific ingredient within a food item.
    """
    return get_ingredient_swap_options(meal=meal, ingredient_query=ingredient_query, top_n=top_n, cuisine=cuisine)

def apply_food_swap_service(meal: dict, option: dict, cuisine: str) -> dict:
    """
    Applies a selected food swap option to the meal dictionary and recalculates macro details.
    """
    return apply_food_swap_option(meal=meal, option=option, cuisine=cuisine)

def apply_ingredient_swap_service(meal: dict, option: dict, cuisine: str) -> dict:
    """
    Applies a selected ingredient swap option to the meal dictionary and recalculates macro details.
    """
    return apply_ingredient_swap_option(meal=meal, option=option, cuisine=cuisine)

from datetime import date, datetime
from repositories.user_plan_repository import load_user_plan, save_user_plan

def strip_meal_payload(meal: dict) -> dict:
    """
    Optimizes payload but retains necessary structures (foods_struct, ingredients_struct) 
    for V2 database normalization.
    """
    if not meal:
        return {}
    meal_copy = meal.copy()
    # V2 requires foods_struct and ingredients_struct to build DietPlanMealFood and DietPlanMealFoodIngredient.
    # We only remove purely textual fields that take up large bandwidth for clients.
    keys_to_remove = ["ingredients", "method", "caution"]
    for key in keys_to_remove:
        meal_copy.pop(key, None)
    return meal_copy

def strip_plan_payload(plan_data: dict) -> dict:
    """
    Strips recipe preparation details from the full plan dictionary.
    """
    if not plan_data:
        return {}
    plan_copy = plan_data.copy()
    
    # Check if this is a single day plan response
    if "plan" in plan_copy and isinstance(plan_copy["plan"], dict):
        stripped_day = {}
        for session, meal in plan_copy["plan"].items():
            if isinstance(meal, dict):
                stripped_day[session] = strip_meal_payload(meal)
            else:
                stripped_day[session] = meal
        plan_copy["plan"] = stripped_day
        
    # Check if this is a multi-day plans response
    if "plans" in plan_copy and isinstance(plan_copy["plans"], list):
        stripped_plans = []
        for day_plan in plan_copy["plans"]:
            if isinstance(day_plan, dict):
                stripped_day = {}
                for session, meal in day_plan.items():
                    if isinstance(meal, dict):
                        stripped_day[session] = strip_meal_payload(meal)
                    else:
                        stripped_day[session] = meal
                stripped_plans.append(stripped_day)
            else:
                stripped_plans.append(day_plan)
        plan_copy["plans"] = stripped_plans
        
    return plan_copy

async def save_user_plan_service(user_identifier: str, days: int, plan_data: dict, profile_data: dict = None) -> dict:
    """
    Strips and saves the user's active diet plan payload asynchronously.
    """
    start_date = date.today()
    # end_date is start_date + days - 1
    from datetime import timedelta
    end_date = start_date + timedelta(days=max(1, days) - 1)
    stripped = strip_plan_payload(plan_data)
    return await save_user_plan(user_identifier, start_date, end_date, stripped, profile_data)

async def get_active_user_plan_service(user_identifier: str) -> Optional[dict]:
    """
    Loads user plan and verifies it is within the active start/end date range asynchronously.
    """
    plan = await load_user_plan(user_identifier)
    if not plan:
        return None
    
    today = date.today()
    start_date = plan["start_date"]
    end_date = plan["end_date"]
    
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)
        
    if start_date <= today <= end_date:
        return plan
    return None


