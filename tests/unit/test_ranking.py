import pytest
from services.ranking_service import (
    _relative_error,
    _macro_weights,
    _macro_score,
    _preview_scaled_macros,
    _normalized_meal_distribution,
    session_target_macros
)

def test_relative_error():
    assert _relative_error(100, 100) == 0.0
    assert _relative_error(110, 100) == 0.1
    assert _relative_error(90, 100) == 0.1
    assert _relative_error(100, 0) == 1.0
    assert _relative_error(0, 0) == 0.0

def test_macro_weights():
    assert _macro_weights("underweight")["protein"] == 1.35
    assert _macro_weights("obese")["fat"] == 1.05
    assert _macro_weights("overweight")["carbs"] == 0.55
    assert _macro_weights("normal")["calories"] == 1.8

def test_macro_score():
    macros = {"caloriesKcal": 100, "proteinG": 10, "carbsG": 20, "fatG": 5}
    expected = {"caloriesKcal": 100, "proteinG": 10, "carbsG": 20, "fatG": 5}
    weights = {"calories": 1.0, "protein": 1.0, "carbs": 1.0, "fat": 1.0}
    assert _macro_score(macros, expected, weights) == 0.0

def test_preview_scaled_macros():
    macros = {"caloriesKcal": 100, "proteinG": 10, "carbsG": 20, "fatG": 5, "fiberG": 2}
    expected = {"caloriesKcal": 150}
    factor, scaled = _preview_scaled_macros(macros, expected)
    assert factor == 1.5
    assert scaled["caloriesKcal"] == 150
    assert scaled["proteinG"] == 15
    
    # Boundary caps: max 2.5
    expected_high = {"caloriesKcal": 300}
    factor_high, _ = _preview_scaled_macros(macros, expected_high)
    assert factor_high == 2.5

def test_normalized_meal_distribution():
    dist = _normalized_meal_distribution(["breakfast", "lunch"])
    assert "breakfast" in dist
    assert "dinner" not in dist
    assert abs(sum(dist.values()) - 1.0) < 0.001

def test_session_target_macros():
    targets = {"dailyCalories": 2000, "proteinG": 100, "carbsG": 200, "fatG": 50, "fiberG": 30}
    res = session_target_macros(targets, "breakfast", ["breakfast", "lunch", "dinner"])
    assert res["caloriesKcal"] > 0
    assert res["proteinG"] > 0
