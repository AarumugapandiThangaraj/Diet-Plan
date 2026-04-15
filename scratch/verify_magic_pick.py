import sys
from pathlib import Path

# Add root to path
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from execution.preference_ranking import rank_meals_with_preference

# Mock meals
meals = [
    {"Meal_ID": "1", "meal_name": "Chicken Curry", "ingredients": "chicken, onion, spices", "_score": 10, "_macros": {"proteinG": 30}},
    {"Meal_ID": "2", "meal_name": "Paneer Tikka", "ingredients": "paneer, yogurt", "_score": 5, "_macros": {"proteinG": 15}},
    {"Meal_ID": "3", "meal_name": "Veg Salad", "ingredients": "cucumber, tomato", "_score": 2, "_macros": {"proteinG": 2}}
]

# Mock structured preference
pref = {
    "preferred_ingredients": ["chicken"],
    "avoid_ingredients": ["paneer"],
    "macro_focus": "high_protein",
    "taste_keywords": ["spicy"]
}

print("Ranking with preference: Chicken, no Paneer, High Protein")
ranked = rank_meals_with_preference(meals, pref)

for m in ranked:
    print(f"ID: {m['Meal_ID']} Name: {m['meal_name']} Score: {m['_final_score']}")

# Verification
assert ranked[0]["Meal_ID"] == "1", "Chicken Curry should be first"
assert ranked[-1]["Meal_ID"] == "2", "Paneer Tikka should be last due to avoid list"
print("\nVerification Successful!")
