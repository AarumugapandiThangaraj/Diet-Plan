from sqlalchemy import String, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base, TimestampMixin

class Substitute(Base, TimestampMixin):
    __tablename__ = "substitutes"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    allergen_category: Mapped[str] = mapped_column(String(100), nullable=True)
    allergen_name: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    substitutes: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)

    __table_args__ = (
        UniqueConstraint("allergen_name", name="uq_substitutes_allergen_name"),
    )
