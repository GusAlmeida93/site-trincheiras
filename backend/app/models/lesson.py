import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, intpk


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[intpk]
    slug: Mapped[str] = mapped_column(sa.String(100), unique=True)
    title: Mapped[str] = mapped_column(sa.String(255))
    description: Mapped[str | None] = mapped_column(sa.Text)
    position: Mapped[int] = mapped_column(default=0)
    is_published: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[created_at_col]
