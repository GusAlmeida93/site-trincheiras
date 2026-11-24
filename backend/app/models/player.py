from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at_col, intpk

if TYPE_CHECKING:
    from app.models.answer import Answer


class Player(Base):
    __tablename__ = "players"

    id: Mapped[intpk]
    name: Mapped[str] = mapped_column(sa.String(255))
    class_group: Mapped[str] = mapped_column(sa.String(50), index=True)
    recruit_number: Mapped[str | None] = mapped_column(sa.String(50))
    created_at: Mapped[created_at_col]

    answers: Mapped[list["Answer"]] = relationship(back_populates="player")
