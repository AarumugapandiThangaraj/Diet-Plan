"""
Nutrition Service

Calculates target macro-nutrients and micro-nutrients for a user profile based on physical metrics
(height, weight, age, activity level, gender) and medical/wellness goals.
"""

from typing import Any, Dict
from domain.nutrition_formulas import (
    _clamp,
    _to_safe_number,
    calculate_bmi,
    calculate_bmr,
    calculate_tdee,
    calculate_target_weight_kg,
    get_bmi_category,
    get_bmi_adjustment,
    get_age_midpoint,
    get_water_target,
    normalize_activity_level
)
from config.constants import (
    BMI_GOAL,
    FIBER_G_PER_1000_KCAL,
    FIBER_MIN_G_PER_DAY,
    WATER_ML_PER_KG_RANGE,
    ACTIVITY_MULTIPLIERS
)

def calculate_daily_targets(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes all target nutrition goals (calories, protein, carbs, fat, fiber, water)
    based on the user's age, gender, height, weight, activity level, and targets.
    """
    print("calc daily")
    age = _clamp(get_age_midpoint(profile.get("age_group") or profile.get("age")), 1, 120)
    height_cm = _clamp(_to_safe_number(profile.get("heightCm"), 165), 100, 250)
    weight_kg = _clamp(_to_safe_number(profile.get("weightKg"), 60), 20, 300)
    gender = profile.get("gender")

    bmi = calculate_bmi(weight_kg, height_cm)
    bmi_category = get_bmi_category(bmi)
    bmi_adjustment = get_bmi_adjustment(bmi)
    
    bmr = calculate_bmr(weight_kg, height_cm, age, gender)
    tdee = calculate_tdee(bmr, profile.get("activityLevel"), bmi_adjustment)

    target_weight_kg_raw = calculate_target_weight_kg(height_cm, BMI_GOAL)
    target_weight_kg = round(target_weight_kg_raw * 10) / 10
    weight_delta_kg = round((target_weight_kg - weight_kg) * 10) / 10

    maintenance_calories = int(round(bmr * ACTIVITY_MULTIPLIERS.get(normalize_activity_level(profile.get("activityLevel")), 1.4))) if "ACTIVITY_MULTIPLIERS" in globals() else int(round(tdee - bmi_adjustment))
    
    # Calorie Range: (TDEE * 0.95) to (TDEE * 1.05)
    daily_calories = int(round(max(1200, tdee)))
    
    # Protein: 10% to 15% of TDEE / 4
    protein_g_min = int(round((daily_calories * 0.10) / 4))
    protein_g_max = int(round((daily_calories * 0.15) / 4))
    protein_g = protein_g_max # Default to max for target, or avg
    
    # Carbs: 50% to 60% of TDEE / 4
    carbs_g_min = int(round((daily_calories * 0.50) / 4))
    carbs_g_max = int(round((daily_calories * 0.60) / 4))
    carbs_g = int(round((daily_calories * 0.55) / 4))

    # Fat: 20% to 30% of TDEE / 9
    fat_g_min = int(round((daily_calories * 0.20) / 9))
    fat_g_max = int(round((daily_calories * 0.30) / 9))
    fat_g = int(round((daily_calories * 0.25) / 9))

    # Fiber Standard: 25 - 35 grams
    fiber_g_raw = int(round((daily_calories / 1000) * FIBER_G_PER_1000_KCAL))
    fiber_g = max(25, min(35, fiber_g_raw)) # Clamp between 25 and 35

    water_target = get_water_target(profile.get("activityLevel"), weight_kg)
    water_l_min = water_target["min"]
    water_l_max = water_target["max"]
    water_l = water_target["default"]
    print("Calc end")
    return {
        "age": int(round(age)),
        "heightCm": float(round(height_cm, 1)),
        "weightKg": float(round(weight_kg, 1)),
        "targetBmi": BMI_GOAL,
        "targetWeightKg": target_weight_kg,
        "weightDeltaKg": weight_delta_kg,
        "bmi": round(bmi, 1),
        "bmiCategory": bmi_category,
        "bmr": int(round(bmr)),
        "tdee": int(round(tdee)),
        "maintenanceCalories": maintenance_calories,
        "dailyCalories": daily_calories,
        "proteinG": protein_g,
        "proteinGMin": protein_g_min,
        "proteinGMax": protein_g_max,
        "carbsG": carbs_g,
        "fatG": fat_g,
        "fatGMin": fat_g_min,
        "fatGMax": fat_g_max,
        "carbsGMin": carbs_g_min,
        "carbsGMax": carbs_g_max,
        "fiberG": fiber_g,
        "fiberGMin": 25,
        "fiberGMax": 35,
        "waterL": water_l,
        "waterLMin": water_l_min,
        "waterLMax": water_l_max,
        "activityLevelNormalized": normalize_activity_level(profile.get("activityLevel")),
    }
