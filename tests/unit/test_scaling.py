from domain.scaling_formulas import (
    clamp,
    ensure_macros,
    scale_macros,
    sum_ingredient_macros,
    sum_food_macros,
    format_nutritive_values,
    scale_meal_to_targets
)

def test_clamp():
    assert clamp(5, 1, 10) == 5
    assert clamp(0, 1, 10) == 1
    assert clamp(15, 1, 10) == 10

def test_ensure_macros():
    raw = {"caloriesKcal": 200, "proteinG": "15.5", "carbsG": None, "fatG": 10}
    clean = ensure_macros(raw)
    assert clean["caloriesKcal"] == 200.0
    assert clean["proteinG"] == 15.5
    assert clean["carbsG"] == 0.0
    assert clean["fatG"] == 10.0
    assert clean["fiberG"] == 0.0

def test_scale_macros():
    macros = {"caloriesKcal": 100, "proteinG": 10, "carbsG": 20, "fatG": 5, "fiberG": 2}
    scaled = scale_macros(macros, 1.5)
    assert scaled["caloriesKcal"] == 150.0
    assert scaled["proteinG"] == 15.0
    assert scaled["carbsG"] == 30.0
    assert scaled["fatG"] == 7.5
    assert scaled["fiberG"] == 3.0

def test_sum_ingredient_macros():
    ings = [
        {"macros": {"caloriesKcal": 50, "proteinG": 5}},
        {"macros": {"caloriesKcal": 100, "carbsG": 10}}
    ]
    totals = sum_ingredient_macros(ings)
    assert totals["caloriesKcal"] == 150.0
    assert totals["proteinG"] == 5.0
    assert totals["carbsG"] == 10.0

def test_format_nutritive_values():
    macros = {"caloriesKcal": 250, "proteinG": 20.5, "carbsG": 30, "fatG": 5.25, "fiberG": 4}
    txt = format_nutritive_values(macros)
    assert "250 kcal" in txt
    assert "Protein 20.5 g" in txt
    assert "Carbs 30 g" in txt
    assert "Fat 5.25 g" in txt
    assert "Fiber 4 g" in txt

def test_scale_meal_to_targets():
    meal = {
        "Meal_ID": "meal_1",
        "meal_name": "Test Meal",
        "_macros": {"caloriesKcal": 200, "proteinG": 10, "carbsG": 20, "fatG": 5, "fiberG": 2},
        "foods_struct": [
            {
                "id": "food_1",
                "name": "Food 1",
                "quantity": 100,
                "unit": "g",
                "macros": {"caloriesKcal": 200, "proteinG": 10, "carbsG": 20, "fatG": 5, "fiberG": 2},
                "ingredients_struct": [
                    {
                        "id": "ing_1",
                        "name": "Ingredient 1",
                        "quantity": 50,
                        "unit": "g",
                        "macros": {"caloriesKcal": 200, "proteinG": 10, "carbsG": 20, "fatG": 5, "fiberG": 2}
                    }
                ]
            }
        ]
    }
    targets = {"caloriesKcal": 400}
    res = scale_meal_to_targets(meal, targets)
    assert res["scaleFactorRequested"] == 2.0
    assert res["scaleFactorApplied"] == 2.0
    scaled_meal = res["scaledMeal"]
    assert scaled_meal["macros"]["caloriesKcal"] == 400.0
