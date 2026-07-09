import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from domain.payload_models import MealPayload

# Simulate what router does
raw_meal = {
    "id": "6a5afc9c-ef13-4eb2-8b5c-1bba3c03931f",
    "meal_name": "Idli with Sambar, Drumstick Leaf Powder Green Shot and Slivered Almonds",
    "foods_struct": [
        {"name": "Idli", "food_id": "36", "quantity": 3},
        {"name": "Sambar", "food_id": "37", "quantity": 160},
        {"name": "Drumstick Leaf Green Shot", "food_id": "38", "quantity": 90},
        {"name": "Slivered Almonds", "food_id": "39", "quantity": 1},
    ]
}

parsed = MealPayload.model_validate(raw_meal)
meal_dict = parsed.model_dump(by_alias=True)

print("=== meal_dict keys ===")
for k, v in meal_dict.items():
    if k != "foods_struct":
        print(f"  {k!r}: {v!r}")

print(f"\n  foods_struct[0]: {meal_dict.get('foods_struct', [{}])[0]}")

print(f"\n=== ID resolution ===")
meal_instance_id = (
    meal_dict.get("Meal_ID") or
    meal_dict.get("id") or
    meal_dict.get("meal_id") or
    ""
)
print(f"  meal_instance_id: {meal_instance_id!r}")
print(f"  cuisine: {meal_dict.get('cuisine_type')!r}  ← THIS IS THE PROBLEM IF None")

# Now simulate apply_food_swap_option cuisine lookup
option = {"replacementMealId": "247"}
cuisine = meal_dict.get("cuisine_type") or "north_indian"
print(f"  cuisine used for lookup: {cuisine!r}")

async def main():
    from repositories.meal_repository import get_meal_index_by_id_async

    idx_north = await get_meal_index_by_id_async("north_indian")
    print(f"\n  Meal 247 in north_indian index: {idx_north.get('247')}")

    idx_south = await get_meal_index_by_id_async("south_indian")
    m = idx_south.get("247")
    print(f"  Meal 247 in south_indian index: {m.get('meal_name') if m else None}")

    idx_all = await get_meal_index_by_id_async(None)
    m2 = idx_all.get("247")
    print(f"  Meal 247 in global index (None): {m2.get('meal_name') if m2 else None}")

asyncio.run(main())
