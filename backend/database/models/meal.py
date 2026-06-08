from sqlalchemy import String, Float, ForeignKey, JSON, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base, TimestampMixin

class MealFood(Base):
    __tablename__ = "meal_foods"

    meal_id: Mapped[str] = mapped_column(String(100), ForeignKey("meals.id", ondelete="CASCADE"), primary_key=True)
    food_id: Mapped[str] = mapped_column(String(100), ForeignKey("foods.id", ondelete="CASCADE"), primary_key=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unit: Mapped[str] = mapped_column(String(50), nullable=False, default="g")
    replaceable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    meal = relationship("Meal", back_populates="food_associations")
    food = relationship("Food", back_populates="meal_associations")

class Meal(Base, TimestampMixin):
    __tablename__ = "meals"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cuisine_id: Mapped[int] = mapped_column(ForeignKey("cuisines.id", ondelete="SET NULL"), nullable=True)
    
    # Collections mapped via JSON / JSONB
    goal: Mapped[list] = mapped_column(JSON, nullable=True)
    diet_types: Mapped[list] = mapped_column(JSON, nullable=True)
    sessions: Mapped[list] = mapped_column(JSON, nullable=True)
    
    scheduled_time: Mapped[str] = mapped_column(String(50), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    allergens: Mapped[str] = mapped_column(JSON, nullable=True) # Can be list or string
    prep_time: Mapped[str] = mapped_column(String(50), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, nullable=True)
    image_url: Mapped[str] = mapped_column(String(512), nullable=True)

    # Core macros promoted to numeric columns
    calories: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    protein: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    carbs: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fiber: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Relationships
    cuisine = relationship("Cuisine", back_populates="meals")
    food_associations = relationship("MealFood", back_populates="meal", cascade="all, delete-orphan")
