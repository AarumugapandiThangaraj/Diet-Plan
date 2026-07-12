from config.config import DATABASE_SCHEMA
from typing import Optional, List
from datetime import time
from sqlalchemy import BigInteger, String, Boolean, DateTime, Float, Integer, JSON, ForeignKey, CheckConstraint, Time, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from database.base import Base, TimestampMixin

class Cuisine(Base, TimestampMixin):
    __tablename__ = "nutri_cuisines"
    __table_args__ = {"schema": DATABASE_SCHEMA}

    id: Mapped[int] = mapped_column("cuisine_id", BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ar: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

# class FoodRole(Base, TimestampMixin):
#     __tablename__ = "food_roles"
#     __table_args__ = {"schema": DATABASE_SCHEMA}

#     id: Mapped[int] = mapped_column(Integer, primary_key=True)
#     code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
#     name_en: Mapped[str] = mapped_column(String(100), nullable=False)
#     is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

class PrimaryGoal(Base, TimestampMixin):
    __tablename__ = "nutri_primary_goals"
    __table_args__ = {"schema": DATABASE_SCHEMA}

    id: Mapped[int] = mapped_column("primary_goal_id", Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

class SecondaryGoal(Base, TimestampMixin):
    __tablename__ = "nutri_secondary_goals"
    __table_args__ = {"schema": DATABASE_SCHEMA}

    id: Mapped[int] = mapped_column("secondary_goal_id", Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

class MealSession(Base, TimestampMixin):
    __tablename__ = "nutri_meal_sessions"
    __table_args__ = {"schema": DATABASE_SCHEMA}

    id: Mapped[int] = mapped_column("meal_session_id", BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(60), nullable=False)
    name_ar: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

class Food(Base, TimestampMixin):
    __tablename__ = "nutri_foods"
    __table_args__ = {"schema": DATABASE_SCHEMA}

    id: Mapped[int] = mapped_column("food_id", BigInteger, primary_key=True)
    cuisine_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey(f"{DATABASE_SCHEMA}.nutri_cuisines.cuisine_id"), nullable=True)
    food_name: Mapped[str] = mapped_column("name_en", String(255), nullable=False)

    meal_foods = relationship("MealFood", back_populates="food")

class Meal(Base, TimestampMixin):
    __tablename__ = "nutri_meals"
    __table_args__ = {"schema": DATABASE_SCHEMA}

    id: Mapped[int] = mapped_column("meal_id", BigInteger, primary_key=True)
    cuisine_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey(f"{DATABASE_SCHEMA}.nutri_cuisines.cuisine_id"), nullable=True)
    meal_session_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey(f"{DATABASE_SCHEMA}.nutri_meal_sessions.meal_session_id"), nullable=True)
    session: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, deferred=True)
    recipe_name: Mapped[str] = mapped_column("name_en", String(255), nullable=False)
    time: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, deferred=True)
    description: Mapped[Optional[str]] = mapped_column("description_en", Text, nullable=True)
    
    allergens: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, deferred=True)
    preparation_steps: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, deferred=True)
    image: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True, deferred=True)

    # Persisted nutrition macros
    calories_kcal: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    carbohydrates_g: Mapped[float] = mapped_column("carbs_g", Float, nullable=False, server_default="0.0")
    protein_g: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    fat_g: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    dietary_fiber_g: Mapped[float] = mapped_column("fiber_g", Float, nullable=False, server_default="0.0")

    cuisine = relationship("Cuisine")
    meal_session = relationship("MealSession")
    meal_foods = relationship("MealFood", back_populates="meal")
    primary_goals = relationship("MealPrimaryGoal", back_populates="meal")
    secondary_goals = relationship("MealSecondaryGoal", back_populates="meal")
    meal_ingredients = relationship("MealIngredient", back_populates="meal")

    @property
    def primary_goal_ids(self):
        return [g.primary_goal_id for g in self.primary_goals]

    @property
    def secondary_goal_ids(self):
        return [g.secondary_goal_id for g in self.secondary_goals]

class MealFood(Base, TimestampMixin):
    __tablename__ = "nutri_meal_foods"
    __table_args__ = {"schema": DATABASE_SCHEMA}

    id: Mapped[int] = mapped_column("meal_food_id", BigInteger, primary_key=True)
    meal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(f"{DATABASE_SCHEMA}.nutri_meals.meal_id", ondelete="CASCADE"))
    food_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(f"{DATABASE_SCHEMA}.nutri_foods.food_id", ondelete="RESTRICT"))
    serving_size: Mapped[float] = mapped_column("quantity", Float, nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    meal = relationship("Meal", back_populates="meal_foods")
    food = relationship("Food", back_populates="meal_foods")

class MealIngredient(Base, TimestampMixin):
    __tablename__ = "nutri_meal_ingredients"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="chk_meal_ingredient_quantity"),
        {"schema": DATABASE_SCHEMA}
    )

    id: Mapped[int] = mapped_column("meal_ingredient_id", BigInteger, primary_key=True)
    meal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(f"{DATABASE_SCHEMA}.nutri_meals.meal_id", ondelete="CASCADE"))
    ingredient_name: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=True)

    meal = relationship("Meal", back_populates="meal_ingredients")

class MealPrimaryGoal(Base, TimestampMixin):
    __tablename__ = "nutri_meal_primary_goals"
    __table_args__ = {"schema": DATABASE_SCHEMA}

    id: Mapped[int] = mapped_column("meal_primary_goal_id", BigInteger, primary_key=True)
    meal_id: Mapped[int] = mapped_column(ForeignKey(f"{DATABASE_SCHEMA}.nutri_meals.meal_id", ondelete="CASCADE"))
    primary_goal_id: Mapped[int] = mapped_column(ForeignKey(f"{DATABASE_SCHEMA}.nutri_primary_goals.primary_goal_id", ondelete="CASCADE"))

    meal = relationship("Meal", back_populates="primary_goals")
    primary_goal = relationship("PrimaryGoal")

class MealSecondaryGoal(Base, TimestampMixin):
    __tablename__ = "nutri_meal_secondary_goals"
    __table_args__ = {"schema": DATABASE_SCHEMA}

    id: Mapped[int] = mapped_column("meal_secondary_goal_id", BigInteger, primary_key=True)
    meal_id: Mapped[int] = mapped_column(ForeignKey(f"{DATABASE_SCHEMA}.nutri_meals.meal_id", ondelete="CASCADE"))
    secondary_goal_id: Mapped[int] = mapped_column(ForeignKey(f"{DATABASE_SCHEMA}.nutri_secondary_goals.secondary_goal_id", ondelete="CASCADE"))

    meal = relationship("Meal", back_populates="secondary_goals")
    secondary_goal = relationship("SecondaryGoal")

# class Substitute(Base, TimestampMixin):
#     __tablename__ = "substitutes"
#     __table_args__ = {"schema": DATABASE_SCHEMA}

#     id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
#     allergen_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
#     allergen_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
#     name_en: Mapped[str] = mapped_column(String(150), nullable=False)
#     name_ar: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
#     substitutes: Mapped[dict] = mapped_column(JSONB, nullable=False)
#     is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
