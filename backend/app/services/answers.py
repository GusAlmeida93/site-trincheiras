"""Answer-telemetry domain service. Owns the answers table."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Answer, Player, Question
from app.schemas.answers import AnswerCreate


class UnknownPlayerError(Exception):
    pass


class UnknownQuestionError(Exception):
    pass


def record_answer(session: Session, data: AnswerCreate) -> Answer:
    if data.player_id is not None:
        if session.scalar(select(Player.id).where(Player.id == data.player_id)) is None:
            raise UnknownPlayerError(f"player {data.player_id} not found")
    if session.scalar(select(Question.id).where(Question.id == data.question_id)) is None:
        raise UnknownQuestionError(f"question {data.question_id} not found")

    answer = Answer(
        player_id=data.player_id,
        question_id=data.question_id,
        selected_value=data.selected_value,
        is_correct=data.is_correct,
        score_delta=data.score_delta,
    )
    session.add(answer)
    session.flush()
    return answer
