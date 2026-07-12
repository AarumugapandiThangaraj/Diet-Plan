from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator
from domain.payload_models import MealPayload


class StudioProfile(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "age": 28,
                "gender": "male",
                "heightCm": 175.0,
                "weightKg": 75.0,
                "activityLevel": "moderate",
                "goal": "skin_repair",
                "secondaryGoal": "",
                "dietType": "non_veg",
                "allergies": "peanut,gluten",
                "cuisineType": "south_indian"
            }
        }
    )

    age: int = Field(
        default=30,
        description="Age of the user in years (e.g. 28). Used to calculate BMR and nutrition needs.",
        json_schema_extra={"example": 28}
    )
    gender: str = Field(
        default="female",
        description="Gender of the user. Used in energy expenditure equations. Allowed values: 'male', 'female'.",
        json_schema_extra={"example": "male"}
    )
    heightCm: float = Field(
        default=165.0,
        description="Height of the user in centimeters (cm). Used to determine BMI and daily calorie needs.",
        json_schema_extra={"example": 175.0}
    )
    weightKg: float = Field(
        default=60.0,
        description="Current body weight of the user in kilograms (kg). Used for calorie/macronutrient distributions.",
        json_schema_extra={"example": 75.0}
    )
    activityLevel: str = Field(
        default="sedentary",
        description="Daily physical activity level. Multiplies BMR to calculate TDEE. Allowed values: 'sedentary' (BMR * 1.2), 'light' (BMR * 1.375), 'moderate' (BMR * 1.55), 'heavy' (BMR * 1.725).",
        json_schema_extra={"example": "moderate"}
    )
    goal: str = Field(
        default="skin_repair",
        description="Target health/nutrition objective. Allowed values: 'skin_repair' (prioritizes micronutrients/collagen-boosting), 'hair_repair' (focuses on protein/micronutrients).",
        json_schema_extra={"example": "skin_repair"}
    )
    secondaryGoal: str = Field(
        default="",
        description="Secondary target health/nutrition objective.",
        json_schema_extra={"example": "Weight Gain"}
    )
    dietType: str = Field(
        default="non_veg",
        description="Dietary preference pattern. Allowed values: 'veg' (vegetarian), 'non_veg' (includes meat, poultry, seafood).",
        json_schema_extra={"example": "non_veg"}
    )
    allergies: str = Field(
        default="",
        description="Comma-separated list of ingredients, allergens, or food items to exclude from recommendation pools.",
        json_schema_extra={"example": "peanut,gluten"}
    )
    cuisineType: str = Field(
        default="north_indian",
        description="Preferred regional cuisine catalog for food recommendations. Allowed values: 'north_indian', 'south_indian', 'uae', 'continental', 'mediterranean', 'african', 'americas', 'east_asian', 'southeast_asian', 'south_asian', 'middle_eastern', 'nordic', 'oceania', 'central', 'russian', 'fusion'.",
        json_schema_extra={"example": "south_indian"}
    )

    @field_validator("age", mode="before")
    @classmethod
    def parse_age(cls, v: Any) -> int:
        try:
            return int(float(str(v).strip()))
        except Exception:
            raise ValueError(f"Invalid age provided: {v}")

    @field_validator("heightCm", mode="before")
    @classmethod
    def parse_height(cls, v: Any) -> float:
        try:
            return float(str(v).strip())
        except Exception:
            raise ValueError(f"Invalid height provided: {v}")

    @field_validator("weightKg", mode="before")
    @classmethod
    def parse_weight(cls, v: Any) -> float:
        try:
            return float(str(v).strip())
        except Exception:
            raise ValueError(f"Invalid weight provided: {v}")


class TargetsProfile(BaseModel):
    activityLevel: str = Field(..., description="Daily physical activity level (e.g., 'moderate').")
    age: int = Field(..., description="Age of the user in years (e.g. 28).")
    gender: str = Field(..., description="Gender of the user (e.g., 'male').")
    goal: str = Field(..., description="Primary health/nutrition objective.")
    secondaryGoal: str = Field(default="", description="Secondary health/nutrition objective.")
    heightCm: float = Field(..., description="Height of the user in centimeters (cm).")
    weightKg: float = Field(..., description="Current body weight of the user in kilograms (kg).")

class TargetsRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "profile": {
                    "activityLevel": "moderate",
                    "age": 28,
                    "gender": "male",
                    "goal": "skin_repair",
                    "secondaryGoal": "Weight gain",
                    "heightCm": 175.0,
                    "weightKg": 75.0
                }
            }
        }
    )
    profile: TargetsProfile = Field(
        ...,
        description="User health, demographic, and dietary profile data used for calculation."
    )


class RankRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "profile": {
                    "age": 28,
                    "gender": "male",
                    "heightCm": 175.0,
                    "weightKg": 75.0,
                    "activityLevel": "moderate",
                    "goal": "skin_repair",
                    "secondaryGoal": "Weight gain",
                    "dietType": "non_veg",
                    "allergies": "",
                    "cuisineType": "south_indian"
                },
                "mealTimes": ["breakfast", "lunch", "dinner"],
                "limit": 10
            }
        }
    )
    profile: StudioProfile = Field(
        ...,
        description="User profile data for computing macro targets and filtering matching meals."
    )
    mealTimes: List[str] = Field(
        default_factory=list,
        description="List of target meal times/sessions to rank meals for. Valid values: 'early_morning', 'breakfast', 'mid_morning', 'lunch', 'evening', 'dinner', 'bedtime'.",
        json_schema_extra={"example": ["breakfast", "lunch", "dinner"]}
    )
    limit: int = Field(
        default=10,
        description="Maximum number of candidate meals to return per meal session/time after scoring.",
        json_schema_extra={"example": 10}
    )


class BuildPlanRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "profile": {
                    "age": 28,
                    "gender": "male",
                    "heightCm": 175.0,
                    "weightKg": 75.0,
                    "activityLevel": "moderate",
                    "goal": "skin_repair",
                    "secondaryGoal": "Weight gain",
                    "dietType": "non_veg",
                    "allergies": "",
                    "cuisineType": "south_indian"
                },
                "days": 3,
                "mealTimes": ["breakfast", "lunch", "dinner"],
                "poolsByTime": {
                    "breakfast": ["meal_1", "meal_2"],
                    "lunch": ["meal_3", "meal_4"],
                    "dinner": ["meal_5", "meal_6"]
                },
                
            }
        }
    )
    profile: StudioProfile = Field(
        ...,
        description="User profile data used to calculate targets and scale macros for each plan day."
    )
    days: int = Field(
        7,
        ge=1,
        le=21,
        description="Number of days to build the diet plan for (must be between 1 and 21 inclusive).",
        json_schema_extra={"example": 3}
    )
    mealTimes: List[str] = Field(
        default_factory=list,
        description="Ordered list of meal sessions to include in the plan.",
        json_schema_extra={"example": ["breakfast", "lunch", "dinner"]}
    )
    poolsByTime: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Dictionary mapping each meal time to a list of selected meal IDs available to assign.",
        json_schema_extra={
            "example": {
                "breakfast": ["meal_1", "meal_2"],
                "lunch": ["meal_3", "meal_4"],
                "dinner": ["meal_5", "meal_6"]
            }
        }
    )
    assignmentByTime: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Dictionary mapping each meal time to an ordered list of meal IDs assigned to each day (length must match 'days').",
        json_schema_extra={
            "example": {
                "breakfast": ["meal_1", "meal_2", "meal_1"],
                "lunch": ["meal_3", "meal_4", "meal_3"],
                "dinner": ["meal_5", "meal_6", "meal_5"]
            }
        }
    )


class SavePlanRequest(BaseModel):
    days: int = Field(
        ...,
        ge=1,
        le=21,
        description="Number of days in the diet plan."
    )
    plan_data: Dict[str, Any] = Field(
        ...,
        description="The full modified plan dictionary."
    )
    profile: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional user profile data to attach."
    )


class SubstitutesRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ingredients": "milk, paneer"
            }
        }
    )
    ingredients: str = Field(
        default="",
        description="Comma-separated query string of food ingredients to find substitutes for.",
        json_schema_extra={"example": "milk, paneer"}
    )


class MealSwapOptionsRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "planMealId": "02627b12-8428-4b13-9be2-4811d4c95f81",
                "cuisineType": "south_indian"
            }
        }
    )
    planMealId: Optional[str] = Field(
        default=None,
        description="Optional DietPlanMeal UUID. If provided, the backend will automatically look up the mealTime, currentMealId, targetMacros, and profile from the database."
    )
    profile: Optional[StudioProfile] = Field(
        default=None,
        description="User profile parameters used for filtering alternative meals by dietary constraint. Required if planMealId is not provided."
    )
    cuisineType: Optional[str] = Field(
        default=None,
        description="Optional cuisine filter (e.g. 'south_indian'). Takes precedence over profile."
    )
    mealTime: Optional[str] = Field(
        default=None,
        description="Specific meal time session context. E.g. 'breakfast', 'lunch', 'dinner'. Required if planMealId is not provided."
    )
    currentMealId: Optional[str] = Field(
        default=None,
        description="The ID of the meal being replaced. Required if planMealId is not provided."
    )
    targetMacros: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Specific target nutritional values (calories, protein, carbs, fat) to match. If omitted, uses default targets calculated for this meal session."
    )
    excludeMealIds: List[str] = Field(
        default_factory=list,
        description="List of meal IDs to exclude from the swap options list.",
        json_schema_extra={"example": ["meal_123"]}
    )
    allowedMealIds: List[str] = Field(
        default_factory=list,
        description="Whitelist of specific meal IDs to restrict the options search to.",
        json_schema_extra={"example": []}
    )
    topN: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of swap option meals to return (between 1 and 20).",
        json_schema_extra={"example": 5}
    )


class MealSwapApplyRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "planMealId": "02627b12-8428-4b13-9be2-4811d4c95f81",
                "newMealId": "201",
                "cuisineType": "south_indian",
                "macros": {
                    "caloriesKcal": 320.0,
                    "proteinG": 7.5,
                    "carbsG": 53.5,
                    "fatG": 8.7,
                    "fiberG": 3.6
                },
                "scaleFactorApplied": 1.0
            }
        }
    )
    planMealId: str = Field(
        ...,
        description="The ID of the meal instance in the database to be updated."
    )
    newMealId: str = Field(
        ...,
        description="The ID of the new meal chosen from the catalog."
    )
    cuisineType: str = Field(
        ...,
        description="The cuisine type of the new meal, used to locate it in the catalog."
    )
    macros: Dict[str, float] = Field(
        ...,
        description="The exact final macros to apply to the database row (allows frontend to apply portion scaling)."
    )
    scaleFactorApplied: Optional[float] = Field(
        default=1.0,
        description="The scale factor applied to the base recipe."
    )


class FoodSwapOptionsRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "meal": {
                    "id": "meal_123",
                    "name": "Oatmeal with Almonds",
                    "cuisine_type": "continental",
                    "foods": [
                        {"name": "Oats", "quantity": 50, "unit": "g"},
                        {"name": "Almonds", "quantity": 10, "unit": "g"}
                    ]
                },
                "foodName": "Almonds",
                "topN": 5
            }
        }
    )
    meal: MealPayload = Field(
        ...,
        description="Complete context of the current meal payload containing the food item to swap.",
        json_schema_extra={
            "example": {
                "meal": {
                    "id": "meal_123",
                    "name": "Oatmeal with Almonds",
                    "cuisine_type": "continental",
                    "foods": [
                        {"name": "Oats", "quantity": 50, "unit": "g"},
                        {"name": "Almonds", "quantity": 10, "unit": "g"}
                    ]
                },
                "foodName": "Almonds",
                "topN": 5
            }
        }
    )
    foodName: str = Field(
        ...,
        description="Exact name of the food item in the meal that needs to be swapped out.",
        json_schema_extra={"example": "Almonds"}
    )
    topN: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of substitute options to return.",
        json_schema_extra={"example": 5}
    )


class FoodSwapApplyRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "meal": {
                    "id": "e2343b67-a021-4f11-92b1-5e8f8103c819",
                    "name": "Oatmeal with Almonds",
                    "foods_struct": [
                        {"name": "Oats", "quantity": 50, "unit": "g", "food_instance_id": "a9043b67-a021-4f11-92b1-5e8f8103c822"},
                        {"name": "Almonds", "quantity": 10, "unit": "g", "food_instance_id": "b7043b67-c011-4f21-93a1-2e8f8103d111"}
                    ]
                },
                "planId": "3b351669-8451-490a-9e98-583d40cba2ed",
                "version": 1,
                "option": {
                    "replacementMealId": "meal_20002",
                    "replacement": {
                        "name": "Walnuts",
                        "quantity": 12,
                        "unit": "g"
                    },
                    "projectedMealMacros": {
                        "caloriesKcal": 654,
                        "proteinG": 15.2,
                        "carbsG": 13.7,
                        "fatG": 65.2
                    }
                }
            }
        }
    )
    planId: Optional[str] = Field(
        None,
        description="The ID of the plan being edited, if applicable."
    )
    version: Optional[int] = Field(
        None,
        description="The current version of the plan, for optimistic concurrency."
    )
    meal: MealPayload = Field(
        ...,
        description="The current meal payload containing the food item being replaced."
    )
    option: Dict[str, Any] = Field(
        ...,
        description="The swap option payload containing replacement parameters (target_food, ratio, etc.)."
    )


class IngredientSwapOptionsRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "meal": {
                    "id": "meal_789",
                    "name": "Chicken Curry",
                    "ingredients": "Chicken breast, Onion, Tomato, Mustard oil"
                },
                "ingredientQuery": "Mustard oil",
                "topN": 5
            }
        }
    )
    meal: MealPayload = Field(
        ...,
        description="The current meal payload containing the target ingredient."
    )
    ingredientQuery: str = Field(
        ...,
        description="Search term / ingredient name within the meal to find substitutes for.",
        json_schema_extra={"example": "Mustard oil"}
    )
    topN: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of options to return.",
        json_schema_extra={"example": 5}
    )


class IngredientSwapApplyRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "meal": {
                    "id": "meal_789",
                    "name": "Chicken Curry",
                    "ingredients": "Chicken breast, Onion, Tomato, Mustard oil"
                },
                "option": {
                    "source_ingredient": "Mustard oil",
                    "target_ingredient": "Olive oil",
                    "ratio": 1.0
                }
            }
        }
    )
    meal: MealPayload = Field(
        ...,
        description="The current meal payload to modify."
    )
    option: Dict[str, Any] = Field(
        ...,
        description="Selected replacement option parameters."
    )


class ChatMessage(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "role": "user",
                "text": "I am feeling bloated and need a lighter dinner tonight."
            }
        }
    )
    role: str = Field(
        ...,
        description="Sender role. Allowed values: 'user', 'assistant' (or 'bot').",
        json_schema_extra={"example": "user"}
    )
    text: str = Field(
        ...,
        description="The conversational text message content.",
        json_schema_extra={"example": "I am feeling bloated and need a lighter dinner tonight."}
    )


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Can you swap my high protein breakfast for something lighter?",
                "history": [
                    {"role": "user", "text": "Hi, I am planning my meals."},
                    {"role": "assistant", "text": "Hello! I can help you plan your diet."}
                ],
                "agentName": "NutriBot",
                "context": {
                    "current_meal_time": "breakfast",
                    "calories_target": 450
                }
            }
        }
    )
    message: str = Field(
        ...,
        description="The current user message query.",
        json_schema_extra={"example": "Can you swap my high protein breakfast for something lighter?"}
    )
    history: List[ChatMessage] = Field(
        default_factory=list,
        description="Conversation history of preceding chat messages for context memory.",
        json_schema_extra={
            "example": [
                {"role": "user", "text": "Hi, I am planning my meals."},
                {"role": "assistant", "text": "Hello! I can help you plan your diet."}
            ]
        }
    )
    agentName: str = Field( 
        default="NutriBot",
        description="The AI agent personality variant to address. Defaults to 'NutriBot'.",
        json_schema_extra={"example": "NutriBot"}
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional frontend context properties (e.g. current selected meal/targets) passed to the AI agent.",
        json_schema_extra={
            "example": {
                "current_meal_time": "breakfast",
                "calories_target": 450
            }
        }
    )


class ChatResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reply": "I have selected a light Oats Porridge for you. It matches your request and is easy on digestion.",
                "preferences": {"exclude": ["spicy"]},
                "quickReplies": [
                    {"title": "Show recipe", "payload": "/recipe"},
                    {"title": "Looks good!", "payload": "/confirm"}
                ],
                "action": {
                    "type": "swap_meal",
                    "parameters": {"meal_id": "meal_oats_1"}
                }
            }
        }
    )
    reply: str = Field(
        ...,
        description="AI response text reply.",
        json_schema_extra={"example": "I have selected a light Oats Porridge for you. It matches your request and is easy on digestion."}
    )
    preferences: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Dynamically extracted or updated user dietary preferences/constraints (e.g. allergies, dislikes).",
        json_schema_extra={"example": {"exclude": ["spicy"]}}
    )
    quickReplies: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Recommended button chips/options to present to the user for fast responses.",
        json_schema_extra={
            "example": [
                {"title": "Show recipe", "payload": "/recipe"},
                {"title": "Looks good!", "payload": "/confirm"}
            ]
        }
    )
    action: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured system action parameters extracted from user message (e.g. trigger meal swap commands).",
        json_schema_extra={
            "example": {
                "type": "swap_meal",
                "parameters": {"meal_id": "meal_oats_1"}
            }
        }
    )


# --- Response Models for Studio Endpoints ---

class StudioMetaResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "mealTimes": ["early_morning", "breakfast", "mid_morning", "lunch", "evening", "dinner", "bedtime"],
                "mealsCount": 420,
                "dataSource": "[north_indian] PostgreSQL Database (Authoritative Ingredient Cache)",
                "validCuisines": {
                    "north_indian": "North Indian",
                    "south_indian": "South Indian"
                },
                "activeCuisine": "north_indian"
            }
        }
    )
    mealTimes: List[str] = Field(
        ...,
        description="List of all supported meal times in order.",
        json_schema_extra={"example": ["early_morning", "breakfast", "mid_morning", "lunch", "evening", "dinner", "bedtime"]}
    )
    mealsCount: int = Field(
        ...,
        description="Total count of recipe/meal options available for the selected cuisine in the database.",
        json_schema_extra={"example": 420}
    )
    dataSource: str = Field(
        ...,
        description="Descriptive identifier of the active database connection or cache source.",
        json_schema_extra={"example": "[north_indian] PostgreSQL Database (Authoritative Ingredient Cache)"}
    )
    validCuisines: Dict[str, str] = Field(
        ...,
        description="Key-value mapping of all supported cuisine catalog identifiers to human-readable names.",
        json_schema_extra={
            "example": {
                "north_indian": "North Indian",
                "south_indian": "South Indian"
            }
        }
    )
    activeCuisine: str = Field(
        ...,
        description="The current active cuisine tag selected for query context.",
        json_schema_extra={"example": "north_indian"}
    )


class DailyTargetsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "targetWeightKg": 67.3,
                "weightDeltaKg": -7.7,
                "bmi": 24.5,
                "bmiCategory": "Overweight",
                "bmr": 1680,
                "tdee": 2604,
                "waterL": 2.4,
               "activityLevel": "moderate"
            }
        }
    )
    # age: int = Field(..., description="Age in years.", json_schema_extra={"example": 28})
    # heightCm: float = Field(..., description="Height in centimeters.", json_schema_extra={"example": 175.0})
    # weightKg: float = Field(..., description="Weight in kilograms.", json_schema_extra={"example": 75.0})
    # targetBmi: int = Field(..., description="Target body mass index used to determine target weight (default 22).", json_schema_extra={"example": 22})
    idealWeight: float = Field(..., description="Calculated healthy target body weight in kilograms.", json_schema_extra={"example": 67.3})
    weightDeltaKg: float = Field(..., description="Difference between target weight and current weight in kilograms.", json_schema_extra={"example": -7.7})
    bmi: float = Field(..., description="Calculated current body mass index (BMI).", json_schema_extra={"example": 24.5})
    bmiCategory: str = Field(..., description="Current BMI health classification (e.g. Underweight, Normal, Overweight).", json_schema_extra={"example": "Overweight"})
    bmr: int = Field(..., description="Basal Metabolic Rate in kcal, calculated using Mifflin-St Jeor equation.", json_schema_extra={"example": 1680})
    tdee: int = Field(..., description="Total Daily Energy Expenditure in kcal (BMR multiplied by activity level factor).", json_schema_extra={"example": 2604})
    # maintenanceCalories: int = Field(..., description="Maintenance calorie needs in kcal.", json_schema_extra={"example": 2604})
    # dailyCalories: int = Field(..., description="Recommended daily calorie target in kcal for the selected goal.", json_schema_extra={"example": 2104})
    # proteinG: int = Field(..., description="Target protein intake in grams.", json_schema_extra={"example": 131})
    # proteinGMin: int = Field(default=0, description="Minimum healthy protein threshold in grams.", json_schema_extra={"example": 110})
    # proteinGMax: int = Field(default=0, description="Maximum healthy protein threshold in grams.", json_schema_extra={"example": 150})
    # carbsG: int = Field(..., description="Target carbohydrates intake in grams.", json_schema_extra={"example": 236})
    # fatG: int = Field(..., description="Target fat intake in grams.", json_schema_extra={"example": 70})
    # fatGMin: int = Field(..., description="Minimum healthy fat threshold in grams.", json_schema_extra={"example": 46})
    # fatGMax: int = Field(..., description="Maximum healthy fat threshold in grams.", json_schema_extra={"example": 81})
    # carbsGMin: int = Field(..., description="Minimum carbohydrates range threshold in grams.", json_schema_extra={"example": 210})
    # carbsGMax: int = Field(..., description="Maximum carbohydrates range threshold in grams.", json_schema_extra={"example": 263})
    # fiberG: int = Field(..., description="Target daily dietary fiber intake in grams.", json_schema_extra={"example": 29})
    # fiberGMin: int = Field(default=25, description="Minimum dietary fiber intake in grams.", json_schema_extra={"example": 25})
    # fiberGMax: int = Field(default=35, description="Maximum dietary fiber intake in grams.", json_schema_extra={"example": 35})
    # fiberGRaw: int = Field(default=0, description="Raw calculated fiber target.", json_schema_extra={"example": 29})
    # fiberGMinimum: int = Field(default=25, description="Minimum recommended fiber intake (default 25g).", json_schema_extra={"example": 25})
    waterL: float = Field(..., description="Target daily water intake in liters.", json_schema_extra={"example": 2.4})
    # waterLMin: float = Field(..., description="Minimum recommended water intake in liters.", json_schema_extra={"example": 2.25})
    # waterLMax: float = Field(..., description="Maximum recommended water intake in liters.", json_schema_extra={"example": 2.62})
    activityLevelNormalized: str = Field(..., description="Normalized activity level label matching constants.", json_schema_extra={"example": "moderate"})
   
    idealWeight: float = Field(..., description="Calculated healthy target body weight in kilograms.", json_schema_extra={"example": 67.3})
    weightDeltaKg: float = Field(..., description="Difference between target weight and current weight in kilograms.", json_schema_extra={"example": -7.7})
    bmi: float = Field(..., description="Calculated current body mass index (BMI).", json_schema_extra={"example": 24.5})
    bmiCategory: str = Field(..., description="Current BMI health classification (e.g. Underweight, Normal, Overweight).", json_schema_extra={"example": "Overweight"})
    bmr: int = Field(..., description="Basal Metabolic Rate in kcal, calculated using Mifflin-St Jeor equation.", json_schema_extra={"example": 1680})
    tdee: int = Field(..., description="Total Daily Energy Expenditure in kcal (BMR multiplied by activity level factor).", json_schema_extra={"example": 2604})
    waterL: float = Field(..., description="Target daily water intake in liters.", json_schema_extra={"example": 2.4})
    waterLMin: float = Field(..., description="Minimum recommended water intake in liters.", json_schema_extra={"example": 2.25})
    waterLMax: float = Field(..., description="Maximum recommended water intake in liters.", json_schema_extra={"example": 2.62})
    activityLevelNormalized: str = Field(..., description="Normalized activity level label matching constants.", json_schema_extra={"example": "moderate"})


class MacroNutrients(BaseModel):
    """Nutritional macro breakdown for a meal or food item."""
    caloriesKcal: float = Field(0.0, description="Energy in kilocalories.")
    proteinG: float = Field(0.0, description="Protein in grams.")
    carbsG: float = Field(0.0, description="Carbohydrates in grams.")
    fatG: float = Field(0.0, description="Fat in grams.")
    fiberG: float = Field(0.0, description="Dietary fiber in grams.")


class PlanFoodItem(BaseModel):
    """A single food item within a meal, with its scaled quantity and macros."""
    model_config = ConfigDict(extra='allow')

    id: Optional[str] = Field(None, description="Unique food identifier from the catalog.")
    # food_instance_id: Optional[str] = Field(None, description="Database row ID of this food in DietPlanMealFood table.")
    name: Optional[str] = Field(None, description="Display name of the food item.")
    quantity: float = Field(0.0, description="Scaled serving quantity.")
    unit: str = Field("g", description="Unit of measurement (g, ml, piece, etc.).")


class RankedMeal(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra='allow')

    Meal_ID: Optional[str] = Field(None, description="Catalog meal identifier.")
    meal_name: Optional[str] = Field(None, description="Recipe display name.")
    Discription: Optional[str] = Field(None, description="Recipe preparation instructions.")
    imageUrl: Optional[str] = Field(None, description="Image URL or ID.")
    serving_size: Optional[str] = Field(None, description="Scaled human-readable serving description.")
    total_quantity: Optional[float] = Field(None, description="Sum of all scaled food quantities.")
    total_quantity_unit: Optional[str] = Field("g", description="Unit for the total quantity.")
    foods_struct: List[PlanFoodItem] = Field(default_factory=list, description="Scaled food items list.")
    macros: Optional[MacroNutrients] = Field(None, alias="_macros", description="Scaled macros for this ranked candidate.")


class RankResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                
                "rankedByTime": {
                    "breakfast": [
                        {
                "Meal_ID": "4533",
                "meal_name": "Appam and Stew",
                "Discription": "",
                "image_ID": "",
                "_macros": {
                    "caloriesKcal": 554,
                    "proteinG": 12,
                    "carbsG": 85,
                    "fatG": 20,
                    "fiberG": 10
                }
            },
                    ],
                    "lunch": [],
                    "dinner": []
                }
            }
        }
    )
    # targets: DailyTargetsResponse = Field(..., description="Calculated daily nutritional targets based on profile parameters.")
    rankedByTime: Dict[str, List[RankedMeal]] = Field(
        ...,
        description="Dictionary mapping each requested meal time to a sorted list of candidate meal objects with matching scores."
    )


class ScaleInfo(BaseModel):
    """Scaling metadata applied to a meal to match session-level macro targets."""
    requested: float = Field(1.0, description="Scale factor requested by the algorithm.")
    applied: float = Field(1.0, description="Scale factor actually applied after clamping.")


class PlanMealItem(BaseModel):
    """A single meal assigned to a meal session within a day plan."""
    model_config = ConfigDict(extra='allow')

    id: Optional[str] = Field(None, description="Meal instance UUID (set after DB persistence).")
    Meal_ID: Optional[str] = Field(None, description="Catalog meal identifier from the cuisine index.")
    name: Optional[str] = Field(None, description="Recipe display name.")
    session: Optional[str] = Field(None, description="Meal session code (e.g. breakfast, lunch).")
    cuisine_type: Optional[str] = Field(None, description="Cuisine catalog the meal belongs to.")
    macros: MacroNutrients = Field(default_factory=MacroNutrients, description="Aggregate nutritional breakdown for the entire meal.")
    foods_struct: List[PlanFoodItem] = Field(default_factory=list, description="List of individual food items composing this meal.")
    scale: Optional[ScaleInfo] = Field(None, description="Scaling metadata applied to this meal.")


class MacroTotals(BaseModel):
    """Aggregate macro nutrient totals (per-day or across all days)."""
    caloriesKcal: float = Field(0.0, description="Total energy in kilocalories.")
    proteinG: float = Field(0.0, description="Total protein in grams.")
    carbsG: float = Field(0.0, description="Total carbohydrates in grams.")
    fatG: float = Field(0.0, description="Total fat in grams.")
    fiberG: float = Field(0.0, description="Total dietary fiber in grams.")


class BuildPlanResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "days": 1,
                "targets": {
                    "age": 28, "heightCm": 175.0, "weightKg": 75.0, "targetBmi": 22, "targetWeightKg": 67.3,
                    "weightDeltaKg": -7.7, "bmi": 24.5, "bmiCategory": "Overweight", "bmr": 1680, "tdee": 2604,
                    "maintenanceCalories": 2604, "dailyCalories": 2104, "proteinG": 131, "carbsG": 236, "fatG": 70,
                    "fatGMin": 46, "fatGMax": 81, "carbsGMin": 210, "carbsGMax": 263, "fiberG": 29, "fiberGRaw": 29,
                    "fiberGMinimum": 25, "waterL": 2.4, "waterLMin": 2.25, "waterLMax": 2.62, "activityLevelNormalized": "moderate"
                },
                "mealTimes": ["breakfast", "lunch", "dinner"],
                "plan": {
                    "breakfast": {
                        "Meal_ID": "meal_101",
                        "name": "Scaled Oatmeal",
                        "macros": {"caloriesKcal": 350.0, "proteinG": 12.0, "carbsG": 60.0, "fatG": 5.0, "fiberG": 8.0},
                        "foods_struct": []
                    }
                },
                "totals": {
                    "caloriesKcal": 350.0,
                    "proteinG": 12.0,
                    "carbsG": 60.0,
                    "fatG": 5.0,
                    "fiberG": 8.0
                }
            }
        }
    )
    days: int = Field(..., description="Number of days in the generated plan.", json_schema_extra={"example": 1})
    targets: DailyTargetsResponse = Field(..., description="The calculated daily target profile.")
    mealTimes: List[str] = Field(..., description="List of meal times included in the plan.", json_schema_extra={"example": ["breakfast", "lunch", "dinner"]})
    plan: Optional[Dict[str, PlanMealItem]] = Field(default=None, description="The compiled plan payload for a single day plan. Keys are meal session codes.")
    totals: Optional[MacroTotals] = Field(default=None, description="Total nutrients for a single day plan.")
    plans: Optional[List[Dict[str, PlanMealItem]]] = Field(default=None, description="List of day plan objects for a multi-day plan. Each item is keyed by meal session code.")
    totalsByDay: Optional[List[MacroTotals]] = Field(default=None, description="Nutrient totals for each day in a multi-day plan.")
    totalsAll: Optional[MacroTotals] = Field(default=None, description="Aggregate nutrient totals across all days in a multi-day plan.")


class MealSwapOptionsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "targetMacros": {
                    "caloriesKcal": 500.0,
                    "proteinG": 30.0,
                    "carbsG": 60.0,
                    "fatG": 15.0,
                    "fiberG": 8.0
                },
                "currentMeal": {
                    "mealInstanceId": "02627b12-8428-4b13-9be2-4811d4c95f81",
                    "mealId": "meal_123",
                    "name":"Biriyani",
                    "mealTime": "lunch",
                    "macros": {
                    "caloriesKcal": 500.0,
                    "proteinG": 30.0,
                    "carbsG": 60.0,
                    "fatG": 15.0,
                    "fiberG": 8.0
                },

                },
                "options": [
                    {
                        "mealId": "meal_777",
                        "name": "Grilled Chicken Rice Bowl",
                        "macros": {"caloriesKcal": 490.0, "proteinG": 32.0, "carbsG": 58.0, "fatG": 14.0, "fiberG": 6.0},
                        "score": 0.0,
                        "scaleFactorRequested": 1.0,
                        "scaleFactorApplied": 1.0
                    }
                ]
            }
        }
    )
    targetMacros: Dict[str, float] = Field(..., description="Nutritional macro targets used as standard to filter alternative options.")
    currentMeal: Optional[Dict[str, Any]] = Field(default=None, description="Details of the current meal being swapped.")
    options: List[Dict[str, Any]] = Field(..., description="List of matching meal items available for swap.")


class SwapMealApplyResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "meal": {
                    "id": "meal_777",
                    "name": "Grilled Chicken Rice Bowl",
                    "macros": {"caloriesKcal": 490.0, "proteinG": 32.0, "carbsG": 58.0, "fatG": 14.0, "fiberG": 6.0}
                }
            }
        }
    )
    meal: Dict[str, Any] = Field(..., description="The newly updated meal payload with scaled/recalculated macros.")
    version: Optional[int] = Field(None, description="The new plan version after this swap was applied. Use this for the next swap call.")



class FoodSwapOption(BaseModel):
    sourceFoodIndex: int
    sourceFoodName: str
    score: float
    nutritionError: float
    fuzzySimilarity: float
    replacement: Dict[str, Any]
    replacementMealId: str
    projectedMealMacros: MacroTotals
    projectedNutritiveValues: str
    model_config = ConfigDict(extra='allow')

class SwapFoodOptionsResponse(BaseModel):
    model_config = ConfigDict(extra='allow')
    matchedSource: Dict[str, Any] = Field(..., description="Nutritional properties of the original food item being swapped out.")
    options: List[FoodSwapOption] = Field(..., description="List of matching swap options indicating ratio and nutrient impact.")


class SwapIngredientOptionsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "matchedSource": {"ingredient": "Mustard oil", "properties": {}},
                "options": [
                    {
                        "target_ingredient": "Olive oil",
                        "ratio": 1.0,
                        "properties": {}
                    }
                ]
            }
        }
    )
    matchedSource: Dict[str, Any] = Field(..., description="Original ingredient metadata details.")
    options: List[Dict[str, Any]] = Field(..., description="Suggested replacement options.")


class SubstitutesResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "choices": [{"name": "Milk", "substitutes": ["Almond milk", "Soy milk"]}],
                "substitutesByKey": {"Milk": [{"name": "Almond milk", "ratio": 1.0}]}
            }
        }
    )
    choices: List[Dict[str, Any]] = Field(..., description="Recognized ingredients from query and their substitute summaries.")
    substitutesByKey: Dict[str, List[Dict[str, Any]]] = Field(..., description="Detailed replacement ratio metrics indexed by ingredient name.")


class HealthResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ok": True
            }
        }
    )
    ok: bool = Field(..., description="Liveness check indicator. Returns True if server is healthy.", json_schema_extra={"example": True})


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Standardized error classification code.", json_schema_extra={"example": "VALIDATION_ERROR"})
    message: str = Field(..., description="Readable error description text.", json_schema_extra={"example": "Invalid request parameters."})
    details: Optional[Any] = Field(None, description="Context-specific details (like Pydantic validation failures).")


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request parameters.",
                    "details": None
                }
            }
        }
    )
    success: bool = Field(False, description="Always False to represent a failed request.", json_schema_extra={"example": False})
    error: ErrorDetail = Field(..., description="Inner details of the error.")


class DashboardRequest(BaseModel):
    profile: StudioProfile


class DashboardDailyTargets(BaseModel):
    caloriesKcal: int
    proteinG: int
    carbsG: int
    fatG: int
    fiberG: int


class DashboardHealthMetrics(BaseModel):
    bmi: float
    bmiCategory: str
    targetWeightKg: float
    weightKg: float
    weightDeltaKg: float


class DashboardHydration(BaseModel):
    targetWaterL: float
    consumedWaterMl: int
    completionPercentage: int


class DashboardEnergySummary(BaseModel):
    targetCalories: int
    consumedCalories: int
    remainingCalories: int


class DashboardMeal(BaseModel):
    mealId: str
    name: str
    imageUrl: str
    session: str
    scheduledTime: str
    macros: Dict[str, float]
    consumed: bool = False

class DashboardFood(BaseModel):
    id: str
    name: str
    servingSize: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None

class DashboardMealDetailed(BaseModel):
    mealId: str
    name: str
    imageUrl: str
    session: str
    scheduledTime: str
    macros: Dict[str, float]
    consumed: bool = False
    foods: List[DashboardFood] = []
    ingredients: Optional[str] = None

class DashboardDay(BaseModel):
    dayNumber: int
    planDayId: Optional[str] = None
    totals: Dict[str, float]
    meals: List[DashboardMealDetailed]

class DashboardWeek(BaseModel):
    weekNumber: int
    days: List[DashboardDay]


class DashboardResponse(BaseModel):
    activePlan: bool
    status: str = "active"
    planId: Optional[str] = None
    version: int = 1
    dailyTargets: DashboardDailyTargets
    healthMetrics: DashboardHealthMetrics
    hydration: DashboardHydration
    energySummary: Optional[DashboardEnergySummary] = None
    todayMeals: List[DashboardMeal]
    weeks: List[DashboardWeek] = []
    goal: str
    activityLevel: str
    cuisineType: str
    currentDay: int
    totalDays: int
    planDayId: Optional[str] = None


class ConsumeMealRequest(BaseModel):
    mealId: str
    mealDate: str  # YYYY-MM-DD format string
    consumed: bool


class ConsumeMealResponse(BaseModel):
    success: bool
    consumed: bool


class LogHydrationRequest(BaseModel):
    planDayId: str
    waterMl: int


class LogHydrationResponse(BaseModel):
    success: bool
    consumedWaterMl: int
    completionPercentage: int


class CuisineSchema(BaseModel):
    id: str = Field(..., description="The unique code of the cuisine")
    name: str = Field(..., description="The name of the cuisine in English")

    model_config = ConfigDict(from_attributes=True)


class CuisineListResponse(BaseModel):
    targetMacros: Dict[str, float] = Field(..., description="Nutritional macro targets used as standard to filter alternative options.")
    options: List[Dict[str, Any]] = Field(..., description="List of matching meal items available for swap.")




class SwapIngredientOptionsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "matchedSource": {"ingredient": "Mustard oil", "properties": {}},
                "options": [
                    {
                        "target_ingredient": "Olive oil",
                        "ratio": 1.0,
                        "properties": {}
                    }
                ]
            }
        }
    )
    matchedSource: Dict[str, Any] = Field(..., description="Original ingredient metadata details.")
    options: List[Dict[str, Any]] = Field(..., description="Suggested replacement options.")


class SubstitutesResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "choices": [{"name": "Milk", "substitutes": ["Almond milk", "Soy milk"]}],
                "substitutesByKey": {"Milk": [{"name": "Almond milk", "ratio": 1.0}]}
            }
        }
    )
    choices: List[Dict[str, Any]] = Field(..., description="Recognized ingredients from query and their substitute summaries.")
    substitutesByKey: Dict[str, List[Dict[str, Any]]] = Field(..., description="Detailed replacement ratio metrics indexed by ingredient name.")


class HealthResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ok": True
            }
        }
    )
    ok: bool = Field(..., description="Liveness check indicator. Returns True if server is healthy.", json_schema_extra={"example": True})


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Standardized error classification code.", json_schema_extra={"example": "VALIDATION_ERROR"})
    message: str = Field(..., description="Readable error description text.", json_schema_extra={"example": "Invalid request parameters."})
    details: Optional[Any] = Field(None, description="Context-specific details (like Pydantic validation failures).")


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request parameters.",
                    "details": None
                }
            }
        }
    )
    success: bool = Field(False, description="Always False to represent a failed request.", json_schema_extra={"example": False})
    error: ErrorDetail = Field(..., description="Inner details of the error.")


class DashboardRequest(BaseModel):
    profile: StudioProfile


class DashboardDailyTargets(BaseModel):
    caloriesKcal: int
    proteinG: int
    carbsG: int
    fatG: int
    fiberG: int


class DashboardHealthMetrics(BaseModel):
    bmi: float
    bmiCategory: str
    targetWeightKg: float
    weightKg: float
    weightDeltaKg: float


class DashboardHydration(BaseModel):
    targetWaterL: float
    consumedWaterMl: int
    completionPercentage: int


class DashboardEnergySummary(BaseModel):
    targetCalories: int
    consumedCalories: int
    remainingCalories: int


class DashboardMeal(BaseModel):
    mealId: str
    name: str
    imageUrl: str
    session: str
    scheduledTime: str
    macros: Dict[str, float]
    consumed: bool = False


class ConsumeMealRequest(BaseModel):
    mealId: str
    mealDate: str  # YYYY-MM-DD format string
    consumed: bool


class ConsumeMealResponse(BaseModel):
    success: bool
    consumed: bool


class LogHydrationRequest(BaseModel):
    planDayId: str
    waterMl: int


class LogHydrationResponse(BaseModel):
    success: bool
    consumedWaterMl: int
    completionPercentage: int


class CuisineSchema(BaseModel):
    id: str = Field(..., description="The unique code of the cuisine")
    name: str = Field(..., description="The name of the cuisine in English")

    model_config = ConfigDict(from_attributes=True)


class CuisineListResponse(BaseModel):
    success: bool
    message: str
    data: List[CuisineSchema]


class CreateDraftRequest(BuildPlanRequest):
    """
    Inherits from BuildPlanRequest to reuse profile, days, mealTimes, poolsByTime.
    """
    pass


class PatchOperation(BaseModel):
    type: str = Field(..., description="Type of operation: 'move', 'swap', or 'food_swap'")
    mealInstanceId: str = Field(..., description="UUID of the meal instance to modify")
    targetDayNumber: Optional[int] = Field(None, description="Required for 'move' operation")
    targetSession: Optional[str] = Field(None, description="Required for 'move' operation")
    replacementMealId: Optional[str] = Field(None, description="Required for 'swap' operation")
    customMealPayload: Optional[Dict[str, Any]] = Field(None, description="Required for 'food_swap' operation")
    foodInstanceIds: Optional[List[str]] = Field(None, description="Required for 'food_swap' operation to track existing DietPlanMealFood IDs")


class PatchPlanRequest(BaseModel):
    version: int = Field(..., description="Optimistic concurrency control version number")
    operations: List[PatchOperation] = Field(..., description="List of mutation operations to apply atomically")


class ActivatePlanRequest(BaseModel):
    version: int = Field(..., description="Optimistic concurrency control version number")


class ActivatePlanResponse(BaseModel):
    success: bool
    status: str


class StoredPlanTargets(BaseModel):
    """Simplified daily targets stored in the database (subset of DailyTargetsResponse)."""
    dailyCalories: float = Field(0.0, description="Target daily calorie intake in kcal.")
    proteinG: float = Field(0.0, description="Target protein in grams.")
    carbsG: float = Field(0.0, description="Target carbohydrates in grams.")
    fatG: float = Field(0.0, description="Target fat in grams.")
    fiberG: float = Field(0.0, description="Target fiber in grams.")
    waterL: float = Field(0.0, description="Target water intake in liters.")


class ActiveMealItem(BaseModel):
    mealId: str
    name: str
    imageUrl: str = ""
    session: str
    scheduledTime: str
    macros: MacroTotals
    foods: List[Dict[str, Any]]
    completed: bool = False
    is_food_swappable: bool = True
    
class ActiveDayPlan(BaseModel):
    dayNumber: int
    planDayId: Optional[str] = None
    totals: MacroTotals
    meals: List[ActiveMealItem]

class ActiveWeek(BaseModel):
    weekNumber: int
    days: List[ActiveDayPlan]

class ActivePlanResponse(BaseModel):
    planId: str
    version: int
    status: str
    targets: Dict[str, Any]
    totalsAll: MacroTotals
    weeks: List[ActiveWeek]

class DraftMealItem(BaseModel):
    id: str = Field(alias="Meal_ID")
    name: str = ""
    imageUrl: str = ""
    session: str = ""
    scheduledTime: str = ""
    is_food_swappable: bool = True
    macros: MacroTotals
    model_config = ConfigDict(extra='allow', populate_by_name=True)

class DraftDayPlan(BaseModel):
    dayNumber: int
    planDayId: Optional[str] = None
    totals: MacroTotals
    meals: List[DraftMealItem] = []
    model_config = ConfigDict(extra='allow')

class DraftWeek(BaseModel):
    weekNumber: int
    days: List[DraftDayPlan]

class DraftPlanResponse(BaseModel):
    planId: str
    version: int
    status: str
    targets: Dict[str, Any]
    totalsAll: MacroTotals
    weeks: List[DraftWeek]

class CreateDraftResponse(BaseModel):
    planId: str = Field(..., description="The unique ID of the draft plan")
    version: int = Field(..., description="The version number of the draft plan")
    status: str = Field(..., description="The status of the plan (should be 'draft')")

    
class RecipeNutritionResponse(BaseModel):
    calories: int
    protein: float
    carbs: float
    fat: float
    fiber: float

class RecipeIngredientResponse(BaseModel):
    ingredientId: str
    ingredientName: str
    quantity: float
    unit: str

class RecipePreparationResponse(BaseModel):
    prepTime: int = 0
    cookTime: int = 0
    totalTime: int = 0
    instructions: List[str] = []

class RecipePersonalizationResponse(BaseModel):
    whyThisMeal: str = ""
    nutritionNotes: str = ""
    recommendationReason: str = ""

class RecipePermissionsResponse(BaseModel):
    canSwap: bool
    canRearrange: bool
    canCustomize: bool

class RecipeDetailResponse(BaseModel):
    mealInstanceId: str
    mealId: str
    mealName: str
    image: Optional[str] = None
    mealTime: str
    dayNumber: int
    servingSize: str = "1 serving"
    scaleFactor: float = 1.0

    nutrition: RecipeNutritionResponse
    ingredients: List[RecipeIngredientResponse]
    preparation: RecipePreparationResponse
    personalization: RecipePersonalizationResponse
    permissions: RecipePermissionsResponse

class CreateHealthProfileRequest(BaseModel):
    activityLevel: str = Field(..., description="Daily physical activity level (e.g., 'moderate').")
    age: int = Field(..., description="Age in years.")
    gender: str = Field(..., description="Gender (male, female).")
    heightCm: float = Field(..., description="Height in centimeters.")
    weightKg: float = Field(..., description="Weight in kilograms.")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "activityLevel": "moderate",
                "age": 28,
                "gender": "male",
                "heightCm": 175.0,
                "weightKg": 75.0
            }
        }
    )

class UserHealthProfileResponse(BaseModel):
    
    target_weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    bmi_category: Optional[str] = None
    bmr_kcal: Optional[int] = None
    tdee_kcal: Optional[int] = None
    target_water_l: Optional[float] = None
    is_latest: bool
    
    model_config = ConfigDict(from_attributes=True)



class RecipeIngredient(BaseModel):
    name: str = Field(..., description="Name of the ingredient")
    quantity: float = Field(..., description="Scaled quantity of the ingredient")
    unit: str = Field(..., description="Measurement unit of the ingredient")


class FoodRecipeInfo(BaseModel):
    food_instance_id: str = Field(..., description="The planned meal food instance ID (UUID)")
    food_id: Optional[Union[int, str]] = Field(None, description="The ID of the catalog food item")
    food_name: str = Field(..., description="Name of the component food")
    quantity: float = Field(..., description="Scaled quantity of the component food")
    unit: str = Field(..., description="Measurement unit of the food item")


class RecipeDetailsResponse(BaseModel):
    mealInstanceId: str = Field(..., description="The planned meal instance ID (UUID)")
    meal_id: Optional[Union[int, str]] = Field(None, description="The ID of the catalog meal item")
    is_food_swappable : bool = Field(..., description="Whether the food in the meal can be swapped")
    recipe_name: str = Field(..., description="The recipe/meal name")
    description: Optional[str] = Field(None, description="Detailed explanation ('Why this for you')")
    imageUrl: Optional[str] = Field(None, description="Image URL of the recipe/meal")
    image_ID: Optional[str] = Field(None, description="Image ID / URL of the recipe/meal")
    preparation_time : Optional[str] = Field(None, description="Preparation of the recipe/meal")
    macros: Dict[str, float] = Field(..., description="Scaled total macros for the planned meal")
    preparation: Optional[str] = Field(None, description="Preparation steps for the entire recipe")
    ingredients: List[RecipeIngredient] = Field(default_factory=list, description="List of all ingredients for the entire meal")
    foods_struct: List[FoodRecipeInfo] = Field(default_factory=list, description="Component foods list")
    total_quantity: Optional[float] = Field(None, description="Sum of all scaled food quantities.")
    total_quantity_unit: Optional[str] = Field("g", description="Unit for the total quantity.")
