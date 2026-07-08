"""Database models package"""

# Catalog models (foods, cuisines, ingredients, meals)
from .catalog import (
    Cuisine,
    MealSession,
    Food,
    Meal,
    MealFood,
    Substitute,
    FoodRole,
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
    DietPlanMealConsumption,
    DietPlanDayHydrationLog,
    DietPlanEvent,
)

# User models (profiles, health data)
from .user import (
    UserHealthProfile,
    UserGoal,
    UserWeightLog,
    UserDailyIntake,
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
    'Food',
    'Meal',
    'MealFood',
    'MealIngredient',
    'Substitute',
    # Plan
    'DietPlan',
    'DietPlanDay',
    'DietPlanMeal',
    'DietPlanMealFood',
    'DietPlanMealConsumption',
    'DietPlanEvent',
    # User
    'UserHealthProfile',
    'UserGoal',
    'UserWeightLog',
    'UserDailyIntake',
    'DietPlanDayHydrationLog',
    # Preferences
    'UserPreference',
    # Concerns
    'FoodConcernTag',
    'MealConcernTag',
    # Chat
    'ChatSession',
    'ChatMessage',
    'FoodRole',
    'PrimaryGoal',
    'SecondaryGoal',
    'MealPrimaryGoal',
    'MealSecondaryGoal',
]

