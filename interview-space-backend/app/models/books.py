from app.core.database import Base
from sqlalchemy import (
    String,
)
from sqlalchemy.orm import Mapped, mapped_column


class Books(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str] = mapped_column(String(255))
    author: Mapped[str] = mapped_column(String(255))
