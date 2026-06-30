from copy import deepcopy
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from domain.scaling_formulas import (
    ensure_macros,
    format_nutritive_values,
    recompute_meal_from_foods,
    recompute_meal_from_ingredients,
)
from utils.normalizers import normalize_food_key, normalize_ingredient_key
from config.constants import MACRO_ERROR_WEIGHTS

def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, str(a or "").lower(), str(b or "").lower()).ratio()

def _clamp(x: float, low: float, high: float) -> float:
    return max(low, min(high, x))

def _macro_error(actual: Dict[str, Any], target: Dict[str, Any]) -> float:
    a = ensure_macros(actual)
    t = ensure_macros(target)
    weights = MACRO_ERROR_WEIGHTS

    def rel_err(av: float, tv: float) -> float:
        if tv <= 0:
            return 0.0 if av <= 0 else 1.0
        return abs(av - tv) / tv

    return sum(weights[k] * rel_err(a[k], t[k]) for k in weights)

def _meal_macros(meal: Dict[str, Any]) -> Dict[str, float]:
    return ensure_macros(meal.get("macros") or meal.get("_macros") or {})

def meal_for_plan_payload(meal: Dict[str, Any], *, scale_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    macros = _meal_macros(meal)
    cuisine = meal.get("cuisine_type")
    if isinstance(cuisine, list):
        cuisine = ", ".join(str(x).strip() for x in cuisine if str(x).strip())
    payload = {
        "Meal_ID": meal.get("Meal_ID"),
        "meal_name": meal.get("meal_name"),
        "meal_time": meal.get("meal_time"),
        "goal": meal.get("goal"),
        "cuisine_type": cuisine or "",
        "country": meal.get("country") or "",
        "image_ID": meal.get("image_ID") or "",
        "diet_type": meal.get("diet_type"),
        "time": meal.get("time") or "",
        "serving_size": meal.get("serving_size") or "",
        "ingredients": meal.get("ingredients") or "",
        "ingredients_struct": meal.get("ingredients_struct") or [],
        "foods_struct": meal.get("foods_struct") or [],
        "method": meal.get("method") or "",
        "caution": meal.get("caution") or "",
        "nutritive_values": meal.get("nutritive_values") or format_nutritive_values(macros),
        "macros": macros,
    }
    if scale_meta:
        payload["scale"] = {
            "requested": float(scale_meta.get("scaleFactorRequested", 1.0) or 1.0),
            "applied": float(scale_meta.get("scaleFactorApplied", 1.0) or 1.0),
        }
    return payload

def _meal_name_from_foods(foods: List[Dict[str, Any]]) -> str:
    names = [str((food or {}).get("name") or "").strip() for food in foods if str((food or {}).get("name") or "").strip()]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return f"{names[0]} with {' with '.join(names[1:])}"

def _flatten_meal_ingredients(meal: Dict[str, Any]) -> List[Dict[str, Any]]:
    foods = list((meal or {}).get("foods_struct") or [])
    entries: List[Dict[str, Any]] = []
    if foods:
        for food_index, food in enumerate(foods):
            for ingredient_index, ing in enumerate(food.get("ingredients_struct") or []):
                entries.append(
                    {
                        "food_index": food_index,
                        "ingredient_index": ingredient_index,
                        "ingredient": ing,
                        "food": food,
                    }
                )
    else:
        for ingredient_index, ing in enumerate((meal or {}).get("ingredients_struct") or []):
            entries.append(
                {
                    "food_index": -1,
                    "ingredient_index": ingredient_index,
                    "ingredient": ing,
                    "food": None,
                }
            )
    return entries

def _resolve_source_ingredient(meal: Dict[str, Any], query: str) -> Tuple[Dict[str, Any], float]:
    entries = _flatten_meal_ingredients(meal)
    if not entries:
        raise ValueError("This meal has no structured ingredient list available.")

    q = normalize_ingredient_key(query)
    if not q:
        raise ValueError("Ingredient name is required.")

    best_entry: Optional[Dict[str, Any]] = None
    best_score = -1.0
    for entry in entries:
        ing = entry.get("ingredient") or {}
        name = normalize_ingredient_key(ing.get("name"))
        if not name:
            continue
        score = 1.0 if name == q else _ratio(name, q)
        if q in name or name in q:
            score = max(score, 0.92)
        if score > best_score:
            best_entry = entry
            best_score = score

    if not best_entry or best_score < 0.35:
        raise ValueError(f"Could not find ingredient '{query}' in this meal.")

    return best_entry, best_score

def _resolve_source_food(meal: Dict[str, Any], query: str) -> Tuple[int, Dict[str, Any], float]:
    foods = list((meal or {}).get("foods_struct") or [])
    if not foods:
        raise ValueError("This meal has no structured food list available.")

    q = normalize_food_key(query)
    if not q:
        raise ValueError("Food name is required.")

    best_idx = -1
    best_score = -1.0
    for i, food in enumerate(foods):
        name = normalize_food_key(food.get("name"))
        if not name:
            continue
        score = 1.0 if name == q else _ratio(name, q)
        if q in name or name in q:
            score = max(score, 0.92)
        if score > best_score:
            best_idx = i
            best_score = score

    if best_idx < 0 or best_score < 0.35:
        raise ValueError(f"Could not find food '{query}' in this meal.")

    return best_idx, foods[best_idx], best_score

def _replacement_from_catalog(
    entry: Dict[str, Any],
    source_ingredient: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    source_macros = ensure_macros((source_ingredient or {}).get("macros") or {})
    source_qty = float((source_ingredient or {}).get("quantity") or 0.0)
    source_unit = str((source_ingredient or {}).get("unit") or "").strip() or "g"

    per100 = ensure_macros(entry.get("per100g") or {})
    per_unit = ensure_macros(entry.get("per_unit") or {})

    target_cal = source_macros["caloriesKcal"]

    if per100["caloriesKcal"] > 0:
        qty = source_qty if source_qty > 0 else 100.0
        if target_cal > 0:
            qty = (target_cal * 100.0) / per100["caloriesKcal"]
        low = source_qty * 0.5 if source_qty > 0 else 10.0
        high = source_qty * 2.5 if source_qty > 0 else 400.0
        qty = _clamp(qty, low, high)

        macros = {
            "caloriesKcal": per100["caloriesKcal"] * qty / 100.0,
            "proteinG": per100["proteinG"] * qty / 100.0,
            "carbsG": per100["carbsG"] * qty / 100.0,
            "fatG": per100["fatG"] * qty / 100.0,
            "fiberG": per100["fiberG"] * qty / 100.0,
        }
        unit = "g"
    elif per_unit["caloriesKcal"] > 0:
        qty = source_qty if source_qty > 0 else 1.0
        if target_cal > 0:
            qty = target_cal / per_unit["caloriesKcal"]
        low = source_qty * 0.5 if source_qty > 0 else 0.25
        high = source_qty * 2.5 if source_qty > 0 else 6.0
        qty = _clamp(qty, low, high)

        macros = {
            "caloriesKcal": per_unit["caloriesKcal"] * qty,
            "proteinG": per_unit["proteinG"] * qty,
            "carbsG": per_unit["carbsG"] * qty,
            "fatG": per_unit["fatG"] * qty,
            "fiberG": per_unit["fiberG"] * qty,
        }
        unit = source_unit or str(entry.get("unit_hint") or "unit")
    else:
        return None

    return {
        "name": str(entry.get("name") or "").strip() or "Replacement",
        "quantity": qty,
        "unit": unit,
        "macros": macros,
        "caution": str(entry.get("caution") or "").strip(),
        "notes": "",
    }

def _replacement_food_from_catalog(entry: Dict[str, Any], source_food: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    source_macros = ensure_macros((source_food or {}).get("macros") or {})
    source_qty = float((source_food or {}).get("quantity") or 0.0)
    source_unit = str((source_food or {}).get("unit") or "").strip() or "g"

    base_macros = ensure_macros(entry.get("macros") or {})
    entry_qty = float(entry.get("quantity") or 1.0)
    target_cal = source_macros["caloriesKcal"]

    min_qty = float(entry.get("min_quantity") or 0.0)
    max_qty = float(entry.get("max_quantity") or 0.0)

    if base_macros["caloriesKcal"] > 0:
        qty = source_qty if source_qty > 0 else entry_qty
        if target_cal > 0:
            qty = (target_cal * entry_qty) / base_macros["caloriesKcal"]
            
        low = min_qty if min_qty > 0 else (entry_qty * 0.5)
        high = max_qty if max_qty > 0 else (entry_qty * 2.5)
        qty = _clamp(qty, low, high)

        factor = qty / entry_qty if entry_qty > 0 else 1.0
        macros = {
            "caloriesKcal": base_macros["caloriesKcal"] * factor,
            "proteinG": base_macros["proteinG"] * factor,
            "carbsG": base_macros["carbsG"] * factor,
            "fatG": base_macros["fatG"] * factor,
            "fiberG": base_macros["fiberG"] * factor,
        }
        unit = str(entry.get("unit") or "g")
    else:
        return None

    return {
        "foodId": entry.get("id"),
        "name": str(entry.get("name") or "").strip() or "Replacement",
        "quantity": qty,
        "unit": unit,
        "macros": macros,
    }

def _candidate_keys_for_source(source_name: str, *, cap: int = 120, cuisine: str = "north_indian") -> List[str]:
    from domain.substitutes import build_substitute_index, normalize_key
    from repositories.meal_repository import ingredient_catalog_by_key

    catalog = ingredient_catalog_by_key(cuisine)
    if not catalog:
        return []

    source_key = normalize_ingredient_key(source_name)
    out: List[str] = []
    seen = set()

    sub_idx = build_substitute_index()
    sub_key = normalize_key(source_name)
    if sub_key in (sub_idx.get("neighbors_by_norm") or {}):
        for n in sorted(sub_idx["neighbors_by_norm"].get(sub_key) or []):
            cand = normalize_ingredient_key(n)
            if cand and cand in catalog and cand not in seen:
                seen.add(cand)
                out.append(cand)

    scored = []
    for k, entry in catalog.items():
        if k == source_key:
            continue
        name = entry.get("name") or k
        score = _ratio(source_name, name)
        if source_key and (source_key in k or k in source_key):
            score = max(score, 0.93)
        scored.append((score, k))
    scored.sort(reverse=True)

    for score, k in scored:
        if score < 0.25:
            continue
        if k in seen:
            continue
        seen.add(k)
        out.append(k)
        if len(out) >= cap:
            break

    return out

def _candidate_food_keys_for_source(source_name: str, *, cap: int = 120, cuisine: str = "north_indian") -> List[str]:
    from repositories.meal_repository import food_catalog_by_key
    catalog = food_catalog_by_key(cuisine)
    if not catalog:
        return []

    source_key = normalize_food_key(source_name)
    scored = []
    for k, entry in catalog.items():
        if k == source_key:
            continue
        name = entry.get("name") or k
        score = _ratio(source_name, name)
        if source_key and (source_key in k or k in source_key):
            score = max(score, 0.93)
        scored.append((score, k))
    scored.sort(reverse=True)

    out: List[str] = []
    for score, k in scored:
        if score < 0.25:
            continue
        out.append(k)
        if len(out) >= cap:
            break
    return out

def _apply_ingredient_replacement(meal: Dict[str, Any], option: Dict[str, Any], cuisine: str = "north_indian") -> Dict[str, Any]:
    meal_copy = deepcopy(meal)
    foods = list(meal_copy.get("foods_struct") or [])

    replacement = option.get("replacement") or {}
    repl_name = str(replacement.get("name") or "").strip()
    if not repl_name:
        raise ValueError("Replacement ingredient is missing a name.")

    from domain.scaling_formulas import sum_ingredient_macros
    if foods:
        food_index = int(option.get("sourceFoodIndex", -1))
        ing_index = int(option.get("sourceIngredientIndex", -1))
        if food_index < 0 or food_index >= len(foods):
            raise ValueError("Invalid source food index.")
        ingredients = list(foods[food_index].get("ingredients_struct") or [])
        if ing_index < 0 or ing_index >= len(ingredients):
            raise ValueError("Invalid source ingredient index.")

        ingredients[ing_index] = {
            "name": repl_name,
            "quantity": float(replacement.get("quantity", 0.0) or 0.0),
            "unit": str(replacement.get("unit") or "g"),
            "macros": ensure_macros(replacement.get("macros") or {}),
            "caution": str(replacement.get("caution") or "").strip(),
            "notes": str(replacement.get("notes") or "").strip(),
            "swapable": True,
        }

        foods[food_index]["ingredients_struct"] = ingredients
        foods[food_index]["macros"] = sum_ingredient_macros(ingredients)
        meal_copy["foods_struct"] = foods
        meal_copy = recompute_meal_from_foods(meal_copy)
        return meal_for_plan_payload(meal_copy)

    ingredients = list(meal_copy.get("ingredients_struct") or [])
    if not ingredients:
        raise ValueError("Cannot apply replacement because meal has no structured ingredients.")

    source_index = int(option.get("sourceIngredientIndex", option.get("sourceIndex", -1)))
    if source_index < 0 or source_index >= len(ingredients):
        raise ValueError("Invalid source ingredient index.")

    ingredients[source_index] = {
        "name": repl_name,
        "quantity": float(replacement.get("quantity", 0.0) or 0.0),
        "unit": str(replacement.get("unit") or "g"),
        "macros": ensure_macros(replacement.get("macros") or {}),
        "caution": str(replacement.get("caution") or "").strip(),
        "notes": str(replacement.get("notes") or "").strip(),
        "swapable": True,
    }

    meal_copy["ingredients_struct"] = ingredients
    meal_copy = recompute_meal_from_ingredients(meal_copy)
    return meal_for_plan_payload(meal_copy)

def _apply_food_replacement(meal: Dict[str, Any], option: Dict[str, Any], cuisine: str = "north_indian") -> Dict[str, Any]:
    from domain.payload_models import MealPayload, FoodPayload
    try:
        m = MealPayload(**meal)
        if not m.foods_struct:
            raise ValueError("Cannot apply replacement because meal has no structured foods.")

        food_index = int(option.get("sourceFoodIndex", -1))
        if food_index < 0 or food_index >= len(m.foods_struct):
            raise ValueError("Invalid source food index.")

        replacement = option.get("replacement") or {}
        food_id = str(replacement.get("foodId") or "").strip()
        if not food_id:
            raise ValueError("Replacement food is missing an id.")

        quantity = float(replacement.get("quantity", 0.0) or 0.0)
        unit = str(replacement.get("unit") or "g")
        replaceable = bool(meal.get("foods_struct", [])[food_index].get("replaceable", True))

        from repositories.meal_repository import build_food_instance
        next_food_dict = build_food_instance(cuisine, food_id, quantity=quantity, unit=unit, replaceable=replaceable)
        if not next_food_dict:
            raise ValueError("Could not build replacement food from catalog.")

        m.foods_struct[food_index] = FoodPayload(**next_food_dict)
        
        # Build meal name
        foods_dict_list = [f.model_dump() for f in m.foods_struct]
        m.meal_name = _meal_name_from_foods(foods_dict_list) or m.meal_name
        
        m.recalculate_macros()
        
        out = m.model_dump(by_alias=True, exclude_unset=True)
        flat_ingredients = []
        for food in out.get("foods_struct") or []:
            for ing in food.get("ingredients_struct") or []:
                flat_ing = deepcopy(ing)
                flat_ing["food_id"] = food.get("id")
                flat_ing["food_name"] = food.get("name")
                flat_ingredients.append(flat_ing)
        out["ingredients_struct"] = flat_ingredients
        
        from domain.scaling_formulas import ingredients_to_text, format_nutritive_values
        out["ingredients"] = ingredients_to_text(flat_ingredients)
        out["nutritive_values"] = format_nutritive_values(out.get("_macros") or {})
        
        return meal_for_plan_payload(out)
    except Exception:
        meal_copy = deepcopy(meal)
        foods = list(meal_copy.get("foods_struct") or [])
        if not foods:
            raise ValueError("Cannot apply replacement because meal has no structured foods.")

        food_index = int(option.get("sourceFoodIndex", -1))
        if food_index < 0 or food_index >= len(foods):
            raise ValueError("Invalid source food index.")

        replacement = option.get("replacement") or {}
        food_id = str(replacement.get("foodId") or "").strip()
        if not food_id:
            raise ValueError("Replacement food is missing an id.")

        quantity = float(replacement.get("quantity", 0.0) or 0.0)
        unit = str(replacement.get("unit") or "g")
        replaceable = bool(foods[food_index].get("replaceable", True))

        from repositories.meal_repository import build_food_instance
        next_food = build_food_instance(cuisine, food_id, quantity=quantity, unit=unit, replaceable=replaceable)
        if not next_food:
            raise ValueError("Could not build replacement food from catalog.")

        foods[food_index] = next_food
        meal_copy["foods_struct"] = foods
        meal_copy["meal_name"] = _meal_name_from_foods(foods) or meal_copy.get("meal_name")
        meal_copy = recompute_meal_from_foods(meal_copy)
        return meal_for_plan_payload(meal_copy)

