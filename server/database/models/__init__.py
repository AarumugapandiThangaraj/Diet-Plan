"""Database models package"""

# Catalog models (foods, cuisines, ingredients, meals)
from .catalog import (
    Cuisine,
    MealSession,
    Food,
    Meal,
    MealFood,
    MealIngredient,
    PrimaryGoal,
    SecondaryGoal,
    MealPrimaryGoal,
    MealSecondaryGoal,
)

# Plan models (diet plans and tracking)
from .plan import (
    DietPlan,
    DietPlanDay,
    DietPlanMeal,
    DietPlanMealFood,
    DietPlanEvent,
)

# User models (profiles, health data)
from .user import (
    UserHealthProfile,
    UserGoal,
)

# Preference models
# from .preference import UserPreference

# Concern/tag models
from .concern import FoodConcernTag, MealConcernTag

# Chat models
# from .chat import ChatSession, ChatMessage

__all__ = [
    # Catalog
    'Cuisine',
    'MealSession',
    'Food',
    'Meal',
    'MealFood',
    'MealIngredient',
    # Plan
    'DietPlan',
    'DietPlanDay',
    'DietPlanMeal',
    'DietPlanMealFood',
    'DietPlanEvent',
    # User
    'UserHealthProfile',
    'UserGoal',
    # Concerns
    'FoodConcernTag',
    'MealConcernTag',
    # Chat
    'PrimaryGoal',
    'SecondaryGoal',
    'MealPrimaryGoal',
    'MealSecondaryGoal',
]

