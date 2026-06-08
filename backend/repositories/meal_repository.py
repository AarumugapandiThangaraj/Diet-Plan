"""
Meal Repository Layer

Defines the database querying, caching, and data access layers for ingredients, foods, 
and meals. Delegates portion scaling and dynamic macro compilation to domain-level compilers.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import math
import os
import re
from copy import deepcopy
from functools import lru_cache
import threading
from typing import Any, Dict, Iterable, List, Optional, Tuple

_db_lock = threading.Lock()
_ingredients_cache = {}
_foods_cache = {}
_meals_cache = {}

from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

from config.constants import VALID_CUISINES, GRAM_UNITS
from database.session import AsyncSessionLocal
from database.models.cuisine import Cuisine
from database.models.ingredient import Ingredient
from database.models.food import Food, FoodIngredient
from database.models.meal import Meal, MealFood
from domain.nutrition_compiler import calculate_ingredient_contribution
from domain.meal_compiler import compile_meal_macros
from database.models.meal import Meal, MealFood
from utils.parsers import _to_number, split_keywords, parse_nutritive_values
from utils.formatters import _fmt_num, format_nutritive_values
from utils.normalizers import (
    _normalize_cuisine,
    normalize_tag,
    normalize_goal,
    normalize_goal_list,
    _normalize_meal_time,
    _normalize_diet_type,
)

_main_loop = None

def set_main_loop(loop):
    global _main_loop
    _main_loop = loop

# Resilient async runner helper
def run_async(coro):
    global _main_loop
    if _main_loop and _main_loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, _main_loop)
        return future.result()

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    
    if loop.is_running():
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(lambda: asyncio.run(coro))
            return future.result()
    else:
        return loop.run_until_complete(coro)

def _sum_macros(items: Iterable[Dict[str, Any]]) -> Dict[str, float]:
    out = {"caloriesKcal": 0.0, "proteinG": 0.0, "carbsG": 0.0, "fatG": 0.0, "fiberG": 0.0}
    for it in items:
        m = it.get("macros") or {}
        out["caloriesKcal"] += _to_number(m.get("caloriesKcal"), 0.0)
        out["proteinG"] += _to_number(m.get("proteinG"), 0.0)
        out["carbsG"] += _to_number(m.get("carbsG"), 0.0)
        out["fatG"] += _to_number(m.get("fatG"), 0.0)
        out["fiberG"] += _to_number(m.get("fiberG"), 0.0)
    return out

def _ingredients_to_text(items: Iterable[Dict[str, Any]]) -> str:
    out = []
    for ing in items:
        name = str(ing.get("name") or "").strip()
        qty = _to_number(ing.get("quantity"), 0.0)
        unit = str(ing.get("unit") or "").strip()
        if not name:
            continue
        if qty > 0:
            out.append(f"{name} {_fmt_num(qty)} {unit}".strip())
        else:
            out.append(name)
    return ", ".join(out)

def _unit_is_gram(unit: Any) -> bool:
    return str(unit or "").strip().lower() in GRAM_UNITS

def _ingredient_macros_for_quantity(
    base_macros: Dict[str, float],
    qty: float,
    unit: str,
    default_unit: str,
    conversions: Optional[Dict[str, float]] = None
) -> Dict[str, float]:
    return calculate_ingredient_contribution(base_macros, qty, unit, default_unit, conversions)

def _build_ingredient_struct(
    base: Dict[str, Any],
    *,
    quantity: float,
    unit: str,
    swapable: Optional[bool] = None,
) -> Dict[str, Any]:
    default_unit = str(base.get("default_unit") or "g")
    conversions = base.get("conversions")
    macros = _ingredient_macros_for_quantity(base.get("base_macros") or {}, quantity, unit, default_unit, conversions)
    out = {
        "id": base.get("id"),
        "name": base.get("name"),
        "quantity": float(quantity or 0.0),
        "unit": unit or default_unit,
        "macros": macros,
        "caution": str(base.get("caution") or "").strip(),
        "notes": str(base.get("notes") or "").strip(),
        "swapable": True if swapable is None else bool(swapable),
    }
    if _unit_is_gram(default_unit):
        out["per100g"] = base.get("base_macros") or {}
    else:
        out["per_unit"] = base.get("base_macros") or {}
    return out

async def _load_ingredients_db() -> Dict[str, Dict[str, Any]]:
    async with AsyncSessionLocal() as session:
        stmt = select(Ingredient)
        res = await session.execute(stmt)
        ingredients = res.scalars().all()
        out = {}
        for ing in ingredients:
            out[ing.id] = {
                "id": ing.id,
                "name": ing.name,
                "default_unit": ing.default_unit,
                "base_macros": {
                    "caloriesKcal": ing.calories,
                    "proteinG": ing.protein,
                    "carbsG": ing.carbs,
                    "fatG": ing.fat,
                    "fiberG": ing.fiber
                },
                "conversions": ing.conversions,
                "caution": ing.caution,
                "notes": ing.notes
            }
        return out

def ingredient_index_by_id(cuisine: str) -> Dict[str, Dict[str, Any]]:
    # In DB, ingredients are unified globally
    key = "global"
    if key in _ingredients_cache:
        return _ingredients_cache[key]
    with _db_lock:
        if key in _ingredients_cache:
            return _ingredients_cache[key]
        data = run_async(_load_ingredients_db())
        _ingredients_cache[key] = data
        return data

async def _load_foods_db(cuisine_name: str) -> Dict[str, Dict[str, Any]]:
    norm_cuisine = _normalize_cuisine(cuisine_name)
    ingredients_by_id = await _load_ingredients_db()
    
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Food)
            .join(Food.cuisine)
            .filter(Cuisine.name == norm_cuisine)
            .options(selectinload(Food.ingredient_associations))
        )
        res = await session.execute(stmt)
        foods = res.scalars().all()
        
        out = {}
        for f in foods:
            ingredients_struct = []
            for ass in f.ingredient_associations:
                ing_base = ingredients_by_id.get(ass.ingredient_id)
                if ing_base:
                    ingredients_struct.append(
                        _build_ingredient_struct(
                            ing_base,
                            quantity=ass.quantity,
                            unit=ass.unit,
                            swapable=ass.swapable
                        )
                    )
            
            out[f.id] = {
                "id": f.id,
                "name": f.name,
                "quantity": f.quantity,
                "unit": f.unit,
                "min_quantity": f.min_quantity or 0.0,
                "max_quantity": f.max_quantity or 0.0,
                "ingredients_struct": ingredients_struct,
                "macros": {
                    "caloriesKcal": f.calories,
                    "proteinG": f.protein,
                    "carbsG": f.carbs,
                    "fatG": f.fat,
                    "fiberG": f.fiber
                },
                "supports": f.supports or [],
                "type": f.type or "",
                "preparation": f.preparation or "",
                "description": f.description or "",
                "image_url": f.image_url or ""
            }
        return out

def food_index_by_id(cuisine: str) -> Dict[str, Dict[str, Any]]:
    if cuisine in _foods_cache:
        return _foods_cache[cuisine]
    with _db_lock:
        if cuisine in _foods_cache:
            return _foods_cache[cuisine]
        data = run_async(_load_foods_db(cuisine))
        _foods_cache[cuisine] = data
        return data

def _scale_food_instance(food_base: Dict[str, Any], *, quantity: float, unit: str, replaceable: bool) -> Dict[str, Any]:
    base_qty = _to_number(food_base.get("quantity"), 0.0)
    scale = quantity / base_qty if base_qty > 0 else 1.0

    scaled_ingredients: List[Dict[str, Any]] = []
    for ing in food_base.get("ingredients_struct") or []:
        ing_base_qty = _to_number(ing.get("quantity"), 0.0)
        scaled_qty = ing_base_qty * scale
        macros = ing.get("macros") or {}
        scaled_macros = {k: _to_number(macros.get(k), 0.0) * scale for k in macros}
        out = deepcopy(ing)
        out["quantity"] = scaled_qty
        out["macros"] = scaled_macros
        scaled_ingredients.append(out)

    food_macros = _sum_macros(scaled_ingredients)

    min_qty = _to_number(food_base.get("min_quantity"), 0.0)
    max_qty = _to_number(food_base.get("max_quantity"), 0.0)
    if base_qty > 0:
        ratio = quantity / base_qty
        min_qty = min_qty * ratio if min_qty > 0 else 0.0
        max_qty = max_qty * ratio if max_qty > 0 else 0.0

    return {
        "id": food_base.get("id"),
        "name": food_base.get("name"),
        "quantity": float(quantity or 0.0),
        "unit": unit or str(food_base.get("unit") or "g"),
        "min_quantity": min_qty,
        "max_quantity": max_qty,
        "replaceable": bool(replaceable),
        "ingredients_struct": scaled_ingredients,
        "macros": food_macros,
        "supports": food_base.get("supports") or [],
        "type": food_base.get("type") or "",
        "preparation": food_base.get("preparation") or "",
        "description": food_base.get("description") or "",
        "image_url": food_base.get("image_url") or "",
    }

def build_food_instance(
    cuisine: str,
    food_id: str,
    *,
    quantity: float,
    unit: str,
    replaceable: bool = True,
) -> Optional[Dict[str, Any]]:
    base = food_index_by_id(cuisine).get(str(food_id))
    if not base:
        return None
    return _scale_food_instance(base, quantity=quantity, unit=unit, replaceable=replaceable)

async def _load_meals_db(cuisine_name: str) -> List[Dict[str, Any]]:
    norm_cuisine = _normalize_cuisine(cuisine_name)
    foods_by_id = await _load_foods_db(cuisine_name)

    async with AsyncSessionLocal() as session:
        stmt = (
            select(Meal)
            .join(Meal.cuisine)
            .filter(Cuisine.name == norm_cuisine)
            .options(selectinload(Meal.food_associations))
        )
        res = await session.execute(stmt)
        meals = res.scalars().all()

        out = []
        for m in meals:
            # Map Foods list
            foods_struct = []
            for ass in m.food_associations:
                f_base = foods_by_id.get(ass.food_id)
                if f_base:
                    foods_struct.append(
                        _scale_food_instance(
                            f_base,
                            quantity=ass.quantity,
                            unit=ass.unit,
                            replaceable=ass.replaceable
                        )
                    )
            
            if not foods_struct:
                continue

            ingredients_struct = []
            for food_index, food in enumerate(foods_struct):
                for ing_index, ing in enumerate(food.get("ingredients_struct") or []):
                    flat = deepcopy(ing)
                    flat["food_id"] = food.get("id")
                    flat["food_name"] = food.get("name")
                    flat["food_index"] = food_index
                    flat["ingredient_index"] = ing_index
                    ingredients_struct.append(flat)

            totals = compile_meal_macros(foods_struct)
            
            # Reconstruct list timings/sessions
            sessions_list = m.sessions if isinstance(m.sessions, list) else [m.sessions]
            meal_time = _normalize_meal_time(sessions_list)

            # Reconstruct diet type list or string
            diet_type = _normalize_diet_type(m.diet_types)

            out.append({
                "Meal_ID": m.id,
                "meal_name": m.name,
                "goal": normalize_goal_list(m.goal),
                "meal_time": meal_time,
                "time": m.scheduled_time or "",
                "ingredients": _ingredients_to_text(ingredients_struct),
                "ingredients_struct": ingredients_struct,
                "foods_struct": foods_struct,
                "method": m.description or "",
                "nutritive_values": format_nutritive_values(totals),
                "serving_size": "",
                "caution": f"Allergens: {m.allergens}" if m.allergens else "",
                "diet_type": diet_type,
                "cuisine_type": cuisine_name,
                "country": "India",
                "image_ID": m.image_url or "",
                "description": m.description or "",
                "_macros": totals
            })
        return out

def load_master_meals(cuisine: str) -> List[Dict[str, Any]]:
    if cuisine in _meals_cache:
        return _meals_cache[cuisine]
    with _db_lock:
        if cuisine in _meals_cache:
            return _meals_cache[cuisine]
        data = run_async(_load_meals_db(cuisine))
        _meals_cache[cuisine] = data
        return data

@lru_cache(maxsize=32)
def meal_index_by_id(cuisine: str) -> Dict[str, Dict[str, Any]]:
    return {str(m["Meal_ID"]): m for m in load_master_meals(cuisine) if m.get("Meal_ID")}

@lru_cache(maxsize=32)
def ingredient_catalog_by_key(cuisine: str) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    ingredients_by_id = ingredient_index_by_id(cuisine)
    for entry in ingredients_by_id.values():
        name = str(entry.get("name") or "").strip()
        if not name:
            continue
        key = normalize_tag(name)
        if not key:
            continue
        base_macros = entry.get("base_macros") or {}
        default_unit = str(entry.get("default_unit") or "g").strip() or "g"
        if _unit_is_gram(default_unit):
            per100g = base_macros
            per_unit = {k: _to_number(base_macros.get(k), 0.0) / 100.0 for k in base_macros}
        else:
            per100g = {"caloriesKcal": 0.0, "proteinG": 0.0, "carbsG": 0.0, "fatG": 0.0, "fiberG": 0.0}
            per_unit = base_macros
        out[key] = {
            "key": key,
            "name": name,
            "count": 1,
            "unit_hint": default_unit,
            "per100g": per100g,
            "per_unit": per_unit,
            "caution": str(entry.get("caution") or "").strip(),
        }
    return out

@lru_cache(maxsize=32)
def food_catalog_by_key(cuisine: str) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    foods_by_id = food_index_by_id(cuisine)
    for entry in foods_by_id.values():
        name = str(entry.get("name") or "").strip()
        if not name:
            continue
        key = normalize_tag(name)
        if not key:
            continue
        macros = entry.get("macros") or {}
        qty = _to_number(entry.get("quantity"), 0.0)
        unit = str(entry.get("unit") or "g").strip() or "g"
        if qty > 0 and _unit_is_gram(unit):
            per100g = {k: _to_number(macros.get(k), 0.0) * 100.0 / qty for k in macros}
            per_unit = {k: _to_number(macros.get(k), 0.0) / qty for k in macros}
        elif qty > 0:
            per100g = {"caloriesKcal": 0.0, "proteinG": 0.0, "carbsG": 0.0, "fatG": 0.0, "fiberG": 0.0}
            per_unit = {k: _to_number(macros.get(k), 0.0) / qty for k in macros}
        else:
            per100g = {"caloriesKcal": 0.0, "proteinG": 0.0, "carbsG": 0.0, "fatG": 0.0, "fiberG": 0.0}
            per_unit = {"caloriesKcal": 0.0, "proteinG": 0.0, "carbsG": 0.0, "fatG": 0.0, "fiberG": 0.0}
        out[key] = {
            "key": key,
            "id": entry.get("id"),
            "name": name,
            "count": 1,
            "unit_hint": unit,
            "per100g": per100g,
            "per_unit": per_unit,
            "min_quantity": entry.get("min_quantity"),
            "max_quantity": entry.get("max_quantity"),
        }
    return out
