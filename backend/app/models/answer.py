import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at_col, intpk
from app.models.player import Player
from app.models.activity import Question


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[intpk]
    # Nullable: anonymous play is allowed (players who skip enlistment).
    player_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("players.id", ondelete="SET NULL"), index=True
    )
    question_id: Mapped[int] = mapped_column(
        sa.ForeignKey("questions.id", ondelete="RESTRICT"), index=True
    )
    # Option slug (quiz) or document slug (match). is_correct and score_delta
    # are computed by the server when the answer is recorded.
    selected_value: Mapped[str] = mapped_column(sa.Text)
    is_correct: Mapped[bool]
    score_delta: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[created_at_col]

    player: Mapped[Player | None] = relationship(back_populates="answers")
    question: Mapped[Question] = relationship()

    __table_args__ = (sa.Index("ix_answers_created_at", "created_at"),)
