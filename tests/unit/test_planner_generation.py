import pytest
from unittest.mock import patch, MagicMock
from services.planner_service import fetch_daily_targets_service, fetch_ranked_meals_service

def test_fetch_daily_targets_service(mock_profile_male):
    res = fetch_daily_targets_service(mock_profile_male)
    assert "dailyCalories" in res
    assert res["dailyCalories"] > 0

@patch("services.planner_service.rank_meals_for_meal_time")
def test_fetch_ranked_meals_service(mock_rank, mock_profile_male):
    mock_rank.return_value = {
        "ranked": [{"Meal_ID": "MEAL_1", "meal_name": "Oatmeal"}]
    }
    
    res = fetch_ranked_meals_service(mock_profile_male, ["breakfast"], limit=5)
    
    assert "targets" in res
    assert "rankedByTime" in res
    assert len(res["rankedByTime"]["breakfast"]) == 1
    assert res["rankedByTime"]["breakfast"][0]["Meal_ID"] == "MEAL_1"
