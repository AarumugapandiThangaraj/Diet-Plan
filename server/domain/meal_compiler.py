"""
Meal Nutrition Compiler

Responsible for aggregating and compiling scaled nutritional macros for meals composed
of multiple food portions. Used for caching and menu plan calculations.
"""

from typing import Any, Dict, List

def compile_meal_macros(scaled_foods: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Input: List of already scaled food structures, each containing a "macros" dictionary.
    Output: Summed dictionary of macros for the entire meal.
    """
    out = {"caloriesKcal": 0.0, "proteinG": 0.0, "carbsG": 0.0, "fatG": 0.0, "fiberG": 0.0}
    
    for f in scaled_foods:
        m = f.get("macros") or {}
        out["caloriesKcal"] += float(m.get("caloriesKcal") or m.get("calories", 0.0))
        out["proteinG"] += float(m.get("proteinG") or m.get("protein", 0.0))
        out["carbsG"] += float(m.get("carbsG") or m.get("carbs", 0.0))
        out["fatG"] += float(m.get("fatG") or m.get("fat", 0.0))
        out["fiberG"] += float(m.get("fiberG") or m.get("fiber", 0.0))
        
    return {k: round(v, 2) for k, v in out.items()}
