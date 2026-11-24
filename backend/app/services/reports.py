"""Reporting domain service: read-only projections for teachers.

Deliberately cross-domain (players + answers + content) — this is the read
model that would become its own service first if the monolith is ever split.
"""

import csv
import io
from datetime import tzinfo

from sqlalchemy import and_, case, distinct, func, select
from sqlalchemy.orm import Session

from app.models import Activity, Answer, MatchDocument, Player, Question, QuestionOption
from app.schemas.common import Page
from app.schemas.reports import (
    ActivitySummary,
    AnswerReportRow,
    ClassSummary,
    PlayerScoreSummary,
    QuestionSummary,
)

_CORRECT = case((Answer.is_correct, 1), else_=0)


def class_summaries(session: Session) -> list[ClassSummary]:
    stmt = (
        select(
            Player.class_group,
            func.count(distinct(Player.id)).label("players_count"),
            func.count(Answer.id).label("answers_count"),
            func.coalesce(func.sum(_CORRECT), 0).label("correct_count"),
            func.coalesce(func.sum(Answer.score_delta), 0).label("total_score"),
            func.max(Answer.created_at).label("last_answer_at"),
        )
        .outerjoin(Answer, Answer.player_id == Player.id)
        .group_by(Player.class_group)
        .order_by(Player.class_group)
    )
    return [ClassSummary.model_validate(row._asdict()) for row in session.execute(stmt)]


def _player_scores_stmt():
    return (
        select(
            Player.id.label("player_id"),
            Player.name,
            Player.class_group,
            Player.recruit_number,
            func.count(Answer.id).label("answers_count"),
            func.coalesce(func.sum(_CORRECT), 0).label("correct_count"),
            func.coalesce(func.sum(Answer.score_delta), 0).label("total_score"),
            func.max(Answer.created_at).label("last_answer_at"),
        )
        .outerjoin(Answer, Answer.player_id == Player.id)
        .group_by(Player.id)
        .order_by(Player.class_group, Player.name, Player.id)
    )


def player_score_summaries(
    session: Session, class_group: str | None = None
) -> list[PlayerScoreSummary]:
    stmt = _player_scores_stmt()
    if class_group:
        stmt = stmt.where(Player.class_group == class_group)
    return [PlayerScoreSummary.model_validate(row._asdict()) for row in session.execute(stmt)]


def player_score_summary(session: Session, player_id: int) -> PlayerScoreSummary | None:
    row = session.execute(
        _player_scores_stmt().where(Player.id == player_id)
    ).one_or_none()
    return PlayerScoreSummary.model_validate(row._asdict()) if row else None


def _answer_rows_stmt():
    return (
        select(
            Answer.id,
            Answer.player_id,
            Player.name.label("player_name"),
            Player.class_group,
            Activity.slug.label("activity_slug"),
            Activity.title.label("activity_title"),
            Question.slug.label("question_slug"),
            Question.title.label("question_title"),
            Answer.selected_value,
            # Slugs are unique per table, so neither join can multiply rows.
            func.coalesce(QuestionOption.label, MatchDocument.body).label("selected_label"),
            Answer.is_correct,
            Answer.score_delta,
            Answer.created_at,
        )
        .join(Question, Answer.question_id == Question.id)
        .join(Activity, Question.activity_id == Activity.id)
        .outerjoin(Player, Answer.player_id == Player.id)
        .outerjoin(
            QuestionOption,
            and_(
                QuestionOption.question_id == Question.id,
                QuestionOption.slug == Answer.selected_value,
            ),
        )
        .outerjoin(
            MatchDocument,
            and_(
                MatchDocument.activity_id == Activity.id,
                MatchDocument.slug == Answer.selected_value,
            ),
        )
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


def activity_summaries(
    session: Session, class_group: str | None = None
) -> list[ActivitySummary]:
    """Every activity and question, with how the class (or everyone) did.

    Questions nobody answered are listed with zeros. Without a class filter,
    answers from students who skipped enlistment count too.
    """
    # The class filter belongs in the join, not in WHERE: filtering afterwards
    # would drop the questions the class has not answered yet.
    answer_join = Answer.question_id == Question.id
    if class_group:
        answer_join = and_(
            answer_join,
            Answer.player_id.in_(
                select(Player.id).where(Player.class_group == class_group)
            ),
        )
    correct_player = case((Answer.is_correct, Answer.player_id))

    question_rows = session.execute(
        select(
            Activity.id.label("activity_id"),
            Question.slug.label("question_slug"),
            Question.title,
            Question.prompt,
            func.count(Answer.id).label("answers_count"),
            func.coalesce(func.sum(_CORRECT), 0).label("correct_count"),
            func.count(distinct(Answer.player_id)).label("players_count"),
            func.count(distinct(correct_player)).label("players_correct_count"),
        )
        .select_from(Activity)
        .join(Question, Question.activity_id == Activity.id)
        .outerjoin(Answer, answer_join)
        .group_by(Activity.id, Question.id)
        .order_by(Activity.id, Question.position, Question.id)
    ).all()

    # Students per activity cannot be added up from the questions: the same
    # student answers several of them.
    activity_rows = session.execute(
        select(
            Activity.id,
            Activity.slug,
            Activity.title,
            Activity.kind,
            func.count(distinct(Answer.player_id)).label("players_count"),
        )
        .select_from(Activity)
        .outerjoin(Question, Question.activity_id == Activity.id)
        .outerjoin(Answer, answer_join)
        .group_by(Activity.id)
        .order_by(Activity.position, Activity.id)
    ).all()

    summaries: list[ActivitySummary] = []
    for activity in activity_rows:
        questions = [
            QuestionSummary.model_validate(row._asdict())
            for row in question_rows
            if row.activity_id == activity.id
        ]
        summaries.append(
            ActivitySummary(
                activity_slug=activity.slug,
                title=activity.title,
                kind=activity.kind,
                players_count=activity.players_count,
                answers_count=sum(q.answers_count for q in questions),
                correct_count=sum(q.correct_count for q in questions),
                questions=questions,
            )
        )
    return summaries


def _csv_cell(value: object) -> object:
    # A student types their own name and class. A cell that begins with one of
    # these would run as a formula when the teacher opens the file.
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def class_csv(session: Session, class_group: str, timezone: tzinfo) -> str | None:
    """One row per student of the class, with the score in each activity.

    Semicolon-separated: that is what a spreadsheet in a pt-BR locale expects
    (the comma is its decimal mark). None when the class has no students.
    """
    players = player_score_summaries(session, class_group=class_group)
    if not players:
        return None

    activities = session.execute(
        select(Activity.id, Activity.title).order_by(Activity.position, Activity.id)
    ).all()
    per_activity: dict[tuple[int, int], int] = {
        (row.player_id, row.activity_id): row.score
        for row in session.execute(
            select(
                Answer.player_id,
                Question.activity_id,
                func.coalesce(func.sum(Answer.score_delta), 0).label("score"),
            )
            .join(Question, Answer.question_id == Question.id)
            .join(Player, Answer.player_id == Player.id)
            .where(Player.class_group == class_group)
            .group_by(Answer.player_id, Question.activity_id)
        )
    }
    enlisted_at = dict(
        session.execute(
            select(Player.id, Player.created_at).where(Player.class_group == class_group)
        ).all()
    )

    def local(moment) -> str:  # type: ignore[no-untyped-def]
        return moment.astimezone(timezone).strftime("%d/%m/%Y %H:%M") if moment else ""

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(
        ["Nome", "Turma", "Nº de recruta", "Alistamento", "Respostas", "Acertos"]
        + [f"Pontos: {activity.title}" for activity in activities]
        + ["Pontuação total", "Última resposta"]
    )
    for player in players:
        writer.writerow(
            [
                _csv_cell(player.name),
                _csv_cell(player.class_group),
                _csv_cell(player.recruit_number or ""),
                local(enlisted_at.get(player.player_id)),
                player.answers_count,
                player.correct_count,
            ]
            + [per_activity.get((player.player_id, activity.id), 0) for activity in activities]
            + [player.total_score, local(player.last_answer_at)]
        )
    return buffer.getvalue()
