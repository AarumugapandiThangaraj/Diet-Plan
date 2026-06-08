import sys
import os
from pathlib import Path
import pytest

# Add backend directory to Python path
backend_path = str(Path(__file__).resolve().parent.parent / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

@pytest.fixture
def mock_profile_male():
    return {
        "age": 30,
        "gender": "male",
        "heightCm": 175,
        "weightKg": 75,
        "activityLevel": "moderate",
        "cuisineType": "north_indian",
        "goal": "hair_repair",
        "mealTimes": ["breakfast", "lunch", "dinner"]
    }

@pytest.fixture
def mock_profile_female():
    return {
        "age": 25,
        "gender": "female",
        "heightCm": 160,
        "weightKg": 50,
        "activityLevel": "sedentary",
        "cuisineType": "south_indian",
        "goal": "skin_repair",
        "mealTimes": ["breakfast", "lunch", "evening", "dinner"]
    }
