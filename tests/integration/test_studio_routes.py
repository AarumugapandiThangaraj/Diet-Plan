import pytest
from unittest.mock import patch

def test_studio_meta(client):
    res = client.get("/api/studio/meta?cuisine=north_indian")
    assert res.status_code == 200
    data = res.json()
    assert "mealTimes" in data
    assert "mealsCount" in data

def test_studio_targets(client, mock_profile_male):
    # TargetsRequest expects {"profile": StudioProfile}
    res = client.post("/api/studio/targets", json={"profile": mock_profile_male})
    assert res.status_code == 200
    data = res.json()
    assert "dailyCalories" in data
    assert "proteinG" in data

def test_studio_rank(client, mock_profile_male):
    # RankRequest expects profile, mealTimes (list), and limit
    req_body = {
        "profile": mock_profile_male,
        "mealTimes": ["lunch"],
        "limit": 5
    }
    res = client.post("/api/studio/rank", json=req_body)
    assert res.status_code == 200
    data = res.json()
    assert "rankedByTime" in data

def test_studio_plan_build(client, mock_profile_male):
    # BuildPlanRequest expects profile, days (ge 1, le 21), and mealTimes
    req_body = {
        "profile": mock_profile_male,
        "days": 3,
        "mealTimes": ["dinner"],
        "poolsByTime": {
            "dinner": ["MEAL_1"]
        },
        "assignmentByTime": {
            "dinner": ["MEAL_1"]
        }
    }
    res = client.post("/api/studio/plan/build", json=req_body)
    assert res.status_code == 200
    data = res.json()
    assert "targets" in data
    assert "mealTimes" in data
