from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class StudioProfile(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    age: int = Field(default=30)
    gender: str = Field(default="female")
    heightCm: float = Field(default=165.0)
    weightKg: float = Field(default=60.0)
    activityLevel: str = Field(default="sedentary")
    goal: str = Field(default="skin_repair")
    dietType: str = Field(default="non_veg")
    allergies: str = Field(default="")
    cuisineType: str = Field(default="north_indian")

    @field_validator("age", mode="before")
    @classmethod
    def parse_age(cls, v: Any) -> int:
        try:
            return int(float(str(v).strip()))
        except Exception:
            return 30

    @field_validator("heightCm", mode="before")
    @classmethod
    def parse_height(cls, v: Any) -> float:
        try:
            return float(str(v).strip())
        except Exception:
            return 165.0

    @field_validator("weightKg", mode="before")
    @classmethod
    def parse_weight(cls, v: Any) -> float:
        try:
            return float(str(v).strip())
        except Exception:
            return 60.0


class TargetsRequest(BaseModel):
    profile: StudioProfile


class RankRequest(BaseModel):
    profile: StudioProfile
    mealTimes: List[str] = Field(default_factory=list)
    limit: int = 180


class BuildPlanRequest(BaseModel):
    profile: StudioProfile
    days: int = Field(7, ge=1, le=21)
    mealTimes: List[str] = Field(default_factory=list)
    poolsByTime: Dict[str, List[str]] = Field(default_factory=dict)
    assignmentByTime: Dict[str, List[str]] = Field(default_factory=dict)


class SubstitutesRequest(BaseModel):
    ingredients: str = ""


class MealSwapOptionsRequest(BaseModel):
    profile: StudioProfile
    mealTime: str
    currentMealId: str
    targetMacros: Optional[Dict[str, Any]] = None
    excludeMealIds: List[str] = Field(default_factory=list)
    allowedMealIds: List[str] = Field(default_factory=list)
    topN: int = Field(5, ge=1, le=20)


class MealSwapApplyRequest(BaseModel):
    meal: Dict[str, Any]


class FoodSwapOptionsRequest(BaseModel):
    meal: Dict[str, Any]
    foodName: str
    topN: int = Field(5, ge=1, le=20)


class FoodSwapApplyRequest(BaseModel):
    meal: Dict[str, Any]
    option: Dict[str, Any]


class IngredientSwapOptionsRequest(BaseModel):
    meal: Dict[str, Any]
    ingredientQuery: str
    topN: int = Field(5, ge=1, le=20)


class IngredientSwapApplyRequest(BaseModel):
    meal: Dict[str, Any]
    option: Dict[str, Any]


class ChatMessage(BaseModel):
    role: str
    text: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = Field(default_factory=list)
    agentName: str = "NutriBot"
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    reply: str
    preferences: Optional[Dict[str, Any]] = None
    quickReplies: Optional[List[Dict[str, str]]] = None
    action: Optional[Dict[str, Any]] = None


# --- Response Models for Studio Endpoints ---

class StudioMetaResponse(BaseModel):
    mealTimes: List[str]
    mealsCount: int
    dataSource: str
    validCuisines: Dict[str, str]
    activeCuisine: str


class DailyTargetsResponse(BaseModel):
    age: int
    heightCm: float
    weightKg: float
    targetBmi: int
    targetWeightKg: float
    weightDeltaKg: float
    bmi: float
    bmiCategory: str
    bmr: int
    tdee: int
    maintenanceCalories: int
    dailyCalories: int
    proteinG: int
    carbsG: int
    fatG: int
    fatGMin: int
    fatGMax: int
    carbsGMin: int
    carbsGMax: int
    fiberG: int
    fiberGRaw: int
    fiberGMinimum: int
    waterL: float
    waterLMin: float
    waterLMax: float
    activityLevelNormalized: str


class RankResponse(BaseModel):
    targets: DailyTargetsResponse
    rankedByTime: Dict[str, List[Dict[str, Any]]]


class BuildPlanResponse(BaseModel):
    days: int
    targets: DailyTargetsResponse
    mealTimes: List[str]
    plan: Optional[Dict[str, Any]] = None
    totals: Optional[Dict[str, float]] = None
    plans: Optional[List[Dict[str, Any]]] = None
    totalsByDay: Optional[List[Dict[str, float]]] = None
    totalsAll: Optional[Dict[str, float]] = None


class MealSwapOptionsResponse(BaseModel):
    targetMacros: Dict[str, float]
    options: List[Dict[str, Any]]


class SwapMealApplyResponse(BaseModel):
    meal: Dict[str, Any]


class SwapFoodOptionsResponse(BaseModel):
    matchedSource: Dict[str, Any]
    options: List[Dict[str, Any]]


class SwapIngredientOptionsResponse(BaseModel):
    matchedSource: Dict[str, Any]
    options: List[Dict[str, Any]]


class SubstitutesResponse(BaseModel):
    choices: List[Dict[str, Any]]
    substitutesByKey: Dict[str, List[Dict[str, Any]]]
