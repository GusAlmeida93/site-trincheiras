from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.answers import AnswerCreate, AnswerRead
from app.services import answers as answers_service

router = APIRouter(prefix="/api/v1/answers", tags=["answers"])


@router.post("", status_code=status.HTTP_201_CREATED)
def record_answer(
    payload: AnswerCreate, db: Annotated[Session, Depends(get_db)]
) -> AnswerRead:
    try:
        answer = answers_service.record_answer(db, payload)
    except answers_service.UnknownPlayerError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Player not found.")
    except answers_service.UnknownQuestionError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Question not found.")
    db.commit()
    return AnswerRead.model_validate(answer)
