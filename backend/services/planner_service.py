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
