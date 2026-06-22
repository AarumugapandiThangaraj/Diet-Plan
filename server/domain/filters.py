import re
from typing import Any, Dict, List, Tuple
from utils.normalizers import _normalize_diet_type

def _is_probably_non_veg(meal: Dict[str, Any]) -> bool:
    ingredient_names = " ".join(str(x.get("name") or "") for x in meal.get("ingredients_struct") or [])
    text = f"{meal.get('ingredients', '')}\n{meal.get('meal_name', '')}\n{ingredient_names}".lower()

    patterns: List[Tuple[re.Pattern[str], Any]] = [
        (re.compile(r"\beggs?\b", re.I), re.compile(r"\beggless\b", re.I)),
        (re.compile(r"\bchicken\b", re.I), None),
        (re.compile(r"\bfish\b", re.I), None),
        (re.compile(r"\bmutton\b", re.I), None),
        (re.compile(r"\blamb\b", re.I), None),
        (re.compile(r"\b(?:prawn|shrimp|shrimps)\b", re.I), None),
        (re.compile(r"\bbeef\b", re.I), None),
        (re.compile(r"\bpork\b", re.I), None),
        (re.compile(r"\bpepperoni\b", re.I), None),
        (re.compile(r"\bchorizo\b", re.I), None),
        (re.compile(r"\bmeat\b", re.I), re.compile(r"\bmeatless\b", re.I)),
    ]

    for rx, neg in patterns:
        if rx.search(text) and not (neg and neg.search(text)):
            return True
    return False

def _contains_any(haystack: Any, keywords: List[str]) -> bool:
    if not haystack or not keywords:
        return False
    h = str(haystack).lower()
    return any(k and k in h for k in keywords)

def _is_meal_allowed(meal: Dict[str, Any], *, diet_type: Any, allergy_keywords: List[str]) -> bool:
    if allergy_keywords:
        ingredient_names = ", ".join(str(x.get("name") or "") for x in meal.get("ingredients_struct") or [])
        combined = f"{meal.get('ingredients', '')}\n{ingredient_names}\n{meal.get('caution', '')}"
        if _contains_any(combined, allergy_keywords):
            return False

    dt_filter = _normalize_diet_type(diet_type)
    if dt_filter == "veg":
        dt = _normalize_diet_type(meal.get("diet_type"))
        if dt == "non_veg":
            return False
        if dt in {"", "any"} and _is_probably_non_veg(meal):
            return False

    return True
