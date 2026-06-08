"""
Food Nutrition Compiler

Compiles nutrition information for a food recipe from its constituent ingredients.
Resolves unit measurements and aggregates nutritional macros per serving size.
"""

from typing import Any, Dict, List, Optional
from domain.conversion_engine import convert_to_grams, _unit_is_gram

def calculate_ingredient_contribution(
    base_macros: Dict[str, float],
    qty: float,
    unit: str,
    default_unit: str = "g",
    conversions: Optional[Dict[str, float]] = None
) -> Dict[str, float]:
    """
    Computes macro contributions of an ingredient based on quantity, unit, default unit, and density.
    """
    if qty <= 0:
        return {k: 0.0 for k in base_macros}
        
    unit_lower = str(unit or "").strip().lower()
    default_unit_lower = str(default_unit or "g").strip().lower()
    
    # Check if default unit of ingredient is gram-based (basis: per 100g)
    if _unit_is_gram(default_unit_lower):
        grams = convert_to_grams(qty, unit_lower, default_unit_lower, conversions)
        factor = grams / 100.0
    else:
        # Default unit is unit-based (basis: per 1 unit, e.g. eggs)
        # If the recipe specifies grams, we scale down; otherwise we scale by count.
        if _unit_is_gram(unit_lower):
            # Recipe says 50g of Eggs, but base macros are per 1 Egg.
            # We assume a default unit is 1 piece = 100g if missing, or use conversion.
            default_weight = 100.0
            if conversions and default_unit_lower in conversions:
                default_weight = float(conversions[default_unit_lower])
            factor = qty / default_weight
        else:
            factor = qty
            
    return {k: base_macros.get(k, 0.0) * factor for k in base_macros}

def compile_food_macros(ingredients_list: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Input: List of ingredient dictionaries, each containing:
        - "base_macros" or "macros": dict
        - "quantity": float
        - "unit": str
        - "default_unit": str
        - "conversions": Optional[dict]
    
    Output: Summed dictionary of macros.
    """
    out = {"caloriesKcal": 0.0, "proteinG": 0.0, "carbsG": 0.0, "fatG": 0.0, "fiberG": 0.0}
    
    for ing in ingredients_list:
        macros = ing.get("base_macros") or ing.get("macros") or {}
        qty = float(ing.get("quantity") or 0.0)
        unit = str(ing.get("unit") or "g")
        default_unit = str(ing.get("default_unit") or "g")
        conversions = ing.get("conversions")
        
        contrib = calculate_ingredient_contribution(macros, qty, unit, default_unit, conversions)
        
        out["caloriesKcal"] += contrib.get("caloriesKcal", contrib.get("calories", 0.0))
        out["proteinG"] += contrib.get("proteinG", contrib.get("protein", 0.0))
        out["carbsG"] += contrib.get("carbsG", contrib.get("carbs", 0.0))
        out["fatG"] += contrib.get("fatG", contrib.get("fat", 0.0))
        out["fiberG"] += contrib.get("fiberG", contrib.get("fiber", 0.0))
        
    return {k: round(v, 2) for k, v in out.items()}
