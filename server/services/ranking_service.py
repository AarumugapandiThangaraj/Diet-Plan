"""
Ranking Service

Ranks and scores meals matching user profile requirements. Evaluates goal compatibility, 
macro deviations, and ingredient exclusions to sort recommended foods.
"""

import os
import json
from typing import Any, Dict, Iterable, List, Optional, Tuple
from config.constants import MEAL_DISTRIBUTION
from utils.normalizers import normalize_goal, normalize_goal_list, _normalize_diet_type
from utils.parsers import split_keywords
from utils.formatters import format_nutritive_values
from domain.filters import _is_meal_allowed
from repositories.meal_repository import load_master_meals
from services.nutrition_service import calculate_daily_targets

def _relative_error(actual: float, target: float) -> float:
    t = max(0.0, float(target or 0.0))
    a = max(0.0, float(actual or 0.0))
    if t == 0:
        return 0.0 if a == 0 else 1.0
    return abs(a - t) / t

def _macro_weights(bmi_category: Any) -> Dict[str, float]:
    c = str(bmi_category or "").strip().lower()
    base = {"calories": 1.8, "protein": 1.2, "carbs": 0.6, "fat": 0.6}
    if c == "underweight":
        return {"calories": 2.0, "protein": 1.35, "carbs": 0.55, "fat": 0.45}
    if c == "overweight":
        return {"calories": 1.8, "protein": 1.25, "carbs": 0.55, "fat": 0.95}
    if c == "obese":
        return {"calories": 1.85, "protein": 1.3, "carbs": 0.5, "fat": 1.05}
    return base

def _macro_score(macros: Dict[str, float], expected: Dict[str, float], weights: Dict[str, float]) -> float:
    return (
        weights["calories"] * _relative_error(macros.get("caloriesKcal", 0.0), expected.get("caloriesKcal", 0.0))
        + weights["protein"] * _relative_error(macros.get("proteinG", 0.0), expected.get("proteinG", 0.0))
        + weights["carbs"] * _relative_error(macros.get("carbsG", 0.0), expected.get("carbsG", 0.0))
        + weights["fat"] * _relative_error(macros.get("fatG", 0.0), expected.get("fatG", 0.0))
    )

def _preview_scaled_macros(macros: Dict[str, float], expected: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
    kcal = max(0.0, float(macros.get("caloriesKcal", 0.0) or 0.0))
    target_kcal = max(0.0, float(expected.get("caloriesKcal", 0.0) or 0.0))
    if kcal <= 0 or target_kcal <= 0:
        factor = 1.0
    else:
        requested = target_kcal / kcal
        factor = max(0.6, min(2.5, requested))

    scaled = {
        "caloriesKcal": macros.get("caloriesKcal", 0.0) * factor,
        "proteinG": macros.get("proteinG", 0.0) * factor,
        "carbsG": macros.get("carbsG", 0.0) * factor,
        "fatG": macros.get("fatG", 0.0) * factor,
        "fiberG": macros.get("fiberG", 0.0) * factor,
    }
    return factor, scaled

def _normalized_meal_distribution(meal_times: Optional[Iterable[str]]) -> Dict[str, float]:
    if not meal_times:
        return MEAL_DISTRIBUTION
    selected = [t for t in meal_times if t in MEAL_DISTRIBUTION]
    if not selected:
        return MEAL_DISTRIBUTION
    total = sum(MEAL_DISTRIBUTION[t] for t in selected)
    if total <= 0:
        return MEAL_DISTRIBUTION
    return {t: MEAL_DISTRIBUTION[t] / total for t in selected}

def session_target_macros(
    targets: Dict[str, Any],
    meal_time: str,
    meal_times: Optional[Iterable[str]] = None,
) -> Dict[str, float]:
    dist = _normalized_meal_distribution(meal_times)
    weight = dist.get(str(meal_time), 0.0)
    return {
        "caloriesKcal": float(targets.get("dailyCalories", 0.0)) * weight,
        "proteinG": float(targets.get("proteinG", 0.0)) * weight,
        "carbsG": float(targets.get("carbsG", 0.0)) * weight,
        "fatG": float(targets.get("fatG", 0.0)) * weight,
        "fiberG": float(targets.get("fiberG", 0.0)) * weight,
    }

def _rank_view(meal: Dict[str, Any], score: float, scaled_macros: Dict[str, float], scale_factor: float) -> Dict[str, Any]:
    return {
        "Meal_ID": meal.get("Meal_ID"),
        "meal_name": meal.get("meal_name"),
        "goal": meal.get("goal"),
        "meal_time": meal.get("meal_time"),
        "ingredients": meal.get("ingredients") or "",
        "method": meal.get("method") or "",
        "cuisine_type": meal.get("cuisine_type") or "",
        "country": meal.get("country") or "",
        "image_ID": meal.get("image_ID") or "",
        "diet_type": meal.get("diet_type"),
        "time": meal.get("time") or "",
        "serving_size": meal.get("serving_size") or "",
        "caution": meal.get("caution") or "",
        "nutritive_values": format_nutritive_values(scaled_macros),
        "_macros": scaled_macros,
        "_base_macros": meal.get("_macros") or {},
        "_score": score,
        "_scale_preview": scale_factor,
    }

def rank_meals_for_meal_time(
    *,
    profile: Dict[str, Any],
    meal_time: str,
    targets: Dict[str, Any],
    limit: int = 180,
    min_options: int = 7,
    allow_relax_goal: bool = True,
    allow_relax_diet: bool = False,
) -> Dict[str, Any]:
    if not targets:
        targets = calculate_daily_targets(profile)

    goal = normalize_goal(profile.get("goal"))
    diet_type = profile.get("dietType")
    allergy_keywords = split_keywords(profile.get("allergies"))
    expected = session_target_macros(targets, meal_time)

    weights = _macro_weights(targets.get("bmiCategory"))
    cuisine = profile.get("cuisineType") or "north_indian"
    all_meals = load_master_meals(cuisine)

    # Check if this cuisine has any image mappings at all. If not, bypass the filter.
    has_any_mapping = False
    for m in all_meals:
        for food in (m.get("foods_struct") or []):
            if str(food.get("image_url") or "").strip():
                has_any_mapping = True
                break
        if has_any_mapping:
            break

    def is_fully_imaged(meal: Dict[str, Any]) -> bool:
        if not has_any_mapping:
            return True
        foods = meal.get("foods_struct") or []
        if not foods:
            return False
        for food in foods:
            if not str(food.get("image_url") or "").strip():
                return False
        return True

    def score(meals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for m in meals:
            base_macros = m.get("_macros") or {}
            scale_factor, scaled_macros = _preview_scaled_macros(base_macros, expected)
            s = _macro_score(scaled_macros, expected, weights)
            out.append(_rank_view(m, s, scaled_macros, scale_factor))
        out.sort(key=lambda x: float(x.get("_score", 0.0)))
        return sorted(out, key=lambda x: float(x.get("_score", 0.0)))

    def goal_matches(meal: Dict[str, Any]) -> bool:
        if not goal:
            return True
        meal_goals = normalize_goal_list(meal.get("goal"))
        return not meal_goals or goal in meal_goals

    strict = [
        m
        for m in all_meals
        if str(m.get("meal_time")) == str(meal_time)
        and goal_matches(m)
        and _is_meal_allowed(m, diet_type=diet_type, allergy_keywords=allergy_keywords)
        and is_fully_imaged(m)
    ]

    ranked: List[Dict[str, Any]] = []
    seen: set[str] = set()

    def push_unique(items: List[Dict[str, Any]]):
        for m in items:
            mid = str(m.get("Meal_ID") or "")
            if not mid or mid in seen:
                continue
            seen.add(mid)
            ranked.append(m)
            if len(ranked) >= int(limit):
                break

    push_unique(score(strict))

    if allow_relax_goal and len(ranked) < int(min_options):
        relaxed_goal = [
            m
            for m in all_meals
            if str(m.get("meal_time")) == str(meal_time)
            and _is_meal_allowed(m, diet_type=diet_type, allergy_keywords=allergy_keywords)
            and is_fully_imaged(m)
        ]
        push_unique(score(relaxed_goal))

    if allow_relax_diet and len(ranked) < int(min_options) and str(diet_type or "any") not in {"any", ""}:
        relaxed_diet = [
            m
            for m in all_meals
            if str(m.get("meal_time")) == str(meal_time)
            and _is_meal_allowed(m, diet_type="any", allergy_keywords=allergy_keywords)
            and is_fully_imaged(m)
        ]
        push_unique(score(relaxed_diet))

    return {
        "targets": targets,
        "filters": {
            "goal": goal,
            "dietType": _normalize_diet_type(diet_type),
            "allergyKeywords": allergy_keywords,
        },
        "mealTime": meal_time,
        "ranked": ranked,
    }
