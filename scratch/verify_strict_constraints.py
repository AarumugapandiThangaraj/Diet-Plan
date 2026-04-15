import sys
from pathlib import Path

# Add root to path
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from execution.preference_ranking import rank_meals_with_preference

# Mock meals
meals = [
    {"Meal_ID": "1", "meal_name": "Wheat Pasta", "ingredients": "whole wheat semolina, water", "_score": 10},
    {"Meal_ID": "2", "meal_name": "Rice Bowl", "ingredients": "basmati rice, veggies", "_score": 10},
    {"Meal_ID": "3", "meal_name": "Egg Salad", "ingredients": "hard boiled egg, mayo", "_score": 10}
]

# Test 1: Allergic to wheat
print("Test 1: Preference 'I am allergic to wheat'")
pref1 = {"avoid_ingredients": ["wheat"]}
ranked1 = rank_meals_with_preference(meals, pref1)
ids1 = [m["Meal_ID"] for m in ranked1]
print(f"Result IDs: {ids1}")
assert "1" not in ids1, "Wheat Pasta should be EXCLUDED"
assert "2" in ids1, "Rice Bowl should be ALLOWED"

# Test 2: Allergic to egg (verify word boundary)
print("\nTest 2: Preference 'no egg'")
pref2 = {"avoid_ingredients": ["egg"]}
ranked2 = rank_meals_with_preference(meals, pref2)
ids2 = [m["Meal_ID"] for m in ranked2]
print(f"Result IDs: {ids2}")
assert "3" not in ids2, "Egg Salad should be EXCLUDED"
assert "2" in ids2, "Rice Bowl (with veggies) should be ALLOWED (verifying 'egg' didn't match 'veggie')"

print("\nSTRICT CONSTRAINT VERIFICATION SUCCESSFUL!")
