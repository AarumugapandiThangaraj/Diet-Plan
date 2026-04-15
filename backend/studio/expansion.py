from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

def _diet_plan_root() -> Path:
    return Path(__file__).resolve().parents[2]

if str(_diet_plan_root()) not in sys.path:
    sys.path.append(str(_diet_plan_root()))

from .meals import load_master_meals
from execution.process_substitution import process_substitution, generate_ingredient_signature, get_next_meal_id

MASTER_PATH = _diet_plan_root() / "data" / "master_meals_updated.json"

def evaluate_and_stage_substitution(
    original_meal_id: str,
    new_ingredients: str,
    subst_name: str = "",
    from_ingredient: str = ""
) -> Dict[str, Any]:
    """
    Evaluates a user substitution and appends directly to the master file.
    - If duplicate exists -> Returns existing ID.
    - Otherwise -> Creates new variant with linear ID, saves to Master, returns ID.
    """
    # 1. Load Master Data (Single Source of Truth)
    with open(MASTER_PATH, "r", encoding="utf-8") as f:
        master_data = json.load(f)
    
    # 2. Find Parent (for context)
    parent_meal = next((m for m in master_data if m.get("Meal_ID") == original_meal_id), None)
    if not parent_meal:
        return {"error": "Original meal not found"}

    # 3. Check for duplicates (Signature Match)
    new_sig = generate_ingredient_signature(new_ingredients)
    existing_match = next((m for m in master_data if m.get("signature") == new_sig), None)
    if existing_match:
        return {
            "mealId": existing_match["Meal_ID"],
            "status": "reused",
            "source": "master",
            "meal": existing_match
        }

    # 4. Generate Linear ID
    next_id = get_next_meal_id(master_data)

    # 5. Process New Variant via Engine
    result = process_substitution(
        original_meal=parent_meal,
        new_ingredients_text=new_ingredients,
        subst_name=subst_name,
        from_ingredient=from_ingredient,
        suggested_id=next_id
    )
    
    new_meal = result.get("meal")
    if not new_meal:
        return {"error": "Failed to generate variant"}

    # 6. Append and Save directly to Master
    master_data.append(new_meal)
    with open(MASTER_PATH, "w", encoding="utf-8") as f:
        json.dump(master_data, f, indent=2, ensure_ascii=False)

    return {
        "mealId": new_meal["Meal_ID"],
        "status": "created",
        "source": "master",
        "meal": new_meal
    }
