from domain.nutrition_formulas import (
    normalize_activity_level,
    calculate_bmi,
    calculate_target_weight_kg,
    get_bmi_category,
    calculate_bmr,
    calculate_tdee
)
from services.nutrition_service import calculate_daily_targets

def test_normalize_activity_level():
    assert normalize_activity_level("desk job") == "sedentary"
    assert normalize_activity_level("lightly active") == "light"
    assert normalize_activity_level("moderate active") == "moderate"
    assert normalize_activity_level("very active") == "heavy"
    assert normalize_activity_level("unknown") == "sedentary"

def test_calculate_bmi():
    # Weight 75, Height 175cm -> 75 / (1.75 * 1.75) = 24.489
    bmi = calculate_bmi(75, 175)
    assert abs(bmi - 24.49) < 0.1
    # Check invalid height
    assert calculate_bmi(75, 0) == 22.0

def test_calculate_target_weight_kg():
    # target weight = 22 * (1.75 * 1.75) = 67.375
    target_weight = calculate_target_weight_kg(175)
    assert abs(target_weight - 67.375) < 0.01
    assert calculate_target_weight_kg(0) == 0.0

def test_get_bmi_category():
    assert get_bmi_category(17.0) == "Underweight"
    assert get_bmi_category(22.0) == "Normal"
    assert get_bmi_category(27.0) == "Overweight"
    assert get_bmi_category(32.0) == "Obese"

def test_calculate_bmr():
    # Male: 66 + 13.7 * weight_kg + 5 * height_cm - 6.8 * age
    bmr_m = calculate_bmr(75, 175, 30, "male")
    expected_m = 66 + 13.7 * 75 + 5 * 175 - 6.8 * 30
    assert abs(bmr_m - expected_m) < 0.01

    # Female: 655 + 9.6 * weight_kg + 1.8 * height_cm - 4.7 * age
    bmr_f = calculate_bmr(50, 160, 25, "female")
    expected_f = 655 + 9.6 * 50 + 1.8 * 160 - 4.7 * 25
    assert abs(bmr_f - expected_f) < 0.01

def test_calculate_tdee():
    # BMR 1500, light activity multiplier 1.375 -> 2062.5
    assert abs(calculate_tdee(1500, "light") - 2062.5) < 0.01

def test_calculate_daily_targets(mock_profile_male, mock_profile_female):
    targets_m = calculate_daily_targets(mock_profile_male)
    assert "dailyCalories" in targets_m
    assert "proteinG" in targets_m
    assert "carbsG" in targets_m
    assert "fatG" in targets_m
    
    targets_f = calculate_daily_targets(mock_profile_female)
    assert "dailyCalories" in targets_f
    assert targets_f["dailyCalories"] >= 1200
