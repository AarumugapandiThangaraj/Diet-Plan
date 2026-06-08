"""Quick smoke test: load meals for each new cuisine."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from backend.studio.meals import set_cuisine, load_master_meals

cuisines = [
    "african", "americas", "east_asian", "southeast_asian", "south_asian",
    "middle_eastern", "nordic", "oceania", "central", "russian", "fusion"
]

print("Cuisine Smoke Test")
print("=" * 50)
total = 0
for c in cuisines:
    try:
        set_cuisine(c)
        meals = load_master_meals()
        count = len(meals)
        total += count
        sample = meals[0]["meal_name"] if meals else "N/A"
        print(f"  {c:20s}  {count:>4d} meals  OK  (e.g. {sample[:40]})")
    except Exception as e:
        print(f"  {c:20s}  FAIL: {e}")

print("=" * 50)
print(f"  Total new meals loaded: {total}")
