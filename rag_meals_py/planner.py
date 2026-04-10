from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .config import DEFAULT_TOP_K, MASTER_MEALS_PATH
from .document_processor import MealMacros, normalize_tag, parse_nutritive_values
from .ingest import ensure_ingested
from .vectorstore import get_collection

logger = logging.getLogger(__name__)


ACTIVITY_MULTIPLIERS: Dict[str, float] = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "heavy": 1.725,
}


# BMI-target mode constants
BMI_GOAL: float = 22.0

# General macro bounds (AMDR-style ranges are % of calories)
FAT_PERCENT_RANGE: Tuple[float, float] = (0.20, 0.35)
FIBER_G_PER_1000_KCAL: int = 14
FIBER_MIN_G_PER_DAY: int = 25
WATER_ML_PER_KG_RANGE: Tuple[int, int] = (30, 35)


MEAL_DISTRIBUTION: Dict[str, float] = {
    "early_morning": 0.05,
    "breakfast": 0.25,
    "mid_morning": 0.10,
    "lunch": 0.30,
    "evening": 0.10,
    "dinner": 0.15,
    "bedtime": 0.05,
}


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    if height_cm <= 0:
        return 22.0
    h_m = height_cm / 100.0
    return weight_kg / (h_m**2)


def bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25.0:
        return "Normal"
    if bmi < 30.0:
        return "Overweight"
    return "Obese"


def calculate_target_weight_kg(height_cm: float, target_bmi: float = BMI_GOAL) -> float:
    if height_cm <= 0:
        return 0.0
    h_m = height_cm / 100.0
    return target_bmi * (h_m**2)


def _protein_g_per_kg_target(category: str) -> float:
    c = (category or "").strip().lower()
    if c == "underweight":
        return 1.6
    if c == "normal":
        return 1.2
    if c == "overweight":
        return 1.4
    if c == "obese":
        return 1.6
    return 1.2


def _fat_percent_preset(category: str) -> Tuple[float, float, float]:
    """Return (min, max, default) fat percent of calories."""

    c = (category or "").strip().lower()
    if c == "underweight":
        return (0.25, 0.35, 0.32)
    if c == "normal":
        return (0.25, 0.35, 0.28)
    if c == "overweight":
        return (0.20, 0.30, 0.22)
    if c == "obese":
        return (0.20, 0.30, 0.20)
    return (FAT_PERCENT_RANGE[0], FAT_PERCENT_RANGE[1], 0.25)


def calculate_bmr_mifflin_st_jeor(*, weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """BMR (kcal/day) using Mifflin-St Jeor."""
    g = (gender or "").strip().lower()
    is_male = g in {"male", "m", "man"}
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + (5 if is_male else -161)


def calculate_bmr_harris_benedict(*, weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """BMR (kcal/day) using Harris-Benedict (as in the provided PPT)."""

    g = (gender or "").strip().lower()
    is_male = g in {"male", "m", "man"}
    if is_male:
        return 66 + (13.7 * weight_kg) + (5 * height_cm) - (6.8 * age)
    return 655 + (9.6 * weight_kg) + (1.8 * height_cm) - (4.7 * age)


def normalize_activity_level(activity_level: str | None) -> str:
    if not activity_level:
        return "sedentary"

    v = activity_level.strip().lower()
    v = v.replace("/", " ").replace("-", " ")
    v = re.sub(r"\s+", " ", v).strip()

    mapping = {
        "sedentary": "sedentary",
        "desk job": "sedentary",
        "light": "light",
        "light active": "light",
        "lightly active": "light",
        "1 2 days week": "light",
        "1-2 days/week": "light",
        "moderate": "moderate",
        "moderate active": "moderate",
        "moderately active": "moderate",
        "3 5 days week": "moderate",
        "3-5 days/week": "moderate",
        "heavy": "heavy",
        "very active worker": "heavy",
        "very active": "heavy",
        "active": "heavy",
        "heavy active": "heavy",
    }

    # Fuzzy keys: remove punctuation
    compact = re.sub(r"[^a-z0-9]+", " ", v)
    compact = re.sub(r"\s+", " ", compact).strip()

    return mapping.get(v) or mapping.get(compact) or "sedentary"


def calculate_tdee(*, bmr_kcal: float, activity_level: str | None) -> float:
    activity = normalize_activity_level(activity_level)
    multiplier = ACTIVITY_MULTIPLIERS.get(activity, ACTIVITY_MULTIPLIERS["sedentary"])
    return bmr_kcal * multiplier


def calculate_daily_targets(
    *,
    age: int,
    gender: str,
    height_cm: float,
    weight_kg: float,
    activity_level: str | None,
    goal: str | None = None,
    timeline: str | None = None,
) -> Dict[str, Any]:
    """Compute BMI/BMR/TDEE and macro targets.

    BMI-target mode:
        - Target BMI is fixed at 22.
        - Target weight is derived from height and BMI=22.
                - Timeline-based calorie adjustment is not used.
                    (The `timeline` parameter is accepted for backward compatibility but ignored.)
        - Protein/fat/carbs and water are computed from the target weight.

    References for constants are documented in Diet Plan/README.md.
    """

    bmi_value = calculate_bmi(weight_kg, height_cm)
    bmi = round(bmi_value, 1)
    category = bmi_category(bmi_value)
    bmr = calculate_bmr_harris_benedict(weight_kg=weight_kg, height_cm=height_cm, age=age, gender=gender)
    tdee = calculate_tdee(bmr_kcal=bmr, activity_level=activity_level)

    maintenance_calories = int(round(tdee))

    target_weight = round(calculate_target_weight_kg(height_cm, BMI_GOAL), 1)
    weight_delta_kg = round(target_weight - weight_kg, 1)

    calories_i = int(round(max(1200.0, maintenance_calories)))

    protein_g = int(round(target_weight * _protein_g_per_kg_target(category)))

    fat_min_p, fat_max_p, fat_default_p = _fat_percent_preset(category)
    fat_g = int(round((calories_i * fat_default_p) / 9.0))
    fat_g_min = int(round((calories_i * fat_min_p) / 9.0))
    fat_g_max = int(round((calories_i * fat_max_p) / 9.0))

    remaining_calories = max(0, calories_i - protein_g * 4 - fat_g * 9)
    carbs_g = int(round(remaining_calories / 4.0))
    carbs_g_min = int(round(max(0, calories_i - protein_g * 4 - fat_g_max * 9) / 4.0))
    carbs_g_max = int(round(max(0, calories_i - protein_g * 4 - fat_g_min * 9) / 4.0))

    fiber_g_raw = int(round((calories_i / 1000.0) * FIBER_G_PER_1000_KCAL))
    fiber_g = max(FIBER_MIN_G_PER_DAY, fiber_g_raw)

    water_l_min = round(target_weight * (WATER_ML_PER_KG_RANGE[0] / 1000.0), 2)
    water_l_max = round(target_weight * (WATER_ML_PER_KG_RANGE[1] / 1000.0), 2)
    water_l = round(target_weight * 0.033, 2)

    return {
        "bmi": bmi,
        "bmi_category": category,
        "target_bmi": BMI_GOAL,
        "target_weight_kg": target_weight,
        "weight_delta_kg": weight_delta_kg,
        "bmr": int(round(bmr)),
        "tdee": int(round(tdee)),
        "maintenance_calories": maintenance_calories,
        "daily_calories": calories_i,
        "daily_protein_g": protein_g,
        "daily_carbs_g": carbs_g,
        "daily_fat_g": fat_g,
        "daily_fat_g_min": fat_g_min,
        "daily_fat_g_max": fat_g_max,
        "daily_carbs_g_min": carbs_g_min,
        "daily_carbs_g_max": carbs_g_max,
        "daily_fiber_g": fiber_g,
        "daily_fiber_g_raw": fiber_g_raw,
        "daily_fiber_g_minimum": FIBER_MIN_G_PER_DAY,
        "daily_water_l": water_l,
        "daily_water_l_min": water_l_min,
        "daily_water_l_max": water_l_max,
        "activity_level_normalized": normalize_activity_level(activity_level),
    }


@lru_cache(maxsize=1)
def _load_master_meals() -> List[Dict[str, Any]]:
    import json

    with open(MASTER_MEALS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("master_meals_updated.json must be a list")
    return data


@lru_cache(maxsize=1)
def _meals_by_id() -> Dict[str, Dict[str, Any]]:
    return {str(m.get("Meal_ID")): m for m in _load_master_meals() if m.get("Meal_ID")}


def _parse_allergy_keywords(allergies: str | Iterable[str] | None) -> List[str]:
    if not allergies:
        return []

    if isinstance(allergies, str):
        parts = re.split(r"[,;/]|\band\b", allergies.lower())
        return [p.strip() for p in parts if p.strip()]

    keywords: List[str] = []
    for item in allergies:
        if item:
            keywords.append(str(item).strip().lower())
    return [k for k in keywords if k]


def _contains_any_keyword(haystack: str, keywords: List[str]) -> bool:
    if not haystack or not keywords:
        return False
    h = haystack.lower()
    return any(k in h for k in keywords)


def _meal_safe_for_allergies(meal: Dict[str, Any], allergy_keywords: List[str]) -> bool:
    if not allergy_keywords:
        return True

    # Basic string containment on ingredients + caution.
    combined = f"{meal.get('ingredients','')}\n{meal.get('caution','')}"
    return not _contains_any_keyword(combined, allergy_keywords)


def _meal_time_candidates(
    *,
    goal: str,
    meal_time: str,
    diet_type: str | None,
    query: str,
    top_k: int,
    allergy_keywords: List[str],
) -> List[Dict[str, Any]]:
    collection = get_collection()

    goal_tag = normalize_tag(goal)
    where: Dict[str, Any] = {"meal_time": meal_time}
    if goal_tag:
        where["goal"] = goal_tag
    if diet_type and diet_type.strip().lower() == "veg":
        where["diet_type"] = "veg"

    results = collection.query(query_texts=[query], n_results=top_k, where=where)

    ids = (results.get("ids") or [[]])[0]
    metas = (results.get("metadatas") or [[]])[0]

    by_id = _meals_by_id()
    candidates: List[Dict[str, Any]] = []
    for mid, meta in zip(ids, metas):
        meal = by_id.get(mid)
        if not meal:
            continue
        if not _meal_safe_for_allergies(meal, allergy_keywords):
            continue

        # Attach parsed macros for planning/scoring.
        macros = parse_nutritive_values(meal.get("nutritive_values"))
        candidates.append(
            {
                "Meal_ID": meal.get("Meal_ID"),
                "meal_name": meal.get("meal_name"),
                "meal_time": meal.get("meal_time"),
                "time": meal.get("time"),
                "ingredients": meal.get("ingredients"),
                "method": meal.get("method"),
                "serving_size": meal.get("serving_size"),
                "caution": meal.get("caution"),
                "diet_type": meal.get("diet_type"),
                "goal": meal.get("goal"),
                "nutritive_values": meal.get("nutritive_values"),
                "macros": macros,
            }
        )

    return candidates


@dataclass(frozen=True)
class PlanTotals:
    calories_kcal: float = 0.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0

    def add(self, m: MealMacros) -> "PlanTotals":
        return PlanTotals(
            calories_kcal=self.calories_kcal + (m.calories_kcal or 0.0),
            protein_g=self.protein_g + (m.protein_g or 0.0),
            carbs_g=self.carbs_g + (m.carbs_g or 0.0),
            fat_g=self.fat_g + (m.fat_g or 0.0),
        )


@dataclass(frozen=True)
class BeamState:
    chosen: Dict[str, Dict[str, Any]]
    totals: PlanTotals
    used_weight: float


def _relative_error(actual: float, target: float) -> float:
    if target <= 0:
        return 0.0 if actual <= 0 else 1.0
    return abs(actual - target) / target


def _partial_score(
    totals: PlanTotals,
    *,
    targets: PlanTotals,
    used_weight: float,
) -> float:
    # Expected totals for the portion of the day covered so far.
    expected = PlanTotals(
        calories_kcal=targets.calories_kcal * used_weight,
        protein_g=targets.protein_g * used_weight,
        carbs_g=targets.carbs_g * used_weight,
        fat_g=targets.fat_g * used_weight,
    )

    # Calories dominate, macros provide secondary signal.
    return (
        2.0 * _relative_error(totals.calories_kcal, expected.calories_kcal)
        + 0.8 * _relative_error(totals.protein_g, expected.protein_g)
        + 0.6 * _relative_error(totals.carbs_g, expected.carbs_g)
        + 0.6 * _relative_error(totals.fat_g, expected.fat_g)
    )


def _final_score(totals: PlanTotals, targets: PlanTotals) -> float:
    return (
        2.0 * _relative_error(totals.calories_kcal, targets.calories_kcal)
        + 0.8 * _relative_error(totals.protein_g, targets.protein_g)
        + 0.6 * _relative_error(totals.carbs_g, targets.carbs_g)
        + 0.6 * _relative_error(totals.fat_g, targets.fat_g)
    )


def generate_daily_plan(
    *,
    age: int,
    gender: str,
    height_cm: float,
    weight_kg: float,
    activity_level: str | None,
    timeline: str | None = None,
    goal: str,
    diet_type: str | None = None,
    allergies: str | Iterable[str] | None = None,
    top_k: int = DEFAULT_TOP_K,
    beam_size: int = 40,
    per_meal_candidates: int = 15,
) -> Dict[str, Any]:
    """Generate a single-day meal plan close to the user's macro targets."""

    ingest_stats = ensure_ingested()

    targets_dict = calculate_daily_targets(
        age=age,
        gender=gender,
        height_cm=height_cm,
        weight_kg=weight_kg,
        activity_level=activity_level,
        goal=goal,
        timeline=timeline,
    )

    targets = PlanTotals(
        calories_kcal=float(targets_dict["daily_calories"]),
        protein_g=float(targets_dict["daily_protein_g"]),
        carbs_g=float(targets_dict["daily_carbs_g"]),
        fat_g=float(targets_dict["daily_fat_g"]),
    )

    allergy_keywords = _parse_allergy_keywords(allergies)

    # Candidate retrieval per meal time.
    candidates_by_time: Dict[str, List[Dict[str, Any]]] = {}
    for meal_time in MEAL_DISTRIBUTION:
        query = f"{goal} {meal_time} {'vegetarian' if (diet_type or '').lower()=='veg' else ''}"
        cands = _meal_time_candidates(
            goal=goal,
            meal_time=meal_time,
            diet_type=diet_type,
            query=query.strip(),
            top_k=top_k,
            allergy_keywords=allergy_keywords,
        )

        # Fallback: relax diet filter if we got nothing.
        if not cands and (diet_type or "").lower() == "veg":
            cands = _meal_time_candidates(
                goal=goal,
                meal_time=meal_time,
                diet_type=None,
                query=f"{goal} {meal_time}",
                top_k=top_k,
                allergy_keywords=allergy_keywords,
            )

        # As a last resort, relax goal.
        if not cands:
            cands = _meal_time_candidates(
                goal="",
                meal_time=meal_time,
                diet_type=None,
                query=f"{meal_time} meal",
                top_k=top_k,
                allergy_keywords=allergy_keywords,
            )

        candidates_by_time[meal_time] = cands[:per_meal_candidates]

    # Beam search across meal-times.
    beam: List[BeamState] = [BeamState(chosen={}, totals=PlanTotals(), used_weight=0.0)]

    for meal_time, weight in MEAL_DISTRIBUTION.items():
        options = candidates_by_time.get(meal_time) or []
        if not options:
            continue

        new_beam: List[Tuple[float, BeamState]] = []
        for state in beam:
            for meal in options:
                macros: MealMacros = meal["macros"]
                totals = state.totals.add(macros)
                used_weight = state.used_weight + weight
                chosen = dict(state.chosen)
                chosen[meal_time] = meal
                score = _partial_score(totals, targets=targets, used_weight=used_weight)
                new_beam.append((score, BeamState(chosen=chosen, totals=totals, used_weight=used_weight)))

        new_beam.sort(key=lambda t: t[0])
        beam = [s for _, s in new_beam[:beam_size]]

    # Pick best final candidate.
    best = min(beam, key=lambda s: _final_score(s.totals, targets))

    plan: Dict[str, Any] = {}
    for meal_time, meal in best.chosen.items():
        macros: MealMacros = meal["macros"]
        plan[meal_time] = {
            "Meal_ID": meal["Meal_ID"],
            "name": meal["meal_name"],
            "time": meal.get("time", ""),
            "ingredients": meal.get("ingredients", ""),
            "method": meal.get("method", ""),
            "serving_size": meal.get("serving_size", ""),
            "caution": meal.get("caution", ""),
            "diet_type": meal.get("diet_type", ""),
            "goal": meal.get("goal", ""),
            "nutritive_values": meal.get("nutritive_values", ""),
            "calories": int(round(macros.calories_kcal)),
            "protein": float(macros.protein_g),
            "carbs": float(macros.carbs_g),
            "fat": float(macros.fat_g),
            "fiber": float(macros.fiber_g),
        }

    totals_out = {
        "calories": int(round(best.totals.calories_kcal)),
        "protein_g": float(round(best.totals.protein_g, 1)),
        "carbs_g": float(round(best.totals.carbs_g, 1)),
        "fat_g": float(round(best.totals.fat_g, 1)),
    }

    return {
        "ingest": ingest_stats,
        "targets": targets_dict,
        "plan": plan,
        "totals": totals_out,
        "distribution": MEAL_DISTRIBUTION,
        "filters": {
            "goal": goal,
            "diet_type": diet_type or "",
            "allergies": allergy_keywords,
        },
    }
