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

class FoodRole(Base, TimestampMixin):
    __tablename__ = "food_roles"
    __table_args__ = {"schema": "Twellr_Nutri"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

class PrimaryGoal(Base, TimestampMixin):
    __tablename__ = "primary_goals"
    __table_args__ = {"schema": "Twellr_Nutri"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

class SecondaryGoal(Base, TimestampMixin):
    __tablename__ = "secondary_goals"
    __table_args__ = {"schema": "Twellr_Nutri"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(150), nullable=False)
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

class Food(Base, TimestampMixin):
    __tablename__ = "foods"
    __table_args__ = {"schema": "Twellr_Nutri"}

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    cuisine_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("Twellr_Nutri.cuisines.id"), nullable=True)
    food_name: Mapped[str] = mapped_column(String(255), nullable=False)

    meal_foods = relationship("MealFood", back_populates="food")

class Meal(Base, TimestampMixin):
    __tablename__ = "meals"
    __table_args__ = {"schema": "Twellr_Nutri"}

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    cuisine_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("Twellr_Nutri.cuisines.id"), nullable=True)
    session: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    recipe_name: Mapped[str] = mapped_column(String(255), nullable=False)
    time: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    allergens: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    preparation_steps: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    image: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # Persisted nutrition macros
    calories_kcal: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    carbohydrates_g: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    protein_g: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    fat_g: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    dietary_fiber_g: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")

    cuisine = relationship("Cuisine")
    meal_foods = relationship("MealFood", back_populates="meal")
    meal_ingredients = relationship("MealIngredient", back_populates="meal")
    primary_goals = relationship("MealPrimaryGoal", back_populates="meal")
    secondary_goals = relationship("MealSecondaryGoal", back_populates="meal")

    @property
    def primary_goal_ids(self):
        return [g.primary_goal_id for g in self.primary_goals]

    @property
    def secondary_goal_ids(self):
        return [g.secondary_goal_id for g in self.secondary_goals]

class MealFood(Base, TimestampMixin):
    __tablename__ = "meal_foods"
    __table_args__ = {"schema": "Twellr_Nutri"}

    meal_id: Mapped[str] = mapped_column(ForeignKey("Twellr_Nutri.meals.id", ondelete="CASCADE"), primary_key=True)
    food_id: Mapped[str] = mapped_column(ForeignKey("Twellr_Nutri.foods.id", ondelete="RESTRICT"), primary_key=True)
    serving_size: Mapped[str] = mapped_column(String(100), nullable=False)

    meal = relationship("Meal", back_populates="meal_foods")
    food = relationship("Food", back_populates="meal_foods")

class MealIngredient(Base, TimestampMixin):
    __tablename__ = "meal_ingredients"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="chk_meal_ingredient_quantity"),
        {"schema": "Twellr_Nutri"}
    )

    meal_id: Mapped[str] = mapped_column(ForeignKey("Twellr_Nutri.meals.id", ondelete="CASCADE"), primary_key=True)
    ingredient_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=True)

    meal = relationship("Meal", back_populates="meal_ingredients")

class MealPrimaryGoal(Base, TimestampMixin):
    __tablename__ = "meal_primary_goals"
    __table_args__ = {"schema": "Twellr_Nutri"}

    meal_id: Mapped[str] = mapped_column(ForeignKey("Twellr_Nutri.meals.id", ondelete="CASCADE"), primary_key=True)
    primary_goal_id: Mapped[int] = mapped_column(ForeignKey("Twellr_Nutri.primary_goals.id", ondelete="CASCADE"), primary_key=True)

    meal = relationship("Meal", back_populates="primary_goals")
    primary_goal = relationship("PrimaryGoal")

class MealSecondaryGoal(Base, TimestampMixin):
    __tablename__ = "meal_secondary_goals"
    __table_args__ = {"schema": "Twellr_Nutri"}

    meal_id: Mapped[str] = mapped_column(ForeignKey("Twellr_Nutri.meals.id", ondelete="CASCADE"), primary_key=True)
    secondary_goal_id: Mapped[int] = mapped_column(ForeignKey("Twellr_Nutri.secondary_goals.id", ondelete="CASCADE"), primary_key=True)

    meal = relationship("Meal", back_populates="secondary_goals")
    secondary_goal = relationship("SecondaryGoal")

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
