import re
import unicodedata
from typing import Annotated
from urllib.parse import quote
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.schemas.common import Page
from app.schemas.reports import (
    ActivitySummary,
    AnswerReportRow,
    ClassSummary,
    PlayerScoreSummary,
)
from app.security import require_admin
from app.services import reports as reports_service

router = APIRouter(
    prefix="/api/v1/reports",
    tags=["reports"],
    dependencies=[Depends(require_admin)],
)


@router.get("/classes")
def class_summaries(db: Annotated[Session, Depends(get_db)]) -> list[ClassSummary]:
    return reports_service.class_summaries(db)


@router.get("/activities")
def activity_summaries(
    db: Annotated[Session, Depends(get_db)],
    class_group: str | None = None,
) -> list[ActivitySummary]:
    """Per activity and per question: attempts, correct answers, students reached."""
    return reports_service.activity_summaries(db, class_group=class_group)


@router.get(
    "/players.csv",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}, "description": "One row per student."}},
)
def class_csv(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    class_group: Annotated[str, Query(min_length=1, max_length=50)],
) -> Response:
    """A class as a spreadsheet: semicolon-separated, UTF-8 with BOM (opens in Excel)."""
    body = reports_service.class_csv(db, class_group, ZoneInfo(settings.display_timezone))
    if body is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Class not found.")
    ascii_name = unicodedata.normalize("NFKD", class_group).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-") or "turma"
    full_name = quote(f"turma-{class_group}.csv", safe="")
    return Response(
        # The BOM is how Excel recognizes UTF-8.
        content=("\ufeff" + body).encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"turma-{slug}.csv\"; filename*=UTF-8''{full_name}"
            )
        },
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
