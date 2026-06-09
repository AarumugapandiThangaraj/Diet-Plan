import pytest
from unittest.mock import patch

def test_studio_swap_meal_options(client, mock_profile_male):
    req_body = {
        "profile": mock_profile_male,
        "mealTime": "lunch",
        "currentMealId": "MEAL_1",
        "targetMacros": None,
        "excludeMealIds": [],
        "allowedMealIds": [],
        "topN": 5
    }
    with patch("studio.router.get_meal_swap_options_service") as mock_service:
        mock_service.return_value = {
            "targetMacros": {"caloriesKcal": 500},
            "options": []
        }
        res = client.post("/api/studio/swap/meal/options", json=req_body)
        assert res.status_code == 200
        assert "options" in res.json()

def test_studio_swap_meal_apply(client):
    req_body = {
        "meal": {
            "Meal_ID": "MEAL_1",
            "meal_name": "Tomato Soup Dinner",
            "macros": {
                "caloriesKcal": 30.0,
                "proteinG": 1.0,
                "carbsG": 6.0,
                "fatG": 0.5,
                "fiberG": 1.0
            }
        }
    }
    res = client.post("/api/studio/swap/meal/apply", json=req_body)
    assert res.status_code == 200
    assert "meal" in res.json()

def test_studio_swap_food_options(client):
    req_body = {
        "meal": {
            "Meal_ID": "MEAL_1",
            "meal_name": "Tomato Soup Dinner",
            "cuisine_type": "north_indian",
            "foods": [
                {
                    "id": "FOOD_1",
                    "name": "Tomato Soup",
                    "quantity": 100.0,
                    "unit": "g"
                }
            ]
        },
        "foodName": "Tomato Soup",
        "topN": 3
    }
    with patch("studio.router.get_food_swap_options_service") as mock_service:
        mock_service.return_value = {
            "matchedSource": {},
            "options": []
        }
        res = client.post("/api/studio/swap/food/options", json=req_body)
        assert res.status_code == 200
        assert "options" in res.json()

def test_studio_swap_food_apply(client):
    req_body = {
        "meal": {
            "Meal_ID": "MEAL_1",
            "meal_name": "Tomato Soup Dinner",
            "cuisine_type": "north_indian",
            "foods": [
                {
                    "id": "FOOD_1",
                    "name": "Tomato Soup",
                    "quantity": 100.0,
                    "unit": "g"
                }
            ]
        },
        "option": {
            "foodId": "FOOD_2",
            "name": "Onion Soup",
            "quantity": 100.0,
            "unit": "g",
            "macros": {"caloriesKcal": 40.0}
        }
    }
    with patch("studio.router.apply_food_swap_service") as mock_service:
        mock_service.return_value = {"Meal_ID": "MEAL_1", "foods": []}
        res = client.post("/api/studio/swap/food/apply", json=req_body)
        assert res.status_code == 200
        assert "meal" in res.json()

def test_studio_substitutes_from_ingredients(client):
    req_body = {
        "ingredients": "milk, wheat"
    }
    res = client.post("/api/studio/substitutes/from-ingredients", json=req_body)
    assert res.status_code == 200
    data = res.json()
    assert "choices" in data
    assert "substitutesByKey" in data
