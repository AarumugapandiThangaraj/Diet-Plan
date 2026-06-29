from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Float, Integer, ForeignKey, CheckConstraint, Date, Numeric, SmallInteger, UniqueConstraint, Text, text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID
import uuid
from database.base import Base, TimestampMixin

class DietPlan(Base, TimestampMixin):
    __tablename__ = "diet_plans"
    __table_args__ = (
        Index("idx_dp_user_active", "user_id", unique=True, postgresql_where=text("status = 'active'")), # Partial index in SQL
        CheckConstraint("days BETWEEN 1 AND 90", name="chk_days"),
        CheckConstraint("status IN ('draft','active','completed','archived','cancelled')", name="chk_status"),
        {"schema": "Twellr_Nutri"}
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    health_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("Twellr_Nutri.user_health_profiles.id", ondelete="SET NULL"), nullable=True)
    
    days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="'draft'")
    
    target_calories_kcal: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_protein_g: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    target_protein_g_min: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    target_protein_g_max: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    target_carbs_g: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    target_carbs_g_min: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    target_carbs_g_max: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    target_fat_g: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    target_fat_g_min: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    target_fat_g_max: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    target_fiber_g: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    target_fiber_g_min: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    target_water_l: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    target_water_l_min: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    target_water_l_max: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    
    bmi_snapshot: Mapped[Optional[float]] = mapped_column(Numeric(4, 1), nullable=True)
    bmi_category_snapshot: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    bmr_kcal_snapshot: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tdee_kcal_snapshot: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    activity_level_snapshot: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    
    totals_calories_kcal: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    totals_protein_g: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    totals_carbs_g: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    totals_fat_g: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    totals_fiber_g: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    
    starts_on: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    ends_on: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    
    archived_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    days_rel: Mapped[list["DietPlanDay"]] = relationship("DietPlanDay", back_populates="plan", cascade="all, delete-orphan")

class DietPlanDay(Base, TimestampMixin):
    __tablename__ = "diet_plan_days"
    __table_args__ = (
        UniqueConstraint("plan_id", "day_number", name="uq_dpd_plan_day"),
        CheckConstraint("day_number BETWEEN 1 AND 90", name="chk_day_number"),
        {"schema": "Twellr_Nutri"}
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Twellr_Nutri.diet_plans.id", ondelete="CASCADE"), nullable=False)
    day_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    plan_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    
    calories_kcal: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    protein_g: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    carbs_g: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    fat_g: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    fiber_g: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    
    plan: Mapped["DietPlan"] = relationship("DietPlan", back_populates="days_rel")
    meals_rel: Mapped[list["DietPlanMeal"]] = relationship("DietPlanMeal", back_populates="day", cascade="all, delete-orphan")
    hydration_logs_rel: Mapped[list["DietPlanDayHydrationLog"]] = relationship("DietPlanDayHydrationLog", back_populates="plan_day", cascade="all, delete-orphan")

class DietPlanMeal(Base, TimestampMixin):
    __tablename__ = "diet_plan_meals"
    __table_args__ = (
        UniqueConstraint("plan_day_id", "meal_session_id", name="uq_dpm_day_session"),
        {"schema": "Twellr_Nutri"}
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_day_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Twellr_Nutri.diet_plan_days.id", ondelete="CASCADE"), nullable=False)
    meal_session_id: Mapped[int] = mapped_column(ForeignKey("Twellr_Nutri.meal_sessions.id", ondelete="RESTRICT"), nullable=False)
    meal_id: Mapped[Optional[int]] = mapped_column(ForeignKey("Twellr_Nutri.meals.id", ondelete="SET NULL"), nullable=True)
    
    calories_kcal: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    protein_g: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    carbs_g: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    fat_g: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    fiber_g: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    
    scale_applied: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    
    day: Mapped["DietPlanDay"] = relationship("DietPlanDay", back_populates="meals_rel")
    meal_foods_rel: Mapped[list["DietPlanMealFood"]] = relationship("DietPlanMealFood", back_populates="meal", cascade="all, delete-orphan")
    consumptions_rel: Mapped[list["DietPlanMealConsumption"]] = relationship("DietPlanMealConsumption", back_populates="plan_meal", cascade="all, delete-orphan")
    meal: Mapped["Meal"] = relationship("Meal")

class DietPlanMealFood(Base, TimestampMixin):
    __tablename__ = "diet_plan_meal_foods"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="chk_quantity"),
        {"schema": "Twellr_Nutri"}
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_meal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Twellr_Nutri.diet_plan_meals.id", ondelete="CASCADE"), nullable=False)
    food_id: Mapped[Optional[int]] = mapped_column(ForeignKey("Twellr_Nutri.foods.id", ondelete="SET NULL"), nullable=True)
    
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    
    calories_kcal: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    protein_g: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    carbs_g: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    fat_g: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    fiber_g: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    
    supports: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    supports_normalized: Mapped[list] = mapped_column(ARRAY(String), nullable=False, server_default="{}")
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    
    meal: Mapped["DietPlanMeal"] = relationship("DietPlanMeal", back_populates="meal_foods_rel")
    ingredients_rel: Mapped[list["DietPlanMealFoodIngredient"]] = relationship("DietPlanMealFoodIngredient", back_populates="meal_food", cascade="all, delete-orphan")
    food: Mapped["Food"] = relationship("Food")

class DietPlanMealFoodIngredient(Base):
    __tablename__ = "diet_plan_meal_food_ingredients"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="chk_quantity"),
        {"schema": "Twellr_Nutri"}
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_meal_food_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Twellr_Nutri.diet_plan_meal_foods.id", ondelete="CASCADE"), nullable=False)
    ingredient_id: Mapped[Optional[int]] = mapped_column(ForeignKey("Twellr_Nutri.ingredients_master.id", ondelete="SET NULL"), nullable=True)
    
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    
    calories_kcal: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    protein_g: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    carbs_g: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    fat_g: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    fiber_g: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
    
    meal_food: Mapped["DietPlanMealFood"] = relationship("DietPlanMealFood", back_populates="ingredients_rel")
    ingredient: Mapped["MasterIngredient"] = relationship("MasterIngredient")

class DietPlanMealConsumption(Base, TimestampMixin):
    __tablename__ = "diet_plan_meal_consumption"
    __table_args__ = (
        UniqueConstraint("user_id", "plan_meal_id", name="uq_dpmc_plan_meal"),
        CheckConstraint("state IN ('eaten','partial','skipped','planned')", name="chk_state"),
        CheckConstraint("portion_factor BETWEEN 0.0 AND 5.0", name="chk_portion_factor"),
        {"schema": "Twellr_Nutri"}
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    plan_meal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Twellr_Nutri.diet_plan_meals.id", ondelete="CASCADE"), nullable=False)
    
    state: Mapped[str] = mapped_column(String(20), nullable=False, server_default="'eaten'")
    portion_factor: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False, server_default="1.0")
    consumed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_date: Mapped[Date] = mapped_column(Date, nullable=False, server_default=text("CURRENT_DATE"))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    plan_meal: Mapped["DietPlanMeal"] = relationship("DietPlanMeal", back_populates="consumptions_rel")

class DietPlanDayHydrationLog(Base):
    __tablename__ = "diet_plan_day_hydration_log"
    __table_args__ = (
        CheckConstraint("glasses BETWEEN 1 AND 20", name="chk_glasses"),
        CheckConstraint("volume_ml IS NULL OR volume_ml BETWEEN 1 AND 5000", name="chk_volume"),
        CheckConstraint("source IN ('manual','imported','wearable')", name="chk_source"),
        {"schema": "Twellr_Nutri"}
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    plan_day_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Twellr_Nutri.diet_plan_days.id", ondelete="CASCADE"), nullable=False)
    
    logged_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
    glasses: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="1")
    volume_ml: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, server_default="'manual'")

    plan_day: Mapped["DietPlanDay"] = relationship("DietPlanDay", back_populates="hydration_logs_rel")

