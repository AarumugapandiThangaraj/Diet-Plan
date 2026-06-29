from typing import Optional, List
from datetime import time
from sqlalchemy import BigInteger, String, Boolean, DateTime, Float, Integer, JSON, ForeignKey, CheckConstraint, Time, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from database.base import Base, TimestampMixin

class Cuisine(Base, TimestampMixin):
    __tablename__ = "cuisines"
    __table_args__ = {"schema": "Twellr_Nutri"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ar: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

class MealSession(Base, TimestampMixin):
    __tablename__ = "meal_sessions"
    __table_args__ = {"schema": "Twellr_Nutri"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(60), nullable=False)
    name_ar: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

class MasterIngredient(Base, TimestampMixin):
    __tablename__ = "ingredients_master"
    __table_args__ = {"schema": "Twellr_Nutri"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    default_unit: Mapped[str] = mapped_column(String(50), nullable=False)
    
    calories_kcal: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    protein_g: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    fat_g: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    fiber_g: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    
    micronutrients: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    benefits: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    caution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    deleted_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)

class Food(Base, TimestampMixin):
    __tablename__ = "foods"
    __table_args__ = (
        UniqueConstraint("cuisine_id", "client_food_id", name="uq_foods_cuisine_client"),
        CheckConstraint("min_quantity IS NULL OR max_quantity IS NULL OR min_quantity <= max_quantity", name="chk_foods_qty_bounds"),
        CheckConstraint("food_role IN ('base','side','snack','dessert','beverage','condiment','other')", name="chk_food_role"),
        CheckConstraint("prep_time_minutes IS NULL OR prep_time_minutes >= 0", name="chk_prep_time"),
        {"schema": "Twellr_Nutri"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cuisine_id: Mapped[int] = mapped_column(ForeignKey("Twellr_Nutri.cuisines.id", ondelete="RESTRICT"), nullable=False)
    client_food_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_ar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preparation_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preparation_ar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    food_role: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    prep_time_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    min_quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    
    diet_types: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    diet_types_normalized: Mapped[list] = mapped_column(ARRAY(String), nullable=False, server_default="{}")
    supports: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    supports_normalized: Mapped[list] = mapped_column(ARRAY(String), nullable=False, server_default="{}")
    image_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    deleted_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)

    food_ingredients = relationship("FoodIngredient", back_populates="food")

class FoodIngredient(Base, TimestampMixin):
    __tablename__ = "food_ingredients"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="chk_quantity"),
        {"schema": "Twellr_Nutri"}
    )

    food_id: Mapped[int] = mapped_column(ForeignKey("Twellr_Nutri.foods.id", ondelete="CASCADE"), primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("Twellr_Nutri.ingredients_master.id", ondelete="RESTRICT"), primary_key=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    food = relationship("Food", back_populates="food_ingredients")
    ingredient = relationship("MasterIngredient")

class Meal(Base, TimestampMixin):
    __tablename__ = "meals"
    __table_args__ = (
        UniqueConstraint("cuisine_id", "client_meal_id", name="uq_meals_cuisine_client"),
        {"schema": "Twellr_Nutri"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cuisine_id: Mapped[int] = mapped_column(ForeignKey("Twellr_Nutri.cuisines.id", ondelete="RESTRICT"), nullable=False)
    client_meal_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_ar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    meal_session_id: Mapped[int] = mapped_column(ForeignKey("Twellr_Nutri.meal_sessions.id", ondelete="RESTRICT"), nullable=False)
    
    goal: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    goal_normalized: Mapped[list] = mapped_column(ARRAY(String), nullable=False, server_default="{}")
    secondary_goal: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    secondary_goal_normalized: Mapped[list] = mapped_column(ARRAY(String), nullable=False, server_default="{}")
    
    diet_types: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    diet_types_normalized: Mapped[list] = mapped_column(ARRAY(String), nullable=False, server_default="{}")
    
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    deleted_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)

    meal_foods = relationship("MealFood", back_populates="meal")

class MealFood(Base, TimestampMixin):
    __tablename__ = "meal_foods"
    __table_args__ = {"schema": "Twellr_Nutri"}

    meal_id: Mapped[int] = mapped_column(ForeignKey("Twellr_Nutri.meals.id", ondelete="CASCADE"), primary_key=True)
    food_id: Mapped[int] = mapped_column(ForeignKey("Twellr_Nutri.foods.id", ondelete="RESTRICT"), primary_key=True)
    is_replaceable: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    meal = relationship("Meal", back_populates="meal_foods")
    food = relationship("Food")

class Substitute(Base, TimestampMixin):
    __tablename__ = "substitutes"
    __table_args__ = {"schema": "Twellr_Nutri"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    allergen_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    allergen_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(150), nullable=False)
    name_ar: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    substitutes: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
