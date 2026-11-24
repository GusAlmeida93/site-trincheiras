"""Answer domain service. Owns the answers table and decides every verdict.

The browser sends only which choice was made; correctness and score are
computed here from the lesson content and the activity's scoring rules.
"""

from dataclasses import dataclass
from datetime import timedelta

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Activity,
    Answer,
    Lesson,
    MatchDocument,
    Player,
    Question,
    QuestionOption,
)
from app.schemas.answers import AnswerCreate, AnswerRetry
from app.services.scoring import ScoringRules

# A retried attempt is matched against answers recorded since it was first
# sent; the slack covers the time the request spent before reaching the
# database.
RETRY_SLACK = timedelta(seconds=10)


class UnknownPlayerError(Exception):
    pass


class UnknownQuestionError(Exception):
    pass


class UnknownChoiceError(Exception):
    pass


@dataclass(frozen=True)
class AnswerOutcome:
    # None when the attempt was judged but not recorded (anonymous play).
    answer_id: int | None
    player_id: int | None
    question_id: int
    choice_id: int
    is_correct: bool
    score_delta: int
    feedback: str | None
    # True when this call inserted a new answer row.
    created: bool


def _load_question(session: Session, question_id: int) -> Question:
    # Questions of unpublished lessons are not in any public bundle, so they
    # must not be answerable either: a verdict would reveal their answers.
    question = session.scalar(
        select(Question)
        .join(Activity, Question.activity_id == Activity.id)
        .join(Lesson, Activity.lesson_id == Lesson.id)
        .where(Question.id == question_id, Lesson.is_published)
        .options(joinedload(Question.activity))
    )
    if question is None:
        raise UnknownQuestionError(f"question {question_id} not found")
    return question


def _judge_choice(session: Session, question: Question, choice_id: int) -> tuple[str, bool]:
    """Returns the choice's slug (what gets stored) and whether it is correct."""
    if question.kind == "match_drawer":
        document = session.scalar(
            select(MatchDocument).where(
                MatchDocument.id == choice_id,
                MatchDocument.activity_id == question.activity_id,
            )
        )
        if document is None:
            raise UnknownChoiceError(
                f"document {choice_id} does not belong to question {question.id}'s activity"
            )
        return document.slug, document.correct_question_id == question.id

    option = session.scalar(
        select(QuestionOption).where(
            QuestionOption.id == choice_id,
            QuestionOption.question_id == question.id,
        )
    )
    if option is None:
        raise UnknownChoiceError(
            f"option {choice_id} does not belong to question {question.id}"
        )
    return option.slug, option.is_correct


def _errors_in_current_round(session: Session, player_id: int, question_id: int) -> int:
    """Wrong answers since the player last got this question right.

    A correct answer closes the round, so replaying an activity starts each
    question with a clean slate, while reloading the page mid-question does
    not reset the cap.
    """
    mine = (Answer.player_id == player_id) & (Answer.question_id == question_id)
    last_correct = (
        select(func.max(Answer.id)).where(mine, Answer.is_correct).scalar_subquery()
    )
    count = session.scalar(
        select(func.count())
        .select_from(Answer)
        .where(mine, ~Answer.is_correct, Answer.id > func.coalesce(last_correct, 0))
    )
    return count or 0


def _find_recorded_attempt(
    session: Session,
    player_id: int,
    question_id: int,
    selected_value: str,
    retry: AnswerRetry,
) -> Answer | None:
    window = timedelta(milliseconds=retry.elapsed_ms) + RETRY_SLACK
    stmt = select(Answer).where(
        Answer.player_id == player_id,
        Answer.question_id == question_id,
        Answer.selected_value == selected_value,
        Answer.created_at >= func.now() - window,
    )
    if retry.after_answer_id is not None:
        stmt = stmt.where(Answer.id > retry.after_answer_id)
    return session.scalar(stmt.order_by(Answer.id.desc()).limit(1))


def submit_answer(session: Session, data: AnswerCreate) -> AnswerOutcome:
    if data.player_id is not None:
        if session.scalar(select(Player.id).where(Player.id == data.player_id)) is None:
            raise UnknownPlayerError(f"player {data.player_id} not found")
    question = _load_question(session, data.question_id)
    selected_value, is_correct = _judge_choice(session, question, data.choice_id)
    rules = ScoringRules.from_config(question.activity.config)
    feedback = question.feedback_correct if is_correct else None

    def outcome(answer_id: int | None, score_delta: int, created: bool) -> AnswerOutcome:
        return AnswerOutcome(
            answer_id=answer_id,
            player_id=data.player_id,
            question_id=question.id,
            choice_id=data.choice_id,
            is_correct=is_correct,
            score_delta=score_delta,
            feedback=feedback,
            created=created,
        )

    if data.player_id is None:
        # Anonymous play: judged with the same rules, never recorded. There is
        # no identity to count earlier errors against, so the cap relies on
        # the browser's own count; that only changes the number this browser
        # displays, since nothing is stored.
        return outcome(None, rules.score_delta(is_correct, data.prior_errors), created=False)

    # One answer at a time per player and question: the error count and the
    # retry lookup below must see every earlier answer, including one from a
    # request that is committing right now. Released at commit or rollback.
    session.execute(
        select(
            func.pg_advisory_xact_lock(
                sa.cast(data.player_id, sa.Integer), sa.cast(question.id, sa.Integer)
            )
        )
    )

    if data.retry is not None:
        recorded = _find_recorded_attempt(
            session, data.player_id, question.id, selected_value, data.retry
        )
        if recorded is not None:
            return outcome(recorded.id, recorded.score_delta, created=False)

    prior_errors = _errors_in_current_round(session, data.player_id, question.id)
    answer = Answer(
        player_id=data.player_id,
        question_id=question.id,
        selected_value=selected_value,
        is_correct=is_correct,
        score_delta=rules.score_delta(is_correct, prior_errors),
    )
    session.add(answer)
    session.flush()
    return outcome(answer.id, answer.score_delta, created=True)
