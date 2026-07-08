from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

class MacroStruct(BaseModel):
    caloriesKcal: float = 0.0
    proteinG: float = 0.0
    carbsG: float = 0.0
    fatG: float = 0.0
    fiberG: float = 0.0
    
    def scale(self, factor: float) -> "MacroStruct":
        return MacroStruct(
            caloriesKcal=self.caloriesKcal * factor,
            proteinG=self.proteinG * factor,
            carbsG=self.carbsG * factor,
            fatG=self.fatG * factor,
            fiberG=self.fiberG * factor
        )

class IngredientPayload(BaseModel):
    id: Optional[Any] = None
    name: Optional[str] = None
    quantity: float = 0.0
    unit: Optional[str] = None
    macros: MacroStruct = Field(default_factory=MacroStruct)
    caution: Optional[str] = None
    notes: Optional[str] = None
    swapable: bool = False
    
    # allow arbitrary extra fields like per100g or per_unit for legacy backward compatibility
    model_config = ConfigDict(extra="allow")

class FoodPayload(BaseModel):
    id: Optional[Any] = None
    name: Optional[str] = None
    quantity: float = 0.0
    unit: Optional[str] = None
    min_quantity: float = 0.0
    max_quantity: float = 0.0
    ingredients_struct: List[IngredientPayload] = Field(default_factory=list)
    macros: MacroStruct = Field(default_factory=MacroStruct)
    supports: List[str] = Field(default_factory=list)
    type: Optional[str] = None
    preparation: Optional[str] = None
    description: Optional[str] = None
    
    model_config = ConfigDict(extra="allow")
    
    def recalculate_macros(self):
        cal = prot = carb = fat = fib = 0.0
        for ing in self.ingredients_struct:
            cal += ing.macros.caloriesKcal
            prot += ing.macros.proteinG
            carb += ing.macros.carbsG
            fat += ing.macros.fatG
            fib += ing.macros.fiberG
        self.macros = MacroStruct(
            caloriesKcal=cal, proteinG=prot, carbsG=carb, fatG=fat, fiberG=fib
        )

class MealPayload(BaseModel):
    id: Optional[Any] = Field(default=None, alias="Meal_ID")
    meal_name: Optional[str] = None
    meal_time: Optional[str] = None
    cuisine_type: Optional[str] = None
    image_ID: Optional[str] = None
    macros: MacroStruct = Field(default_factory=MacroStruct, alias="_macros")
    foods_struct: List[FoodPayload] = Field(default_factory=list)
    
    model_config = ConfigDict(populate_by_name=True, extra="allow")
    
    def recalculate_macros(self):
        cal = prot = carb = fat = fib = 0.0
        for food in self.foods_struct:
            cal += food.macros.caloriesKcal
            prot += food.macros.proteinG
            carb += food.macros.carbsG
            fat += food.macros.fatG
            fib += food.macros.fiberG
        self.macros = MacroStruct(
            caloriesKcal=cal, proteinG=prot, carbsG=carb, fatG=fat, fiberG=fib
        )
