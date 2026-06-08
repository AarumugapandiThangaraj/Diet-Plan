from sqlalchemy import String, Float, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base, TimestampMixin

class Ingredient(Base, TimestampMixin):
    __tablename__ = "ingredients"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    default_unit: Mapped[str] = mapped_column(String(50), nullable=False, default="g")
    
    # Core macros promoted to numeric columns
    calories: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    protein: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    carbs: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fiber: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Micronutrients and metadata stored as JSONB / JSON
    micronutrients: Mapped[dict] = mapped_column(JSON, nullable=True)
    benefits: Mapped[dict] = mapped_column(JSON, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    main_name: Mapped[str] = mapped_column(String(100), nullable=True)
    grup: Mapped[str] = mapped_column(String(100), nullable=True)
    food_type: Mapped[str] = mapped_column(String(50), nullable=True)
    food_state: Mapped[str] = mapped_column(String(50), nullable=True)
    allergens: Mapped[str] = mapped_column(JSON, nullable=True) # Can be list or string
    caution: Mapped[str] = mapped_column(Text, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    conversions: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)

    # Relationships
    food_associations = relationship("FoodIngredient", back_populates="ingredient")
