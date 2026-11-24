from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.common import Page
from app.schemas.reports import AnswerReportRow, PlayerScoreSummary
from app.security import require_admin
from app.services import reports as reports_service

router = APIRouter(
    prefix="/api/v1/reports",
    tags=["reports"],
    dependencies=[Depends(require_admin)],
)


@router.get("/players")
def player_scores(
    db: Annotated[Session, Depends(get_db)],
    class_group: str | None = None,
) -> list[PlayerScoreSummary]:
    return reports_service.player_score_summaries(db, class_group=class_group)


@router.get("/players/{player_id}/answers")
def player_answers(
    player_id: int, db: Annotated[Session, Depends(get_db)]
) -> list[AnswerReportRow]:
    rows = reports_service.player_answers(db, player_id)
    if rows is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Player not found.")
    return rows


@router.get("/answers")
def list_answers(
    db: Annotated[Session, Depends(get_db)],
    class_group: str | None = None,
    activity: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[AnswerReportRow]:
    return reports_service.list_answers(
        db,
        class_group=class_group,
        activity_slug=activity,
        limit=limit,
        offset=offset,
    )
