"""Reporting domain service: read-only projections for teachers.

Deliberately cross-domain (players + answers + content) — this is the read
model that would become its own service first if the monolith is ever split.
"""

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Activity, Answer, Player, Question
from app.schemas.common import Page
from app.schemas.reports import AnswerReportRow, PlayerScoreSummary


def player_score_summaries(
    session: Session, class_group: str | None = None
) -> list[PlayerScoreSummary]:
    stmt = (
        select(
            Player.id.label("player_id"),
            Player.name,
            Player.class_group,
            Player.recruit_number,
            func.count(Answer.id).label("answers_count"),
            func.coalesce(
                func.sum(case((Answer.is_correct, 1), else_=0)), 0
            ).label("correct_count"),
            func.coalesce(func.sum(Answer.score_delta), 0).label("total_score"),
            func.max(Answer.created_at).label("last_answer_at"),
        )
        .outerjoin(Answer, Answer.player_id == Player.id)
        .group_by(Player.id)
        .order_by(Player.class_group, Player.name, Player.id)
    )
    if class_group:
        stmt = stmt.where(Player.class_group == class_group)
    return [PlayerScoreSummary.model_validate(row._asdict()) for row in session.execute(stmt)]


def _answer_rows_stmt():
    return (
        select(
            Answer.id,
            Answer.player_id,
            Player.name.label("player_name"),
            Player.class_group,
            Activity.slug.label("activity_slug"),
            Question.slug.label("question_slug"),
            Answer.selected_value,
            Answer.is_correct,
            Answer.score_delta,
            Answer.created_at,
        )
        .join(Question, Answer.question_id == Question.id)
        .join(Activity, Question.activity_id == Activity.id)
        .outerjoin(Player, Answer.player_id == Player.id)
    )


def player_answers(session: Session, player_id: int) -> list[AnswerReportRow] | None:
    if session.scalar(select(Player.id).where(Player.id == player_id)) is None:
        return None
    stmt = (
        _answer_rows_stmt()
        .where(Answer.player_id == player_id)
        .order_by(Answer.created_at, Answer.id)
    )
    return [AnswerReportRow.model_validate(row._asdict()) for row in session.execute(stmt)]


def list_answers(
    session: Session,
    class_group: str | None = None,
    activity_slug: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[AnswerReportRow]:
    stmt = _answer_rows_stmt()
    if class_group:
        stmt = stmt.where(Player.class_group == class_group)
    if activity_slug:
        stmt = stmt.where(Activity.slug == activity_slug)

    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = session.execute(
        stmt.order_by(Answer.created_at.desc(), Answer.id.desc()).limit(limit).offset(offset)
    )
    return Page(
        items=[AnswerReportRow.model_validate(row._asdict()) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
