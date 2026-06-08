from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


MEAL_DISTRIBUTION: Dict[str, float] = {
    "early_morning": 0.05,
    "breakfast": 0.3,
    "mid_morning": 0.1,
    "lunch": 0.25,
    "evening": 0.1,
    "dinner": 0.15,
    "bedtime": 0.05,
}

MEAL_TIME_ORDER: List[str] = list(MEAL_DISTRIBUTION.keys())


def _diet_plan_root() -> Path:
    # Diet Plan/backend/studio/meals.py -> studio -> backend -> Diet Plan
    return Path(__file__).resolve().parents[2]


def _data_path(*parts: str) -> Path:
    return _diet_plan_root().joinpath(*parts)


def normalize_tag(value: Any) -> str:
    s = str(value or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s)
    s = re.sub(r"^_+|_+$", "", s)
    return s


def normalize_goal(goal: Any) -> str:
    g = normalize_tag(goal)
    if g == "skin_repair":
        return "skin_repair"
    if g == "hair_repair":
        return "hair_repair"
    return g


def split_keywords(raw: Any) -> List[str]:
    s = str(raw or "").lower()
    parts = re.split(r"[,;/]|\band\b", s)
    return [p.strip() for p in parts if p and p.strip()]


def _to_number(x: Any) -> float:
    try:
        n = float(x)
    except Exception:
        return 0.0
    return n if n == n and n != float("inf") and n != float("-inf") else 0.0


def parse_nutritive_values(text: Any) -> Dict[str, float]:
    t = str(text or "")

    def m(rx: str) -> float:
        match = re.search(rx, t, flags=re.IGNORECASE)
        return _to_number(match.group(1)) if match else 0.0

    return {
        "caloriesKcal": m(r"(\d+(?:\.\d+)?)\s*kcal"),
        "proteinG": m(r"protein\s*(\d+(?:\.\d+)?)\s*g"),
        "carbsG": m(r"(?:carbs?|carbohydrates?)\s*(\d+(?:\.\d+)?)\s*g"),
        "fatG": m(r"fat\s*(\d+(?:\.\d+)?)\s*g"),
        "fiberG": m(r"(?:fiber|fibre)\s*(\d+(?:\.\d+)?)\s*g"),
    }


def _normalize_diet_type_for_filtering(diet_type: Any) -> str:
    dt = str(diet_type or "").strip().lower()
    if dt == "veg":
        return "veg"
    if dt in {"non_veg", "non-veg", "nonveg"}:
        return "any"
    if dt == "any":
        return "any"
    return "any"


def _contains_any(haystack: Any, keywords: List[str]) -> bool:
    if not haystack or not keywords:
        return False
    h = str(haystack).lower()
    return any(k and k in h for k in keywords)


def _is_probably_non_veg(meal: Dict[str, Any]) -> bool:
    text = f"{meal.get('ingredients','')}\n{meal.get('meal_name','')}".lower()

    patterns: List[Tuple[re.Pattern[str], Optional[re.Pattern[str]]]] = [
        (re.compile(r"\beggs?\b", re.I), re.compile(r"\beggless\b", re.I)),
        (re.compile(r"\bchicken\b", re.I), None),
        (re.compile(r"\bfish\b", re.I), None),
        (re.compile(r"\bmutton\b", re.I), None),
        (re.compile(r"\blamb\b", re.I), None),
        (re.compile(r"\b(?:prawn|shrimp|shrimps)\b", re.I), None),
        (re.compile(r"\bmeat\b", re.I), re.compile(r"\bmeatless\b", re.I)),
    ]

    for rx, neg in patterns:
        if rx.search(text) and not (neg and neg.search(text)):
            return True
    return False


def _is_meal_allowed(meal: Dict[str, Any], *, diet_type: Any, allergy_keywords: List[str]) -> bool:
    if allergy_keywords:
        combined = f"{meal.get('ingredients','')}\n{meal.get('caution','')}"
        if _contains_any(combined, allergy_keywords):
            return False

    dt_filter = _normalize_diet_type_for_filtering(diet_type)
    if dt_filter == "veg":
        dt = str(meal.get("diet_type") or "").lower()
        if dt == "non_veg":
            return False
        if dt == "" and _is_probably_non_veg(meal):
            return False

    return True


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
    w = weights
    return (
        w["calories"] * _relative_error(macros.get("caloriesKcal", 0.0), expected.get("caloriesKcal", 0.0))
        + w["protein"] * _relative_error(macros.get("proteinG", 0.0), expected.get("proteinG", 0.0))
        + w["carbs"] * _relative_error(macros.get("carbsG", 0.0), expected.get("carbsG", 0.0))
        + w["fat"] * _relative_error(macros.get("fatG", 0.0), expected.get("fatG", 0.0))
    )


@lru_cache(maxsize=1)
def load_master_meals() -> List[Dict[str, Any]]:
    path = _data_path("data", "master_meals_updated.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []

    out: List[Dict[str, Any]] = []
    for m in data:
        if not isinstance(m, dict):
            continue
        macros = parse_nutritive_values(m.get("nutritive_values"))
        mm = dict(m)
        mm["_macros"] = macros
        out.append(mm)
    return out


@lru_cache(maxsize=1)
def meal_index_by_id() -> Dict[str, Dict[str, Any]]:
    idx: Dict[str, Dict[str, Any]] = {}
    for m in load_master_meals():
        mid = m.get("Meal_ID")
        if mid is None:
            continue
        key = str(mid)
        if key and key not in idx:
            idx[key] = m
    return idx


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
    from .nutrition import calculate_daily_targets

    if not targets:
        targets = calculate_daily_targets(profile)

    goal = normalize_goal(profile.get("goal"))
    diet_type = profile.get("dietType")
    allergy_keywords = split_keywords(profile.get("allergies"))

    weight = MEAL_DISTRIBUTION.get(str(meal_time), 0.0)

    expected = {
        "caloriesKcal": float(targets.get("dailyCalories", 0.0)) * weight,
        "proteinG": float(targets.get("proteinG", 0.0)) * weight,
        "carbsG": float(targets.get("carbsG", 0.0)) * weight,
        "fatG": float(targets.get("fatG", 0.0)) * weight,
    }

    weights = _macro_weights(targets.get("bmiCategory"))
    all_meals = load_master_meals()

    def score(meals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for m in meals:
            macros = m.get("_macros") or {}
            out.append({**m, "_score": _macro_score(macros, expected, weights)})
        out.sort(key=lambda x: float(x.get("_score", 0.0)))
        return out

    strict = [
        m
        for m in all_meals
        if str(m.get("meal_time")) == str(meal_time)
        and normalize_goal(m.get("goal")) == goal
        and _is_meal_allowed(m, diet_type=diet_type, allergy_keywords=allergy_keywords)
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
        ]
        push_unique(score(relaxed_goal))

    if allow_relax_diet and len(ranked) < int(min_options) and str(diet_type or "any") not in {"any", ""}:
        relaxed_diet = [
            m
            for m in all_meals
            if str(m.get("meal_time")) == str(meal_time)
            and _is_meal_allowed(m, diet_type="any", allergy_keywords=allergy_keywords)
        ]
        push_unique(score(relaxed_diet))

    return {
        "targets": targets,
        "filters": {
            "goal": goal,
            "dietType": _normalize_diet_type_for_filtering(diet_type),
            "allergyKeywords": allergy_keywords,
        },
        "mealTime": meal_time,
        "ranked": ranked,
    }
