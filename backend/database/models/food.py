from sqlalchemy import String, Float, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base, TimestampMixin

class FoodIngredient(Base):
    __tablename__ = "food_ingredients"

    food_id: Mapped[str] = mapped_column(String(100), ForeignKey("foods.id", ondelete="CASCADE"), primary_key=True)
    ingredient_id: Mapped[str] = mapped_column(String(100), ForeignKey("ingredients.id", ondelete="CASCADE"), primary_key=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unit: Mapped[str] = mapped_column(String(50), nullable=False, default="g")
    swapable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    food = relationship("Food", back_populates="ingredient_associations")
    ingredient = relationship("Ingredient", back_populates="food_associations")

class Food(Base, TimestampMixin):
    __tablename__ = "foods"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cuisine_id: Mapped[int] = mapped_column(ForeignKey("cuisines.id", ondelete="SET NULL"), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    diet_types: Mapped[list] = mapped_column(JSON, nullable=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    min_quantity: Mapped[float] = mapped_column(Float, nullable=True)
    max_quantity: Mapped[float] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=False, default="g")
    supports: Mapped[list] = mapped_column(JSON, nullable=True)
    preparation: Mapped[str] = mapped_column(Text, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    warning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Core macros promoted to numeric columns
    calories: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    protein: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    carbs: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fiber: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    type: Mapped[str] = mapped_column(String(100), nullable=True)
    image_url: Mapped[str] = mapped_column(String(512), nullable=True)

    # Relationships
    cuisine = relationship("Cuisine", back_populates="foods")
    ingredient_associations = relationship("FoodIngredient", back_populates="food", cascade="all, delete-orphan")
    meal_associations = relationship("MealFood", back_populates="food", cascade="all, delete-orphan")
