import sys
import os
import json
from pathlib import Path

# Setup pathing
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from backend.studio.substitutes import suggest_for_ingredients_text
from execution.process_substitution import process_substitution

def test_engine():
    print("--- Testing Suggestion Logic ---")
    ingredients = "Whole wheat bread 40 g, whole eggs 2 (100 g)"
    suggestions = suggest_for_ingredients_text(ingredients)
    
    # Check if first result has nested macros
    if suggestions['choices']:
        first_key = suggestions['choices'][0]['key']
        first_sub = suggestions['substitutesByKey'][first_key][0]
        if 'macros' in first_sub:
            print(f"SUCCESS: Nested macros found in {first_sub['name']}")
        else:
            print(f"FAILURE: Flat macros found in {first_sub['name']}")
            print(json.dumps(first_sub, indent=2))
    
    print("\n--- Testing Substitution Applied ---")
    original_meal = {
        "Meal_ID": "TEST_01",
        "meal_name": "Bread and Eggs",
        "ingredients": ingredients,
        "_macros": {"caloriesKcal": 300, "proteinG": 20, "carbsG": 30, "fatG": 10}
    }
    
    res = process_substitution(
        original_meal=original_meal,
        new_ingredients_text="Dosa 100 g, whole eggs 2 (100 g)",
        subst_name="Dosa",
        from_ingredient="Whole wheat bread 40 g"
    )
    print(f"New Meal Name: {res['meal']['meal_name']}")
    print(f"New Macros: {res['meal']['_macros']}")

if __name__ == "__main__":
    test_engine()
