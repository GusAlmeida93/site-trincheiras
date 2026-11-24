from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.activities import LessonBundle
from app.services import content as content_service

router = APIRouter(prefix="/api/v1/lessons", tags=["lessons"])


@router.get("/{slug}/bundle")
def get_lesson_bundle(slug: str, db: Annotated[Session, Depends(get_db)]) -> LessonBundle:
    bundle = content_service.get_lesson_bundle(db, slug)
    if bundle is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lesson not found.")
    return bundle
