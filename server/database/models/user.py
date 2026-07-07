from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Float, Integer, JSON, ForeignKey, CheckConstraint, Text, UniqueConstraint, Date, Numeric, SmallInteger, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID
import uuid
from database.base import Base, TimestampMixin

class UserHealthProfile(Base, TimestampMixin):
    __tablename__ = "user_health_profiles"
    __table_args__ = (
        Index("idx_uhp_latest", "user_id", unique=True, postgresql_where=text("is_latest = true")),
        CheckConstraint("age IS NULL OR age BETWEEN 1 AND 120", name="chk_age"),
        CheckConstraint("gender IS NULL OR gender IN ('male','female','non_binary','prefer_not_to_say')", name="chk_gender"),
        CheckConstraint("height_cm IS NULL OR height_cm BETWEEN 50 AND 260", name="chk_height"),
        CheckConstraint("weight_kg IS NULL OR weight_kg BETWEEN 10 AND 400", name="chk_weight"),
        CheckConstraint("activity_level IS NULL OR activity_level IN ('sedentary','lightly_active','moderately_active','very_active','extra_active')", name="chk_activity"),
        {"schema": "Twellr_Nutri"}
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False) # Cross-schema FK to wellness_platform.users not strictly enforced in SQLAlchemy here unless both are mapped.
    legacy_user_identifier: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    age: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    height_cm: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    target_weight_kg: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    bmi: Mapped[Optional[float]] = mapped_column(Numeric(4, 1), nullable=True)
    bmi_category: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    
    activity_level: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    bmr_kcal: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tdee_kcal: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_water_l: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    
    allergies: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    allergies_normalized: Mapped[list] = mapped_column(ARRAY(String), nullable=False, server_default="{}")
    
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

class UserGoal(Base, TimestampMixin):
    __tablename__ = "user_goals"
    __table_args__ = (
        UniqueConstraint("user_id", "primary_goal_id", name="uq_ug_user_primary"),
        UniqueConstraint("user_id", "secondary_goal_id", name="uq_ug_user_secondary"),
        CheckConstraint("goal_tier IN ('primary','secondary')", name="chk_goal_tier"),
        CheckConstraint(
            "(goal_tier = 'primary' AND primary_goal_id IS NOT NULL AND secondary_goal_id IS NULL) OR "
            "(goal_tier = 'secondary' AND secondary_goal_id IS NOT NULL AND primary_goal_id IS NULL)", 
            name="chk_goal_tier_fks"
        ),
        {"schema": "Twellr_Nutri"}
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    primary_goal_id: Mapped[Optional[int]] = mapped_column(ForeignKey("Twellr_Nutri.primary_goals.id", ondelete="RESTRICT"), nullable=True)
    secondary_goal_id: Mapped[Optional[int]] = mapped_column(ForeignKey("Twellr_Nutri.secondary_goals.id", ondelete="RESTRICT"), nullable=True)
    goal_tier: Mapped[str] = mapped_column(String(20), nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

class UserWeightLog(Base, TimestampMixin):
    __tablename__ = "user_weight_logs"
    __table_args__ = (
        CheckConstraint("weight_kg BETWEEN 10 AND 400", name="chk_weight_log"),
        {"schema": "Twellr_Nutri"}
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    weight_kg: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    bmi: Mapped[Optional[float]] = mapped_column(Numeric(4, 1), nullable=True)
    bmi_category: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    bmr_kcal: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_weight_kg: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    water_l: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")

class UserDailyIntake(Base, TimestampMixin):
    __tablename__ = "user_daily_intake"
    __table_args__ = (
        UniqueConstraint("user_id", "intake_date", name="uq_udi_user_date"),
        {"schema": "Twellr_Nutri"}
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    intake_date: Mapped[Date] = mapped_column(Date, nullable=False)
    
    calories_consumed: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, server_default="0")
    protein_consumed_g: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, server_default="0")
    carbs_consumed_g: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, server_default="0")
    fat_consumed_g: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, server_default="0")
    fiber_consumed_g: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, server_default="0")
    
    calories_target: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    protein_target_g: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    carbs_target_g: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    fat_target_g: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    fiber_target_g: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)

