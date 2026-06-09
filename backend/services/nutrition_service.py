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
    _protein_g_per_kg_target,
    _fat_percent_preset,
    normalize_activity_level
)
from config.constants import (
    BMI_GOAL,
    FIBER_G_PER_1000_KCAL,
    FIBER_MIN_G_PER_DAY,
    WATER_ML_PER_KG_RANGE
)

def calculate_daily_targets(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes all target nutrition goals (calories, protein, carbs, fat, fiber, water)
    based on the user's age, gender, height, weight, activity level, and targets.
    """
    age = _clamp(_to_safe_number(profile.get("age"), 30), 1, 120)
    height_cm = _clamp(_to_safe_number(profile.get("heightCm"), 165), 100, 250)
    weight_kg = _clamp(_to_safe_number(profile.get("weightKg"), 60), 20, 300)
    gender = profile.get("gender")

    bmi = calculate_bmi(weight_kg, height_cm)
    bmi_category = get_bmi_category(bmi)
    bmr = calculate_bmr(weight_kg, height_cm, age, gender)
    tdee = calculate_tdee(bmr, profile.get("activityLevel"))

    target_weight_kg_raw = calculate_target_weight_kg(height_cm, BMI_GOAL)
    target_weight_kg = round(target_weight_kg_raw * 10) / 10
    weight_delta_kg = round((target_weight_kg - weight_kg) * 10) / 10

    maintenance_calories = int(round(tdee))
    daily_calories = int(round(max(1200, maintenance_calories)))

    protein_per_kg = _protein_g_per_kg_target(bmi_category)
    protein_g = int(round(target_weight_kg * protein_per_kg))

    fat_preset = _fat_percent_preset(bmi_category)
    fat_g = int(round((daily_calories * fat_preset["default"]) / 9))
    fat_g_min = int(round((daily_calories * fat_preset["min"]) / 9))
    fat_g_max = int(round((daily_calories * fat_preset["max"]) / 9))

    remaining_calories = max(0, daily_calories - protein_g * 4 - fat_g * 9)
    carbs_g = int(round(remaining_calories / 4))

    carbs_g_min = int(round(max(0, daily_calories - protein_g * 4 - fat_g_max * 9) / 4))
    carbs_g_max = int(round(max(0, daily_calories - protein_g * 4 - fat_g_min * 9) / 4))

    fiber_g_raw = int(round((daily_calories / 1000) * FIBER_G_PER_1000_KCAL))
    fiber_g = max(FIBER_MIN_G_PER_DAY, fiber_g_raw)

    water_l_min = round(target_weight_kg * (WATER_ML_PER_KG_RANGE["min"] / 1000) * 100) / 100
    water_l_max = round(target_weight_kg * (WATER_ML_PER_KG_RANGE["max"] / 1000) * 100) / 100
    water_l = round(target_weight_kg * 0.033 * 100) / 100

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
        "carbsG": carbs_g,
        "fatG": fat_g,
        "fatGMin": fat_g_min,
        "fatGMax": fat_g_max,
        "carbsGMin": carbs_g_min,
        "carbsGMax": carbs_g_max,
        "fiberG": fiber_g,
        "fiberGRaw": fiber_g_raw,
        "fiberGMinimum": FIBER_MIN_G_PER_DAY,
        "waterL": water_l,
        "waterLMin": water_l_min,
        "waterLMax": water_l_max,
        "activityLevelNormalized": normalize_activity_level(profile.get("activityLevel")),
    }
