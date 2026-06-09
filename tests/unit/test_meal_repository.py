import pytest
from repositories.meal_repository import (
    ingredient_index_by_id,
    load_master_meals,
    meal_index_by_id,
    _unit_is_gram
)

def test_unit_is_gram():
    assert _unit_is_gram("g") is True
    assert _unit_is_gram("ml") is True
    assert _unit_is_gram("piece") is False

def test_ingredient_index():
    index = ingredient_index_by_id("north_indian")
    assert "ING_1" in index
    assert index["ING_1"]["name"] == "Tomato"

def test_load_master_meals():
    meals = load_master_meals("north_indian")
    assert len(meals) == 1
    assert meals[0]["Meal_ID"] == "MEAL_1"
    assert meals[0]["meal_name"] == "Tomato Soup Dinner"

def test_meal_index_by_id():
    idx = meal_index_by_id("north_indian")
    assert "MEAL_1" in idx
    assert idx["MEAL_1"]["meal_name"] == "Tomato Soup Dinner"
