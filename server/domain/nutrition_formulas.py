import math
import re
from typing import Any, Dict
from config.constants import (
    ACTIVITY_MULTIPLIERS,
    BMI_GOAL,
    FAT_PERCENT_RANGE,
    FIBER_G_PER_1000_KCAL,
    FIBER_MIN_G_PER_DAY,
    WATER_ML_PER_KG_RANGE
)
# Let's write the helper normalize activity level inside normalizers or locally.
# Let's write a simple normalizer for activity level locally or import it.
# Let's import it from normalizers or write locally to keep cohesion.
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
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

def calculate_tdee(bmr_kcal: float, activity_level: Any, bmi_adjustment: float = 0.0) -> float:
    activity = normalize_activity_level(activity_level)
    mapping = {
        "sedentary": 1.40,
        "light": 1.55,
        "moderate": 1.70,
        "heavy": 1.90
    }
    mult = mapping.get(activity, 1.40)
    return bmr_kcal * mult + bmi_adjustment

def get_bmi_adjustment(bmi: float) -> float:
    if bmi < 18.5:
        return 300.0
    if bmi < 25.0:
        return 0.0
    if bmi < 30.0:
        return -300.0
    return -500.0

def get_age_midpoint(age_str: Any) -> float:
    # "25-30" -> 27.5
    s = str(age_str or "").strip()
    match = re.search(r"(\d+)-(\d+)", s)
    if match:
        low = float(match.group(1))
        high = float(match.group(2))
        return (low + high) / 2.0
    
    val = _to_safe_number(s, 30.0)
    return val

def get_water_target(activity_level: str) -> Dict[str, float]:
    activity = normalize_activity_level(activity_level)
    if activity in ("sedentary", "light"):
        return {"min": 3.0, "max": 3.5, "default": 3.25}
    return {"min": 4.0, "max": 4.5, "default": 4.25}

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
