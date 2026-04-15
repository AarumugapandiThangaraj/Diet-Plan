from typing import List, Dict, Any, Tuple
import re

def score_meal_by_preference(meal: Dict[str, Any], structured_pref: Dict[str, Any]) -> float:
    """
    Calculates a preference score (soft constraints) for a single meal.
    Assumes hard constraints (filtering) have already been applied.
    """
    score = 0.0
    
    ingredients_text = (meal.get("ingredients", "") or "").lower()
    meal_name = (meal.get("meal_name", "") or "").lower()
    combined_text = f"{meal_name} {ingredients_text}"
    
    # 1. Preferred Ingredients (+50 per match)
    preferred = structured_pref.get("preferred_ingredients", [])
    for ing in preferred:
        if not ing: continue
        pattern = re.compile(rf"\b{re.escape(ing.lower())}\b", re.I)
        if pattern.search(combined_text):
            score += 50.0
            
    # 2. Macro Focus (+30 if alignment found)
    macro_focus = structured_pref.get("macro_focus")
    macros = meal.get("_macros", {})
    if macro_focus == "high_protein":
        protein = float(macros.get("proteinG", 0) or 0)
        if protein > 25: score += 30.0
    elif macro_focus == "low_carb":
        carbs = float(macros.get("carbsG", 0) or 0)
        if carbs < 20: score += 30.0
    elif macro_focus == "low_fat":
        fat = float(macros.get("fatG", 0) or 0)
        if fat < 10: score += 30.0

    # 3. Taste Keywords (+10 per match)
    taste = structured_pref.get("taste_keywords", [])
    for t in taste:
        if not t: continue
        if t.lower() in combined_text:
            score += 10.0

    return score

def rank_meals_with_preference(meals: List[Dict[str, Any]], structured_pref: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Ranks a list of meals by combining their base score with the preference score.
    Logic assumes specific filtering has already occurred.
    """
    ranked = []
    for m in meals:
        pref_score = score_meal_by_preference(m, structured_pref)
        
        # Use existing _score if present (lower is better for base macro match)
        # We convert it to a positive 'points' system where higher is better
        base_score = 100 - m.get("_score", 50) 
        
        final_score = base_score + pref_score
        ranked.append({**m, "_final_score": final_score})
        
    # Sort descending
    ranked.sort(key=lambda x: x["_final_score"], reverse=True)
    return ranked
