import json
import re
import os
import hashlib
from typing import List, Dict, Any, Optional, Set
from backend.studio.food_engine import get_engine, ErrorResponse

def normalize_ingredient_token(token: str) -> str:
    """Standardize a single ingredient token."""
    s = token.lower().strip()
    s = re.sub(r'\(.*?\)', '', s)
    units = r'(?:ml|g|kg|tsp|tbsp|cup|glasses|katori|medium|small|big|large|pieces|whole|raw|cooked|baked|boiled|juice|powder|decoction)'
    s = re.sub(rf'\b\d+(?:\.\d+)?\s*{units}?\b', '', s, flags=re.I)
    s = re.sub(rf'\b{units}\b', '', s, flags=re.I)
    s = re.sub(r'[^a-z0-9 ]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def generate_ingredient_signature(ingredients_text: str) -> str:
    if not ingredients_text: return ""
    tokens = re.split(r'[,\n;]', ingredients_text)
    normalized = set()
    for t in tokens:
        n = normalize_ingredient_token(t)
        if n: normalized.add(n)
    return "|".join(sorted(list(normalized)))

def get_next_meal_id(master_data: List[Dict[str, Any]]) -> str:
    max_num = 0
    for m in master_data:
        mid = m.get('Meal_ID')
        if mid and mid.startswith('MEAL_'):
            try:
                num = int(mid.split('_')[1])
                if num > max_num: max_num = num
            except: continue
    return f"MEAL_{str(max_num + 1).zfill(6)}"

def calculate_macro_delta(old_item_text: str, new_item_name: str, new_qty: float) -> Dict[str, float]:
    engine = get_engine()
    
    # Match old
    old_clean = normalize_ingredient_token(old_item_text)
    old_idx = engine.matcher.find(old_clean)
    
    # Extract old qty
    qty_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:g|ml)', old_item_text, re.I)
    old_qty = float(qty_match.group(1)) if qty_match else 100.0
    
    # Match new
    new_idx = engine.matcher.find(new_item_name)
    
    delta = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0, "fiber": 0.0}
    
    if old_idx is not None and not isinstance(old_idx, dict) and new_idx is not None and not isinstance(new_idx, dict):
        old_row = engine.df.iloc[old_idx]
        new_row = engine.df.iloc[new_idx]
        
        f_old = old_qty / 100.0
        f_new = new_qty / 100.0
        
        cols = {"calories": "energy (kcal)", "protein": "protein (g)", "carbs": "carbohydrates (g)", "fat": "fat (g)", "fiber": "dietary fiber (g)"}
        for key, col in cols.items():
            old_val = float(old_row.get(col, 0) or 0) * f_old
            new_val = float(new_row.get(col, 0) or 0) * f_new
            delta[key] = new_val - old_val
            
    return delta

def process_substitution(
    original_meal: Dict[str, Any],
    new_ingredients_text: str,
    subst_name: str = "",
    from_ingredient: str = "",
    suggested_id: str = ""
) -> Dict[str, Any]:
    new_sig = generate_ingredient_signature(new_ingredients_text)
    
    delta = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0, "fiber": 0.0}
    if from_ingredient and subst_name:
        qty_match = re.search(rf'{re.escape(subst_name)}.*?(\d+(?:\.\d+)?)\s*(?:g|ml)', new_ingredients_text, re.I)
        new_qty = float(qty_match.group(1)) if qty_match else 100.0
        delta = calculate_macro_delta(from_ingredient, subst_name, new_qty)

    curr_macros = original_meal.get('_macros', {})
    new_macros = {
        "caloriesKcal": round(float(curr_macros.get("caloriesKcal", 0) or 0) + delta["calories"], 1),
        "proteinG": round(float(curr_macros.get("proteinG", 0) or 0) + delta["protein"], 1),
        "carbsG": round(float(curr_macros.get("carbsG", 0) or 0) + delta["carbs"], 1),
        "fatG": round(float(curr_macros.get("fatG", 0) or 0) + delta["fat"], 1),
        "fiberG": round(float(curr_macros.get("fiberG", 0) or 0) + delta["fiber"], 1),
    }

    new_nutritive = f"{new_macros['caloriesKcal']} kcal | Protein {new_macros['proteinG']} g | Carbs {new_macros['carbsG']} g | Fat {new_macros['fatG']} g"

    orig_name = original_meal.get('meal_name', 'Untitled')
    new_name = orig_name
    if from_ingredient and subst_name:
        old_clean = normalize_ingredient_token(from_ingredient)
        if old_clean in orig_name.lower():
            pattern = re.compile(re.escape(old_clean), re.I)
            new_name = pattern.sub(subst_name.title(), orig_name)
    
    if new_name == orig_name:
        variant_label = subst_name.strip() if subst_name else "modified"
        new_name = f"{orig_name} ({variant_label} variant)"

    new_meal = original_meal.copy()
    new_meal.update({
        'Meal_ID': suggested_id or f"VAR_{hashlib.md5(new_sig.encode()).hexdigest()[:8].upper()}",
        'meal_name': new_name,
        'ingredients': new_ingredients_text,
        'nutritive_values': new_nutritive,
        '_macros': new_macros,
        'parent_meal_id': original_meal.get('Meal_ID'),
        'signature': new_sig,
        'tags': list(set(original_meal.get('tags', []) + ["generated", "substitution", "pending", (subst_name or "mod").lower()]))
    })
    
    return {'meal': new_meal}
