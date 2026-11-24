from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.answers import AnswerCreate, AnswerResult
from app.services import answers as answers_service

router = APIRouter(prefix="/api/v1/answers", tags=["answers"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {
            "model": AnswerResult,
            "description": (
                "Judged without recording a new answer: anonymous play, or a "
                "retry of an attempt that was already recorded."
            ),
        },
        status.HTTP_404_NOT_FOUND: {"description": "Unknown player or question."},
    },
)
def submit_answer(
    payload: AnswerCreate,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> AnswerResult:
    """Judge one attempt and, for an enlisted player, record it.

    The server decides `is_correct` and `score_delta` from the lesson content
    and the activity's scoring rules; the request carries only the choice.
    """
    try:
        outcome = answers_service.submit_answer(db, payload)
    except answers_service.UnknownPlayerError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Player not found.")
    except answers_service.UnknownQuestionError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Question not found.")
    except answers_service.UnknownChoiceError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The choice does not belong to this question.",
        )
    db.commit()
    if not outcome.created:
        response.status_code = status.HTTP_200_OK
    return AnswerResult(
        id=outcome.answer_id,
        player_id=outcome.player_id,
        question_id=outcome.question_id,
        choice_id=outcome.choice_id,
        is_correct=outcome.is_correct,
        score_delta=outcome.score_delta,
        feedback=outcome.feedback,
    )
