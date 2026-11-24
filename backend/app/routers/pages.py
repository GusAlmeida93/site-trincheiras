from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.avatars import AVATARS
from app.config import get_settings
from app.db import get_db
from app.services import content as content_service

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request, db: Annotated[Session, Depends(get_db)]):
    settings = get_settings()
    display = content_service.get_display_content(db, settings.default_lesson_slug)
    if display is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lesson content is not available. Has the database been seeded?",
        )
    return request.app.state.templates.TemplateResponse(
        request,
        "index.html",
        {
            "lesson": display.lesson,
            "flip_cards": display.flip_cards,
            "participants": display.participants,
            "clauses": display.clauses,
            "map_regions": display.map_regions,
            "war_room": display.war_room,
            "trench": display.trench,
            "avatars": AVATARS,
        },
    )
