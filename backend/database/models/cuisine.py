from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base, TimestampMixin

class Cuisine(Base, TimestampMixin):
    __tablename__ = "cuisines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Relationships
    foods = relationship("Food", back_populates="cuisine")
    meals = relationship("Meal", back_populates="cuisine")
