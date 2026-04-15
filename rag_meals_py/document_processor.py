from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class MealMacros:
    calories_kcal: float = 0.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0


_NUM = r"(?P<num>\d+(?:\.\d+)?)"

_RE_KCAL = re.compile(rf"{_NUM}\s*kcal", re.IGNORECASE)
_RE_PROTEIN = re.compile(rf"protein\s*{_NUM}\s*g", re.IGNORECASE)
_RE_CARBS = re.compile(rf"(?:carbs?|carbohydrates?)\s*{_NUM}\s*g", re.IGNORECASE)
_RE_FAT = re.compile(rf"fat\s*{_NUM}\s*g", re.IGNORECASE)
_RE_FIBER = re.compile(rf"(?:fiber|fibre)\s*{_NUM}\s*g", re.IGNORECASE)


def _to_float(match: re.Match | None) -> float:
    if not match:
        return 0.0
    try:
        return float(match.group("num"))
    except Exception:
        return 0.0


def parse_nutritive_values(text: str | None) -> MealMacros:
    """Parse the standardized `nutritive_values` text into numeric macros.

    Expected input examples:
        "360 kcal | Protein 24 g | Carbs 24 g | Fat 18 g"
        "210 kcal | Protein 2 g | Carbs 48 g | Fat 0 g"
    """
    if not text:
        return MealMacros()

    return MealMacros(
        calories_kcal=_to_float(_RE_KCAL.search(text)),
        protein_g=_to_float(_RE_PROTEIN.search(text)),
        carbs_g=_to_float(_RE_CARBS.search(text)),
        fat_g=_to_float(_RE_FAT.search(text)),
        fiber_g=_to_float(_RE_FIBER.search(text)),
    )


def normalize_tag(value: str | None) -> str:
    """Normalize a free-form label into a stable metadata token."""
    if not value:
        return ""
    v = value.strip().lower()
    v = re.sub(r"[^a-z0-9]+", "_", v)
    v = re.sub(r"_+", "_", v).strip("_")
    return v


def build_document_text(meal: Dict[str, Any]) -> str:
    parts: list[str] = []
    parts.append(f"Meal: {meal.get('meal_name', '')}")
    parts.append(f"Goal: {meal.get('goal', '')}")
    parts.append(f"Meal Time: {meal.get('meal_time', '')}")
    parts.append(f"Diet Type: {meal.get('diet_type', '')}")
    if meal.get("time"):
        parts.append(f"Time Window: {meal.get('time')}")
    if meal.get("serving_size"):
        parts.append(f"Serving Size: {meal.get('serving_size')}")
    if meal.get("ingredients"):
        parts.append(f"Ingredients: {meal.get('ingredients')}")
    if meal.get("method"):
        parts.append(f"Method: {meal.get('method')}")
    if meal.get("nutritive_values"):
        parts.append(f"Nutrition: {meal.get('nutritive_values')}")
    if meal.get("caution"):
        parts.append(f"Caution: {meal.get('caution')}")
    return "\n".join(parts)


def build_metadata(meal: Dict[str, Any]) -> Dict[str, Any]:
    macros = parse_nutritive_values(meal.get("nutritive_values"))

    # Keep metadata compact and filter-friendly.
    return {
        "meal_id": str(meal.get("Meal_ID", "")),
        "meal_name": str(meal.get("meal_name", "")),
        "goal": normalize_tag(str(meal.get("goal", ""))),
        "meal_time": str(meal.get("meal_time", "")),
        "diet_type": str(meal.get("diet_type", "")),
        "country": str(meal.get("country", "")),
        "cuisine_type": str(meal.get("cuisine_type", "")),
        "image_id": str(meal.get("image_ID", "")),
        "calories_kcal": float(macros.calories_kcal),
        "protein_g": float(macros.protein_g),
        "carbs_g": float(macros.carbs_g),
        "fat_g": float(macros.fat_g),
        "fiber_g": float(macros.fiber_g),
    }
