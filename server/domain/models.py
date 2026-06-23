# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
from typing import Any, Dict, List

class Ingredient(BaseModel):
    id: str
    name: str
    default_unit: str
    base_macros: Dict[str, float]
    caution: str
    notes: str

class Food(BaseModel):
    id: str
    name: str
    quantity: float
    unit: str
    min_quantity: float
    max_quantity: float
    ingredients_struct: List[Dict[str, Any]]
    macros: Dict[str, float]
    supports: List[str]
    type: str
    preparation: str
    description: str

class Meal(BaseModel):
    Meal_ID: str = Field(alias="Meal_ID")
    meal_name: str
    goal: List[str]
    meal_time: str
    time: str
    ingredients: str
    ingredients_struct: List[Dict[str, Any]]
    foods_struct: List[Dict[str, Any]]
    method: str
    nutritive_values: str
    serving_size: str
    caution: str
    diet_type: str
    cuisine_type: str
    country: str
    image_ID: str = Field(alias="image_ID")
    description: str
    macros: Dict[str, float] = Field(alias="_macros")
