from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, intpk

CONTENT_BLOCK_KINDS = ("flip_card", "participant", "clause")


class ContentBlock(Base):
    __tablename__ = "content_blocks"

    id: Mapped[intpk]
    lesson_id: Mapped[int] = mapped_column(
        sa.ForeignKey("lessons.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(sa.String(30))
    slug: Mapped[str] = mapped_column(sa.String(100), unique=True)
    position: Mapped[int] = mapped_column(default=0)
    data: Mapped[dict[str, Any]]

    __table_args__ = (
        sa.CheckConstraint(
            "kind IN ('flip_card', 'participant', 'clause')", name="kind_valid"
        ),
        sa.Index("ix_content_blocks_lesson_kind_position", "lesson_id", "kind", "position"),
    )
