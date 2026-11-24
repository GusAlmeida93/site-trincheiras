from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, intpk

ACTIVITY_KINDS = ("match", "quiz")
QUESTION_KINDS = ("multiple_choice", "match_drawer")


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[intpk]
    lesson_id: Mapped[int] = mapped_column(
        sa.ForeignKey("lessons.id", ondelete="CASCADE")
    )
    slug: Mapped[str] = mapped_column(sa.String(100), unique=True)
    kind: Mapped[str] = mapped_column(sa.String(30))
    title: Mapped[str] = mapped_column(sa.String(255))
    position: Mapped[int] = mapped_column(default=0)
    # Scoring rules, e.g. {"points_correct": 10, "points_wrong": -5,
    # "max_penalized_errors": 2}.
    config: Mapped[dict[str, Any]] = mapped_column(default=dict)

    questions: Mapped[list["Question"]] = relationship(
        back_populates="activity",
        order_by="Question.position",
        cascade="all, delete-orphan",
    )
    documents: Mapped[list["MatchDocument"]] = relationship(
        back_populates="activity",
        order_by="MatchDocument.position",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        sa.CheckConstraint("kind IN ('match', 'quiz')", name="kind_valid"),
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[intpk]
    activity_id: Mapped[int] = mapped_column(
        sa.ForeignKey("activities.id", ondelete="CASCADE")
    )
    slug: Mapped[str] = mapped_column(sa.String(100), unique=True)
    kind: Mapped[str] = mapped_column(sa.String(30))
    position: Mapped[int] = mapped_column(default=0)
    title: Mapped[str | None] = mapped_column(sa.String(255))
    prompt: Mapped[str] = mapped_column(sa.Text)
    feedback_correct: Mapped[str | None] = mapped_column(sa.Text)

    activity: Mapped[Activity] = relationship(back_populates="questions")
    options: Mapped[list["QuestionOption"]] = relationship(
        back_populates="question",
        order_by="QuestionOption.position",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        sa.CheckConstraint(
            "kind IN ('multiple_choice', 'match_drawer')", name="kind_valid"
        ),
    )


class QuestionOption(Base):
    __tablename__ = "question_options"

    id: Mapped[intpk]
    question_id: Mapped[int] = mapped_column(
        sa.ForeignKey("questions.id", ondelete="CASCADE")
    )
    slug: Mapped[str] = mapped_column(sa.String(100), unique=True)
    position: Mapped[int] = mapped_column(default=0)
    label: Mapped[str] = mapped_column(sa.Text)
    is_correct: Mapped[bool] = mapped_column(default=False)

    question: Mapped[Question] = relationship(back_populates="options")

    __table_args__ = (
        sa.UniqueConstraint("question_id", "position"),
        # At most one correct option per question.
        sa.Index(
            "uq_question_options_one_correct",
            "question_id",
            unique=True,
            postgresql_where=sa.text("is_correct"),
        ),
    )


class MatchDocument(Base):
    __tablename__ = "match_documents"

    id: Mapped[intpk]
    activity_id: Mapped[int] = mapped_column(
        sa.ForeignKey("activities.id", ondelete="CASCADE")
    )
    slug: Mapped[str] = mapped_column(sa.String(100), unique=True)
    body: Mapped[str] = mapped_column(sa.Text)
    # Board display order (intentionally scrambled relative to the drawers).
    position: Mapped[int] = mapped_column(default=0)
    correct_question_id: Mapped[int] = mapped_column(
        sa.ForeignKey("questions.id", ondelete="CASCADE"), unique=True
    )

    activity: Mapped[Activity] = relationship(back_populates="documents")
    correct_question: Mapped[Question] = relationship()

    @property
    def correct_question_slug(self) -> str:
        # Exposed so Pydantic read models can serialize the pairing by slug.
        return self.correct_question.slug
