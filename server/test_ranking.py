import asyncio
from services.ranking_service import rank_meals_for_meal_time
from services.nutrition_service import calculate_daily_targets

profile = {
    "age": "30",
    "gender": "male",
    "weightKg": "70",
    "heightCm": "175",
    "activityLevel": "moderate",
    "goal": "weight_loss",
    "dietType": "non_veg",
    "cuisineType": "southeast_asian",
    "allergies": ""
}

targets = calculate_daily_targets(profile)

res = rank_meals_for_meal_time(
    profile=profile,
    meal_time="bedtime",
    targets=targets,
    limit=5
)
print("Ranked meals:", [r["meal_name"] for r in res["ranked"]])
