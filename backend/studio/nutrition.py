from __future__ import annotations

import math
import re
from typing import Any, Dict


ACTIVITY_MULTIPLIERS: Dict[str, float] = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "heavy": 1.725,
}

BMI_GOAL = 22

FAT_PERCENT_RANGE = {"min": 0.2, "max": 0.35}
FIBER_G_PER_1000_KCAL = 14
FIBER_MIN_G_PER_DAY = 25
WATER_ML_PER_KG_RANGE = {"min": 30, "max": 35}


def _to_safe_number(value: Any, fallback: float) -> float:
    text = str(value if value is not None else "").strip().replace(",", ".")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    parsed = float(match.group(0)) if match else None
    if parsed is None:
        try:
            parsed = float(value)
        except Exception:
            parsed = None
    return parsed if isinstance(parsed, (int, float)) and math.isfinite(parsed) else fallback


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def normalize_activity_level(activity_level: Any) -> str:
    v = str(activity_level or "").strip().lower()
    mapping = {
        "sedentary": "sedentary",
        "desk job": "sedentary",
        "light": "light",
        "light active": "light",
        "lightly active": "light",
        "moderate": "moderate",
        "moderate active": "moderate",
        "moderately active": "moderate",
        "heavy": "heavy",
        "very active": "heavy",
        "very active worker": "heavy",
        "active": "heavy",
    }
    return mapping.get(v, "sedentary")


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    if not height_cm or height_cm <= 0:
        return 22.0
    h_m = height_cm / 100.0
    return weight_kg / (h_m * h_m)


def calculate_target_weight_kg(height_cm: float, target_bmi: float = BMI_GOAL) -> float:
    if not height_cm or height_cm <= 0:
        return 0.0
    h_m = height_cm / 100.0
    return target_bmi * h_m * h_m


def get_bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Overweight"
    return "Obese"


def calculate_bmr(weight_kg: float, height_cm: float, age: float, gender: Any) -> float:
    g = str(gender or "").strip().lower()
    is_male = g in {"male", "m", "man"}
    if is_male:
        return 66 + 13.7 * weight_kg + 5 * height_cm - 6.8 * age
    return 655 + 9.6 * weight_kg + 1.8 * height_cm - 4.7 * age


def calculate_tdee(bmr_kcal: float, activity_level: Any) -> float:
    activity = normalize_activity_level(activity_level)
    mult = ACTIVITY_MULTIPLIERS.get(activity, ACTIVITY_MULTIPLIERS["sedentary"])
    return bmr_kcal * mult


def _protein_g_per_kg_target(bmi_category: str) -> float:
    c = str(bmi_category or "").lower()
    if c == "underweight":
        return 1.6
    if c == "normal":
        return 1.2
    if c == "overweight":
        return 1.4
    if c == "obese":
        return 1.6
    return 1.2


def _fat_percent_preset(bmi_category: str) -> Dict[str, float]:
    c = str(bmi_category or "").lower()
    if c == "underweight":
        return {"min": 0.25, "max": 0.35, "default": 0.32}
    if c == "normal":
        return {"min": 0.25, "max": 0.35, "default": 0.28}
    if c == "overweight":
        return {"min": 0.2, "max": 0.3, "default": 0.22}
    if c == "obese":
        return {"min": 0.2, "max": 0.3, "default": 0.2}
    return {"min": FAT_PERCENT_RANGE["min"], "max": FAT_PERCENT_RANGE["max"], "default": 0.25}


def calculate_daily_targets(profile: Dict[str, Any]) -> Dict[str, Any]:
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
