from typing import Any, Dict, List

VALID_CUISINES: Dict[str, str] = {
    "north_indian": "North Indian",
    "south_indian": "South Indian",
    "uae": "UAE",
    "continental": "Continental",
    "mediterranean": "Mediterranean",
    "african": "African",
    "americas": "Americas",
    "east_asian": "East Asian",
    "southeast_asian": "Southeast Asian",
    "south_asian": "South Asian",
    "middle_eastern": "Middle Eastern",
    "nordic": "Nordic",
    "oceania": "Oceania",
    "central": "Central",
    "russian": "Russian",
    "fusion": "Fusion",
}

ACTIVITY_MULTIPLIERS: Dict[str, float] = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "heavy": 1.725,
}

MEAL_DISTRIBUTION: Dict[str, float] = {
    "early_morning": 0.05,
    "breakfast": 0.20,
    "mid_morning": 0.10,
    "lunch": 0.25,
    "evening": 0.10,
    "dinner": 0.25,
    "bedtime": 0.05,
}

MEAL_TIME_ORDER: List[str] = list(MEAL_DISTRIBUTION.keys())

GRAM_UNITS = {"g", "gram", "grams", "ml", "milliliter", "milliliters"}

VALID_GOALS = {"skin_repair": "Skin Repair", "hair_repair": "Hair Repair"}
VALID_ACTIVITY = {"sedentary": "Sedentary", "light": "Light", "moderate": "Moderate", "heavy": "Heavy"}
VALID_DIET = {"veg": "Veg", "non_veg": "Non-Veg"}
VALID_GENDER = {"male": "Male", "female": "Female"}

FIELD_ALIASES = {
    "weight": "weightKg", "wt": "weightKg", "mass": "weightKg",
    "height": "heightCm", "ht": "heightCm",
    "age": "age",
    "goal": "goal", "primary goal": "goal", "target": "goal",
    "diet": "dietType", "diet type": "dietType", "food type": "dietType", "diet preference": "dietType",
    "activity": "activityLevel", "activity level": "activityLevel",
    "cuisine": "cuisineType", "cuisine type": "cuisineType",
    "gender": "gender", "sex": "gender",
    "allergies": "allergies", "allergy": "allergies",
}

FIELD_VALIDATORS = {
    "goal": VALID_GOALS,
    "dietType": VALID_DIET,
    "activityLevel": VALID_ACTIVITY,
    "cuisineType": VALID_CUISINES,
    "gender": VALID_GENDER,
}

BMI_GOAL = 22
FAT_PERCENT_RANGE = {"min": 0.2, "max": 0.35}
FIBER_G_PER_1000_KCAL = 14
FIBER_MIN_G_PER_DAY = 25
WATER_ML_PER_KG_RANGE = {"min": 30, "max": 35}

MACRO_ERROR_WEIGHTS: Dict[str, float] = {
    "caloriesKcal": 1.8,
    "proteinG": 1.2,
    "carbsG": 0.7,
    "fatG": 0.8,
    "fiberG": 0.4,
}
