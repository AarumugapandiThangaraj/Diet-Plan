from sqlalchemy import String, JSON
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base, TimestampMixin

class UserPreference(Base, TimestampMixin):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_identifier: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    
    # Store arrays of strings or configurations in JSONB / JSON
    likes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    dislikes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    allergies: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    notes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
