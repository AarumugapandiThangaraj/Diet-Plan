"""
Swap Service

Provides logical operations for swapping/replacing items within a meal plan, 
supporting meal swaps, food item swaps, and ingredient replacements.
"""

from copy import deepcopy
from typing import Any, Dict, List, Optional
from domain.swap_engine import (
    _macro_error,
    _meal_macros,
    meal_for_plan_payload,
    _resolve_source_food,
    _candidate_food_keys_for_source,
    _replacement_food_from_catalog,
    _ratio,
    _resolve_source_ingredient,
    _candidate_keys_for_source,
    _replacement_from_catalog,
    _apply_food_replacement,
    _apply_ingredient_replacement
)
from domain.scaling_formulas import (
    ensure_macros,
    format_nutritive_values,
    scale_meal_to_targets,
    recompute_meal_from_foods,
    recompute_meal_from_ingredients
)
from config.constants import MEAL_TIME_ORDER
from repositories.meal_repository import (
    meal_index_by_id,
    food_catalog_by_key,
    ingredient_catalog_by_key,
    build_food_instance
)
from services.nutrition_service import calculate_daily_targets
from services.ranking_service import session_target_macros, rank_meals_for_meal_time

def get_meal_swap_options(
    *,
    profile: Dict[str, Any],
    meal_time: str,
    current_meal_id: str,
    target_macros: Optional[Dict[str, Any]] = None,
    exclude_meal_ids: Optional[List[str]] = None,
    allowed_meal_ids: Optional[List[str]] = None,
    top_n: int = 5,
) -> Dict[str, Any]:
    targets = calculate_daily_targets(profile)
    target = ensure_macros(target_macros or session_target_macros(targets, meal_time))

    excluded = {str(current_meal_id or "").strip()}
    for x in exclude_meal_ids or []:
        if str(x or "").strip():
            excluded.add(str(x).strip())

    cuisine = profile.get("cuisineType") or "north_indian"
    idx = meal_index_by_id(cuisine)
    if allowed_meal_ids:
        allowed = [str(x or "").strip() for x in allowed_meal_ids if str(x or "").strip()]
        options: List[Dict[str, Any]] = []
        for mid in allowed:
            if mid in excluded:
                continue

            base = idx.get(mid)
            if not base:
                continue
            if str(base.get("meal_time")) != str(meal_time):
                continue

            scale_info = scale_meal_to_targets(base, target)
            scaled = scale_info["scaledMeal"]
            score = _macro_error(_meal_macros(scaled), target)

            options.append(
                {
                    "mealId": mid,
                    "score": float(score),
                    "scaleFactorRequested": float(scale_info["scaleFactorRequested"]),
                    "scaleFactorApplied": float(scale_info["scaleFactorApplied"]),
                    "meal": meal_for_plan_payload(scaled, scale_meta=scale_info),
                }
            )

        options.sort(key=lambda x: x["score"])
        return {
            "targetMacros": target,
            "options": options[: max(1, int(top_n))],
        }

    ranked_meta = rank_meals_for_meal_time(
        profile=profile,
        meal_time=meal_time,
        targets=targets,
        limit=max(80, int(top_n) * 20),
        min_options=max(7, int(top_n)),
    )
    ranked = ranked_meta.get("ranked") or []

    options: List[Dict[str, Any]] = []
    for item in ranked:
        mid = str(item.get("Meal_ID") or "")
        if not mid or mid in excluded:
            continue

        base = idx.get(mid)
        if not base:
            continue

        scale_info = scale_meal_to_targets(base, target)
        scaled = scale_info["scaledMeal"]
        score = _macro_error(_meal_macros(scaled), target)

        options.append(
            {
                "mealId": mid,
                "score": float(score),
                "scaleFactorRequested": float(scale_info["scaleFactorRequested"]),
                "scaleFactorApplied": float(scale_info["scaleFactorApplied"]),
                "meal": meal_for_plan_payload(scaled, scale_meta=scale_info),
            }
        )

    options.sort(key=lambda x: x["score"])
    return {
        "targetMacros": target,
        "options": options[: max(1, int(top_n))],
    }

from exceptions.domain import SwapEngineException

def get_food_swap_options(*, meal: Dict[str, Any], food_name: str, top_n: int = 5, cuisine: str = "north_indian") -> Dict[str, Any]:
    meal_base = deepcopy(meal)
    if not (meal_base.get("foods_struct") or []):
        raise SwapEngineException("This meal cannot be swapped at food level because no structured food data is available.")

    meal_base = recompute_meal_from_foods(meal_base)
    meal_target_macros = _meal_macros(meal_base)

    source_idx, source_food, source_match = _resolve_source_food(meal_base, food_name)

    source_macros = ensure_macros((source_food or {}).get("macros") or {})
    source_name = str(source_food.get("name") or "")

    catalog = food_catalog_by_key(cuisine)
    keys = _candidate_food_keys_for_source(source_name)

    options: List[Dict[str, Any]] = []
    for key in keys:
        entry = catalog.get(key)
        if not entry:
            continue
        replacement = _replacement_food_from_catalog(entry, source_food)
        if not replacement:
            continue

        replacement_food = build_food_instance(
            cuisine,
            str(replacement.get("foodId") or ""),
            quantity=float(replacement.get("quantity") or 0.0),
            unit=str(replacement.get("unit") or "g"),
            replaceable=True,
        )
        repl_macros = ensure_macros((replacement_food or {}).get("macros") or replacement.get("macros") or {})

        projected = {
            "caloriesKcal": meal_target_macros["caloriesKcal"] - source_macros["caloriesKcal"] + repl_macros["caloriesKcal"],
            "proteinG": meal_target_macros["proteinG"] - source_macros["proteinG"] + repl_macros["proteinG"],
            "carbsG": meal_target_macros["carbsG"] - source_macros["carbsG"] + repl_macros["carbsG"],
            "fatG": meal_target_macros["fatG"] - source_macros["fatG"] + repl_macros["fatG"],
            "fiberG": meal_target_macros["fiberG"] - source_macros["fiberG"] + repl_macros["fiberG"],
        }

        nutrition_error = _macro_error(projected, meal_target_macros)
        lexical = _ratio(source_name, replacement["name"])
        score = nutrition_error + (1.0 - lexical) * 0.15

        options.append(
            {
                "sourceFoodIndex": source_idx,
                "sourceFoodName": source_name,
                "score": float(score),
                "nutritionError": float(nutrition_error),
                "fuzzySimilarity": float(lexical),
                "replacement": replacement,
                "projectedMealMacros": projected,
                "projectedNutritiveValues": format_nutritive_values(projected),
            }
        )

    options.sort(key=lambda x: x["score"])
    return {
        "matchedSource": {
            "name": source_name,
            "index": source_idx,
            "matchScore": float(source_match),
            "macros": source_macros,
        },
        "options": options[: max(1, int(top_n))],
    }

def get_ingredient_swap_options(*, meal: Dict[str, Any], ingredient_query: str, top_n: int = 5, cuisine: str = "north_indian") -> Dict[str, Any]:
    meal_base = deepcopy(meal)
    if meal_base.get("foods_struct"):
        meal_base = recompute_meal_from_foods(meal_base)
    else:
        meal_base = recompute_meal_from_ingredients(meal_base)
    meal_target_macros = _meal_macros(meal_base)

    source_entry, source_match = _resolve_source_ingredient(meal_base, ingredient_query)
    source_ing = source_entry.get("ingredient") or {}
    source_macros = ensure_macros((source_ing or {}).get("macros") or {})
    source_name = str(source_ing.get("name") or "")

    catalog = ingredient_catalog_by_key(cuisine)
    keys = _candidate_keys_for_source(source_name)

    options: List[Dict[str, Any]] = []
    for key in keys:
        entry = catalog.get(key)
        if not entry:
            continue
        replacement = _replacement_from_catalog(entry, source_ing)
        if not replacement:
            continue

        projected = {
            "caloriesKcal": meal_target_macros["caloriesKcal"] - source_macros["caloriesKcal"] + replacement["macros"]["caloriesKcal"],
            "proteinG": meal_target_macros["proteinG"] - source_macros["proteinG"] + replacement["macros"]["proteinG"],
            "carbsG": meal_target_macros["carbsG"] - source_macros["carbsG"] + replacement["macros"]["carbsG"],
            "fatG": meal_target_macros["fatG"] - source_macros["fatG"] + replacement["macros"]["fatG"],
            "fiberG": meal_target_macros["fiberG"] - source_macros["fiberG"] + replacement["macros"]["fiberG"],
        }

        nutrition_error = _macro_error(projected, meal_target_macros)
        lexical = _ratio(source_name, replacement["name"])
        score = nutrition_error + (1.0 - lexical) * 0.15

        options.append(
            {
                "sourceFoodIndex": source_entry.get("food_index"),
                "sourceIngredientIndex": source_entry.get("ingredient_index"),
                "sourceIndex": source_entry.get("ingredient_index"),
                "sourceName": source_name,
                "score": float(score),
                "nutritionError": float(nutrition_error),
                "fuzzySimilarity": float(lexical),
                "replacement": replacement,
                "projectedMealMacros": projected,
                "projectedNutritiveValues": format_nutritive_values(projected),
            }
        )

    options.sort(key=lambda x: x["score"])
    return {
        "matchedSource": {
            "name": source_name,
            "index": source_entry.get("ingredient_index"),
            "matchScore": float(source_match),
            "macros": source_macros,
        },
        "options": options[: max(1, int(top_n))],
    }

def apply_food_swap_option(*, meal: Dict[str, Any], option: Dict[str, Any], cuisine: str = "north_indian") -> Dict[str, Any]:
    return _apply_food_replacement(meal, option, cuisine=cuisine)

def apply_ingredient_swap_option(*, meal: Dict[str, Any], option: Dict[str, Any], cuisine: str = "north_indian") -> Dict[str, Any]:
    return _apply_ingredient_replacement(meal, option, cuisine=cuisine)
