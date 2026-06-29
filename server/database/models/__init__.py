"""Database models package"""

# Catalog models (foods, cuisines, ingredients, meals)
from .catalog import (
    Cuisine,
    MealSession,
    MasterIngredient,
    Food,
    FoodIngredient,
    Meal,
    MealFood,
    Substitute,
)

# Plan models (diet plans and tracking)
from .plan import (
    DietPlan,
    DietPlanDay,
    DietPlanMeal,
    DietPlanMealFood,
    DietPlanMealFoodIngredient,
    DietPlanMealConsumption,
)

# User models (profiles, health data)
from .user import (
    UserHealthProfile,
    UserGoal,
    UserWeightLog,
    UserDailyIntake,
    UserHydrationLog,
)

# Preference models
from .preference import UserPreference

# Concern/tag models
from .concern import FoodConcernTag, MealConcernTag

# Chat models
from .chat import ChatSession, ChatMessage

__all__ = [
    # Catalog
    'Cuisine',
    'MealSession',
    'MasterIngredient',
    'Food',
    'FoodIngredient',
    'Meal',
    'MealFood',
    'Substitute',
    # Plan
    'DietPlan',
    'DietPlanDay',
    'DietPlanMeal',
    'DietPlanMealFood',
    'DietPlanMealFoodIngredient',
    'DietPlanMealConsumption',
    # User
    'UserHealthProfile',
    'UserGoal',
    'UserWeightLog',
    'UserDailyIntake',
    'UserHydrationLog',
    # Preferences
    'UserPreference',
    # Concerns
    'FoodConcernTag',
    'MealConcernTag',
    # Chat
    'ChatSession',
    'ChatMessage',
]

