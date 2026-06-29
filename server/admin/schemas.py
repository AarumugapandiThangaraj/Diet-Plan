"""
Admin data entry schemas for CRUD operations
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator
from datetime import datetime, time


# Base model with ORM mode enabled for all schemas
class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def empty_strings_to_none(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {k: (None if v == "" else v) for k, v in data.items()}
        return data


# Cuisine Schemas
class CuisineCreate(ORMBaseModel):
    code: str = Field(..., description="Unique cuisine code (e.g., north_indian)")
    name_en: str = Field(..., description="English name")
    name_ar: Optional[str] = Field(None, description="Arabic name")
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)


class CuisineUpdate(ORMBaseModel):
    code: Optional[str] = None
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class CuisineResponse(CuisineCreate):
    id: int
    created_at: datetime
    updated_at: datetime


# Meal Session Schemas
class MealSessionCreate(ORMBaseModel):
    code: str = Field(..., description="Unique session code (e.g., breakfast)")
    name_en: str = Field(..., description="English name")
    name_ar: Optional[str] = Field(None, description="Arabic name")
    start_time: Optional[time] = Field(None, description="Start of slot time (HH:MM:SS)")
    end_time: Optional[time] = Field(None, description="End of slot time (HH:MM:SS)")
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)


class MealSessionUpdate(ORMBaseModel):
    code: Optional[str] = None
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class MealSessionResponse(MealSessionCreate):
    id: int
    created_at: datetime
    updated_at: datetime


# Ingredient Schemas
class MasterIngredientCreate(ORMBaseModel):
    name_en: str = Field(..., description="English name")
    name_ar: Optional[str] = Field(None, description="Arabic name")
    default_unit: str = Field(..., description="Default unit (g, ml, cup, etc.)")
    
    calories_kcal: float = Field(default=0.0)
    protein_g: float = Field(default=0.0)
    carbs_g: float = Field(default=0.0)
    fat_g: float = Field(default=0.0)
    fiber_g: float = Field(default=0.0)
    
    micronutrients: Optional[Dict[str, Any]] = Field(None, description="JSON: {vitamin: amount, ...}")
    benefits: Optional[Dict[str, Any]] = Field(None, description="JSON: {benefit: description, ...}")
    caution: Optional[str] = Field(None, description="Health warnings or allergies")
    notes: Optional[str] = Field(None, description="General notes")
    
    is_active: bool = Field(default=True)


class MasterIngredientUpdate(ORMBaseModel):
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    default_unit: Optional[str] = None
    calories_kcal: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    micronutrients: Optional[Dict[str, Any]] = None
    benefits: Optional[Dict[str, Any]] = None
    caution: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class MasterIngredientResponse(MasterIngredientCreate):
    id: int
    created_at: datetime
    updated_at: datetime


# Food Ingredient Schema
class FoodIngredientCreate(ORMBaseModel):
    ingredient_id: int
    quantity: float = Field(..., description="Quantity of ingredient")
    sort_order: int = Field(default=0)


class FoodIngredientUpdate(ORMBaseModel):
    quantity: Optional[float] = None
    sort_order: Optional[int] = None


class FoodIngredientResponse(FoodIngredientCreate):
    created_at: datetime
    updated_at: datetime


# Food Schemas
class FoodCreate(ORMBaseModel):
    cuisine_id: int
    client_food_id: str = Field(..., description="Client-specific food ID")
    name_en: str
    name_ar: Optional[str] = None
    description_en: Optional[str] = None
    description_ar: Optional[str] = None
    preparation_en: Optional[str] = None
    preparation_ar: Optional[str] = None
    notes: Optional[str] = None
    food_role: Optional[str] = Field(None, description="Role: base, side, snack, dessert, beverage, condiment, other")
    prep_time_minutes: Optional[int] = None
    
    quantity: float = Field(..., description="Default quantity")
    min_quantity: Optional[float] = None
    max_quantity: Optional[float] = None
    unit: str = Field(..., description="Unit of measurement")
    
    diet_types: Optional[Any] = None
    supports: Optional[Any] = None
    image_url: Optional[str] = None
    
    is_active: bool = Field(default=True)
    food_ingredients: List[FoodIngredientCreate] = Field(default_factory=list)


class FoodUpdate(ORMBaseModel):
    cuisine_id: Optional[int] = None
    client_food_id: Optional[str] = None
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    description_en: Optional[str] = None
    description_ar: Optional[str] = None
    preparation_en: Optional[str] = None
    preparation_ar: Optional[str] = None
    notes: Optional[str] = None
    food_role: Optional[str] = None
    prep_time_minutes: Optional[int] = None
    quantity: Optional[float] = None
    min_quantity: Optional[float] = None
    max_quantity: Optional[float] = None
    unit: Optional[str] = None
    diet_types: Optional[Any] = None
    supports: Optional[Any] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    food_ingredients: Optional[List[FoodIngredientCreate]] = None


class FoodResponse(FoodCreate):
    id: int
    created_at: datetime
    updated_at: datetime


# Meal Schemas
class MealFoodCreate(ORMBaseModel):
    food_id: int
    is_replaceable: bool = Field(default=False)
    sort_order: int = Field(default=0)


class MealFoodUpdate(ORMBaseModel):
    is_replaceable: Optional[bool] = None
    sort_order: Optional[int] = None


class MealFoodResponse(MealFoodCreate):
    created_at: datetime
    updated_at: datetime


class MealFoodWithFoodResponse(ORMBaseModel):
    """Meal-Food relationship with full Food details"""
    food_id: int
    is_replaceable: bool
    sort_order: int
    food: Optional[FoodResponse] = None
    created_at: datetime
    updated_at: datetime


class MealCreate(ORMBaseModel):
    cuisine_id: int
    client_meal_id: str = Field(..., description="Client-specific meal ID")
    name_en: str
    name_ar: Optional[str] = None
    description_en: Optional[str] = None
    description_ar: Optional[str] = None
    
    meal_session_id: int
    
    goal: Optional[Any] = None
    secondary_goal: Optional[Any] = None
    diet_types: Optional[Any] = None
    
    is_active: bool = Field(default=True)
    meal_foods: List[MealFoodCreate] = Field(default_factory=list)


class MealUpdate(ORMBaseModel):
    cuisine_id: Optional[int] = None
    client_meal_id: Optional[str] = None
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    description_en: Optional[str] = None
    description_ar: Optional[str] = None
    meal_session_id: Optional[int] = None
    goal: Optional[Any] = None
    secondary_goal: Optional[Any] = None
    diet_types: Optional[Any] = None
    is_active: Optional[bool] = None
    meal_foods: Optional[List[MealFoodCreate]] = None


class MealResponse(ORMBaseModel):
    """Meal response with full Food details"""
    id: int
    cuisine_id: int
    client_meal_id: str
    name_en: str
    name_ar: Optional[str]
    description_en: Optional[str]
    description_ar: Optional[str]
    meal_session_id: int
    goal: Optional[Any] = None
    secondary_goal: Optional[Any] = None
    diet_types: Optional[Any] = None
    is_active: bool
    meal_foods: List[MealFoodWithFoodResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# List responses
class CuisineListResponse(ORMBaseModel):
    total: int
    items: List[CuisineResponse]


class MealSessionListResponse(ORMBaseModel):
    total: int
    items: List[MealSessionResponse]


class MasterIngredientListResponse(ORMBaseModel):
    total: int
    items: List[MasterIngredientResponse]


class FoodListResponse(ORMBaseModel):
    total: int
    items: List[FoodResponse]


class MealListResponse(ORMBaseModel):
    total: int
    items: List[MealResponse]
