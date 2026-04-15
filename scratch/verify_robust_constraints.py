import sys
import unittest
from pathlib import Path

# Add root to path
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from backend.studio.constraints import filter_meals, expand_avoid_list

class TestRobustConstraints(unittest.TestCase):
    def setUp(self):
        self.meals = [
            {"Meal_ID": "1", "meal_name": "Egg Salad", "ingredients": "boiled egg, mayo", "caution": "Contains eggs"},
            {"Meal_ID": "2", "meal_name": "Veggie Stir Fry", "ingredients": "broccoli, carrots, soy sauce", "caution": ""},
            {"Meal_ID": "3", "meal_name": "Paneer Tikka", "ingredients": "paneer, spices, yogurt", "caution": "Dairy product"},
            {"Meal_ID": "4", "meal_name": "Chicken Curry", "ingredients": "chicken, onion, tomato", "caution": ""},
            {"Meal_ID": "5", "meal_name": "Fruit Bowl", "ingredients": "apple, banana, grapes", "caution": ""}
        ]

    def test_plural_matching(self):
        print("Running: Plural Matching Test ('egg' should catch 'eggs')")
        # 'egg' should catch 'boiled egg' and 'Contains eggs'
        allowed, meta = filter_meals(self.meals, ["egg"])
        ids = [m["Meal_ID"] for m in allowed]
        self.assertNotIn("1", ids)
        self.assertIn("2", ids)
        print(f"  Success: Filtered count {meta['filtered_count']}")

    def test_synonym_expansion(self):
        print("\nRunning: Synonym Expansion Test ('milk' should catch 'paneer' and 'yogurt')")
        # 'milk' is part of 'dairy' group which includes 'paneer' and 'yogurt'
        allowed, meta = filter_meals(self.meals, ["milk"])
        ids = [m["Meal_ID"] for m in allowed]
        self.assertNotIn("3", ids) # Paneer Tikka contains paneer and yogurt
        print(f"  Success: Filtered count {meta['filtered_count']}")
        print(f"  Ingredients avoid list expanded to: {meta['avoided_ingredients_used']}")

    def test_caution_field(self):
        print("\nRunning: Caution Field Test")
        # 'dairy' should be caught via caution 'Dairy product' in Paneer Tikka
        allowed, meta = filter_meals(self.meals, ["dairy"])
        ids = [m["Meal_ID"] for m in allowed]
        self.assertNotIn("3", ids)
        print("  Success: Caution field correctly scanned.")

    def test_no_false_positives(self):
        print("\nRunning: False Positive Test ('egg' should NOT catch 'veggie')")
        # Simple string 'egg' in 'veggie' should NOT match due to \b boundary
        allowed, _ = filter_meals(self.meals, ["egg"])
        ids = [m["Meal_ID"] for m in allowed]
        self.assertIn("2", ids) # 'Veggie Stir Fry' should be ALLOWED
        print("  Success: No false positive for 'egg' in 'veggie'.")

if __name__ == "__main__":
    unittest.main()
