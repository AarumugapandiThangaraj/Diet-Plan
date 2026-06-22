from sqlalchemy import BigInteger, Numeric, String, Boolean, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base, TimestampMixin

class FoodConcernTag(Base, TimestampMixin):
    __tablename__ = "food_concern_tags"
    __table_args__ = (
        UniqueConstraint("food_id", "concern_id", name="uq_fct_food_concern"),
        CheckConstraint("tag_weight BETWEEN 0.0 AND 1.0", name="chk_tag_weight"),
        CheckConstraint("source IN ('llm','manual','dietician','imported')", name="chk_source"),
        {"schema": "Twellr_Nutri"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    food_id: Mapped[int] = mapped_column(ForeignKey("Twellr_Nutri.foods.id", ondelete="CASCADE"), nullable=False)
    concern_id: Mapped[int] = mapped_column(BigInteger, nullable=False) # Maps to wellness_platform.concern_taxonomy
    tag_weight: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, server_default="1.0")
    source: Mapped[str] = mapped_column(String(30), nullable=False, server_default="'llm'")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

class MealConcernTag(Base, TimestampMixin):
    __tablename__ = "meal_concern_tags"
    __table_args__ = (
        UniqueConstraint("meal_id", "concern_id", name="uq_mct_meal_concern"),
        CheckConstraint("tag_weight BETWEEN 0.0 AND 1.0", name="chk_tag_weight_mct"),
        CheckConstraint("source IN ('llm','manual','dietician','imported')", name="chk_source_mct"),
        {"schema": "Twellr_Nutri"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    meal_id: Mapped[int] = mapped_column(ForeignKey("Twellr_Nutri.meals.id", ondelete="CASCADE"), nullable=False)
    concern_id: Mapped[int] = mapped_column(BigInteger, nullable=False) # Maps to wellness_platform.concern_taxonomy
    tag_weight: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, server_default="1.0")
    source: Mapped[str] = mapped_column(String(30), nullable=False, server_default="'llm'")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
