from copy import deepcopy
from typing import Any, Dict, Iterable, List
from utils.parsers import _to_number
from utils.formatters import _fmt_num, format_nutritive_values

MACRO_KEYS = ["caloriesKcal", "proteinG", "carbsG", "fatG", "fiberG"]

def _f(v: Any) -> float:
    return _to_number(v, 0.0)

def clamp(x: float, low: float, high: float) -> float:
    return max(low, min(high, x))

from exceptions.domain import NutritionCalculationException

def ensure_macros(macros: Dict[str, Any] | None) -> Dict[str, float]:
    m = macros or {}
    out = {
        "caloriesKcal": _f(m.get("caloriesKcal", 0.0)),
        "proteinG": _f(m.get("proteinG", 0.0)),
        "carbsG": _f(m.get("carbsG", 0.0)),
        "fatG": _f(m.get("fatG", 0.0)),
        "fiberG": _f(m.get("fiberG", 0.0)),
    }
    for k, v in out.items():
        if v < 0:
            raise NutritionCalculationException(f"Negative value detected for macro key '{k}': {v}")
    return out

def scale_macros(macros: Dict[str, Any], factor: float) -> Dict[str, float]:
    base = ensure_macros(macros)
    f = float(factor)
    return {k: base[k] * f for k in MACRO_KEYS}

def sum_ingredient_macros(ingredients: Iterable[Dict[str, Any]]) -> Dict[str, float]:
    out = {k: 0.0 for k in MACRO_KEYS}
    for ing in ingredients:
        m = ensure_macros((ing or {}).get("macros") or {})
        for k in MACRO_KEYS:
            out[k] += m[k]
    return out

def sum_food_macros(foods: Iterable[Dict[str, Any]]) -> Dict[str, float]:
    out = {k: 0.0 for k in MACRO_KEYS}
    for food in foods:
        m = ensure_macros((food or {}).get("macros") or {})
        for k in MACRO_KEYS:
            out[k] += m[k]
    return out

def ingredient_to_text(ing: Dict[str, Any]) -> str:
    name = str((ing or {}).get("name") or "").strip()
    qty = _f((ing or {}).get("quantity", 0.0))
    unit = str((ing or {}).get("unit") or "").strip()
    if not name:
        return ""
    if qty > 0:
        return f"{name} {_fmt_num(qty)} {unit}".strip()
    return name

def ingredients_to_text(ingredients: Iterable[Dict[str, Any]]) -> str:
    out: List[str] = []
    for ing in ingredients:
        token = ingredient_to_text(ing)
        if token:
            out.append(token)
    return ", ".join(out)

def recompute_meal_from_ingredients(meal: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(meal)
    ingredients = list(out.get("ingredients_struct") or [])
    totals = sum_ingredient_macros(ingredients)
    out["_macros"] = totals
    out["macros"] = totals
    out["nutritive_values"] = format_nutritive_values(totals)
    out["ingredients"] = ingredients_to_text(ingredients)
    return out

def recompute_meal_from_foods(meal: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(meal)
    foods = list(out.get("foods_struct") or [])
    ingredients: List[Dict[str, Any]] = []
    for food in foods:
        for ing in food.get("ingredients_struct") or []:
            flat = deepcopy(ing)
            if food.get("id"):
                flat["food_id"] = food.get("id")
            if food.get("name"):
                flat["food_name"] = food.get("name")
            ingredients.append(flat)

    totals = sum_food_macros(foods)
    out["ingredients_struct"] = ingredients
    out["_macros"] = totals
    out["macros"] = totals
    out["nutritive_values"] = format_nutritive_values(totals)
    out["ingredients"] = ingredients_to_text(ingredients)
    return out

def _scale_ingredient(
    ing: Dict[str, Any],
    *,
    factor: float,
    ingredient_min_ratio: float,
    ingredient_max_ratio: float,
) -> Dict[str, Any]:
    out = deepcopy(ing)
    base_qty = _f(out.get("quantity", 0.0))
    if base_qty < 0:
        raise NutritionCalculationException("Negative ingredient quantity detected")

    if base_qty > 0:
        req = base_qty * factor
        low = base_qty * ingredient_min_ratio
        high = base_qty * ingredient_max_ratio
        next_qty = clamp(req, low, high)
        qty_factor = next_qty / base_qty if base_qty > 0 else factor
        out["quantity"] = next_qty
    else:
        qty_factor = factor

    out["macros"] = scale_macros(out.get("macros") or {}, qty_factor)
    return out

def scale_meal_to_targets(
    meal: Dict[str, Any],
    target_macros: Dict[str, Any],
    *,
    min_scale: float = 0.6,
    max_scale: float = 2.5,
    ingredient_min_ratio: float = 0.5,
    ingredient_max_ratio: float = 2.5,
) -> Dict[str, Any]:
    base = deepcopy(meal)
    base_macros = ensure_macros(base.get("_macros") or base.get("macros") or {})
    if base_macros["caloriesKcal"] <= 0 and base.get("foods_struct"):
        base = recompute_meal_from_foods(base)
        base_macros = ensure_macros(base.get("_macros") or {})
    if base_macros["caloriesKcal"] <= 0 and base.get("ingredients_struct"):
        base = recompute_meal_from_ingredients(base)
        base_macros = ensure_macros(base.get("_macros") or {})

    target = ensure_macros(target_macros)
    if target.get("caloriesKcal", 0.0) < 0:
        raise NutritionCalculationException("Target calories cannot be negative")

    foods = base.get("foods_struct") or []
    ingredients = base.get("ingredients_struct") or []
    if not foods and not ingredients and base_macros["caloriesKcal"] <= 0:
        raise NutritionCalculationException("Invalid meal composition: no foods, ingredients, or base calories present to scale")

    base_kcal = base_macros["caloriesKcal"]
    target_kcal = target["caloriesKcal"]

    if base_kcal > 0 and target_kcal > 0:
        scale_factor_requested = target_kcal / base_kcal
    else:
        scale_factor_requested = 1.0

    scale_factor_applied = clamp(scale_factor_requested, min_scale, max_scale)

    scaled = deepcopy(base)
    foods = list(scaled.get("foods_struct") or [])
    if foods:
        scaled_foods: List[Dict[str, Any]] = []
        for food in foods:
            base_qty = _f(food.get("quantity", 0.0))
            req = base_qty * scale_factor_applied

            low = _f(food.get("min_quantity", 0.0))
            high = _f(food.get("max_quantity", 0.0))
            if low > 0 or high > 0:
                low = low if low > 0 else req
                high = high if high > 0 else req
                next_qty = clamp(req, low, high)
            else:
                next_qty = req

            qty_factor = next_qty / base_qty if base_qty > 0 else scale_factor_applied

            next_food = deepcopy(food)
            next_food["quantity"] = next_qty

            scaled_ingredients = [
                _scale_ingredient(
                    ing,
                    factor=qty_factor,
                    ingredient_min_ratio=ingredient_min_ratio,
                    ingredient_max_ratio=ingredient_max_ratio,
                )
                for ing in (food.get("ingredients_struct") or [])
            ]

            next_food["ingredients_struct"] = scaled_ingredients
            next_food["macros"] = sum_ingredient_macros(scaled_ingredients)
            scaled_foods.append(next_food)

        scaled["foods_struct"] = scaled_foods
        scaled = recompute_meal_from_foods(scaled)
    else:
        ingredients = list(scaled.get("ingredients_struct") or [])
        if ingredients:
            scaled_ingredients = [
                _scale_ingredient(
                    ing,
                    factor=scale_factor_applied,
                    ingredient_min_ratio=ingredient_min_ratio,
                    ingredient_max_ratio=ingredient_max_ratio,
                )
                for ing in ingredients
            ]
            scaled["ingredients_struct"] = scaled_ingredients
            scaled = recompute_meal_from_ingredients(scaled)
        else:
            scaled_macros = scale_macros(base_macros, scale_factor_applied)
            scaled["_macros"] = scaled_macros
            scaled["macros"] = scaled_macros
            scaled["nutritive_values"] = format_nutritive_values(scaled_macros)

    return {
        "scaleFactorRequested": scale_factor_requested,
        "scaleFactorApplied": scale_factor_applied,
        "scaledMeal": scaled,
    }
