from typing import Any, Dict, Iterable, List
from utils.clone import fast_clone_meal, fast_clone_food, fast_clone_ingredient
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
    from domain.payload_models import MealPayload
    try:
        m = MealPayload(**meal)
        m.recalculate_macros()
        out = m.model_dump(by_alias=True, exclude_unset=True)
        out["nutritive_values"] = format_nutritive_values(out.get("_macros") or {})
        out["ingredients"] = ingredients_to_text(out.get("ingredients_struct") or [])
        return out
    except Exception:
        out = fast_clone_meal(meal)
        ingredients = list(out.get("ingredients_struct") or [])
        totals = sum_ingredient_macros(ingredients)
        out["_macros"] = totals
        out["macros"] = totals
        out["nutritive_values"] = format_nutritive_values(totals)
        out["ingredients"] = ingredients_to_text(ingredients)
        return out

def recompute_meal_from_foods(meal: Dict[str, Any]) -> Dict[str, Any]:
    from domain.payload_models import MealPayload
    try:
        m = MealPayload(**meal)
        m.recalculate_macros()
        out = m.model_dump(by_alias=True, exclude_unset=True)
        out["nutritive_values"] = format_nutritive_values(out.get("_macros") or {})
        
        flat_ingredients = []
        for food in out.get("foods_struct") or []:
            for ing in food.get("ingredients_struct") or []:
                flat_ing = fast_clone_ingredient(ing)
                flat_ing["food_id"] = food.get("id")
                flat_ing["food_name"] = food.get("name")
                flat_ingredients.append(flat_ing)
        out["ingredients_struct"] = flat_ingredients
        out["ingredients"] = ingredients_to_text(flat_ingredients)
        return out
    except Exception:
        out = fast_clone_meal(meal)
        foods = list(out.get("foods_struct") or [])
        ingredients: List[Dict[str, Any]] = []
        for food in foods:
            for ing in food.get("ingredients_struct") or []:
                flat = fast_clone_ingredient(ing)
                if food.get("id"):
                    flat["food_id"] = food.get("id")
                if food.get("name"):
                    flat["food_name"] = food.get("name")
                ingredients.append(flat)

        totals = sum_food_macros(foods)
        out["ingredients_struct"] = ingredients
        
        base_macros = out.get("_macros") or out.get("macros") or {}
        if totals.get("caloriesKcal", 0) <= 0 and base_macros.get("caloriesKcal", 0) > 0:
            pass # preserve existing macros
        else:
            out["_macros"] = totals
            out["macros"] = totals
            
        out["nutritive_values"] = format_nutritive_values(out.get("macros", {}))
        out["ingredients"] = ingredients_to_text(ingredients)
        return out

def _scale_ingredient(
    ing: Dict[str, Any],
    *,
    factor: float,
    ingredient_min_ratio: float,
    ingredient_max_ratio: float,
) -> Dict[str, Any]:
    out = fast_clone_ingredient(ing)
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

def scale_meal_payload_to_targets(
    meal: Any,
    target_macros: Any,
) -> tuple[float, float, Any]:
    base = meal.model_copy(deep=True)
    if base.macros.caloriesKcal <= 0 and base.foods_struct:
        base.recalculate_macros()

    base_kcal = base.macros.caloriesKcal
    target_kcal = target_macros.caloriesKcal

    if target_kcal < 0:
        raise NutritionCalculationException("Target calories cannot be negative")

    if not base.foods_struct and base_kcal <= 0:
        raise NutritionCalculationException("Invalid meal composition")

    scale_factor_requested = target_kcal / base_kcal if base_kcal > 0 and target_kcal > 0 else 1.0
    scale_factor_applied = scale_factor_requested

    scaled = base.model_copy(deep=True)
    if scaled.foods_struct:
        for food in scaled.foods_struct:
            req = food.quantity * scale_factor_applied
            low = food.min_quantity
            high = food.max_quantity
            if low > 0 or high > 0:
                low = low if low > 0 else req
                high = high if high > 0 else req
                next_qty = clamp(req, low, high)
            else:
                next_qty = req
            
            qty_factor = next_qty / food.quantity if food.quantity > 0 else scale_factor_applied
            food.quantity = next_qty
            
            for ing in food.ingredients_struct:
                next_ing_qty = ing.quantity * qty_factor
                ing.quantity = next_ing_qty
                ing.macros = ing.macros.scale(qty_factor)
            
            food.recalculate_macros()
                
        scaled.recalculate_macros()
        if scaled.macros.caloriesKcal <= 0 and base.macros.caloriesKcal > 0:
            scaled.macros = base.macros.scale(scale_factor_applied)
    else:
        scaled.macros = scaled.macros.scale(scale_factor_applied)

    return scale_factor_requested, scale_factor_applied, scaled

def scale_meal_to_targets(
    meal: Dict[str, Any],
    target_macros: Dict[str, Any],
) -> Dict[str, Any]:
    from domain.payload_models import MealPayload, MacroStruct
    
    try:
        m = MealPayload(**meal)
        t = MacroStruct(**target_macros)
        
        req, app, scaled = scale_meal_payload_to_targets(m, t)
        
        out = scaled.model_dump(by_alias=True, exclude_unset=True)
        out["macros"] = out.get("_macros")
        # recompute ingredients struct list just in case
        flat_ingredients = []
        for food in out.get("foods_struct") or []:
            for ing in food.get("ingredients_struct") or []:
                flat_ing = fast_clone_ingredient(ing)
                flat_ing["food_id"] = food.get("id")
                flat_ing["food_name"] = food.get("name")
                flat_ingredients.append(flat_ing)
        out["ingredients_struct"] = flat_ingredients
        out["ingredients"] = ingredients_to_text(flat_ingredients)
        out["nutritive_values"] = format_nutritive_values(out.get("_macros") or out.get("macros") or {})
        
        return {
            "scaleFactorRequested": req,
            "scaleFactorApplied": app,
            "scaledMeal": out,
        }
    except Exception:
        # fallback to legacy dict loop if parsing fails
        base = fast_clone_meal(meal)
        base_macros = ensure_macros(base.get("_macros") or base.get("macros") or {})
        if base_macros["caloriesKcal"] <= 0 and base.get("foods_struct"):
            base = recompute_meal_from_foods(base)
            base_macros = ensure_macros(base.get("_macros") or {})

        target = ensure_macros(target_macros)
        if target.get("caloriesKcal", 0.0) < 0:
            raise NutritionCalculationException("Target calories cannot be negative")

        base_kcal = base_macros["caloriesKcal"]
        target_kcal = target["caloriesKcal"]

        scale_factor_requested = target_kcal / base_kcal if base_kcal > 0 and target_kcal > 0 else 1.0
        min_scale = 0.6
        max_scale = 2.5
        scale_factor_applied = clamp(scale_factor_requested, min_scale, max_scale)

        scaled = fast_clone_meal(base)
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
                next_food = fast_clone_food(food)
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

        return {
            "scaleFactorRequested": scale_factor_requested,
            "scaleFactorApplied": scale_factor_applied,
            "scaledMeal": scaled,
        }
