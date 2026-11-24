"""Token-protected content management.

PUT upserts by slug at aggregate roots — the same service functions the seed
uses, so admin edits and fixtures behave identically.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Activity, ContentBlock, Lesson, MapRegion
from app.schemas.activities import ActivityRead, ActivityWrite
from app.schemas.content import (
    ContentBlockRead,
    ContentBlockWrite,
    LessonRead,
    LessonWrite,
)
from app.schemas.map import MapRegionRead, MapRegionWrite
from app.security import require_admin
from app.services import content as content_service

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


def _require_lesson(db: Session, lesson_slug: str) -> Lesson:
    lesson = content_service.get_lesson_by_slug(db, lesson_slug)
    if lesson is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lesson not found.")
    return lesson


def _require_slug_match(path_slug: str, body_slug: str) -> None:
    if path_slug != body_slug:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Slug in the URL and in the body must match.",
        )


@router.get("/lessons")
def list_lessons(db: Annotated[Session, Depends(get_db)]) -> list[LessonRead]:
    return [LessonRead.model_validate(l) for l in content_service.list_lessons(db)]


@router.put("/lessons/{lesson_slug}")
def put_lesson(
    lesson_slug: str,
    payload: LessonWrite,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> LessonRead:
    _require_slug_match(lesson_slug, payload.slug)
    created = content_service.get_lesson_by_slug(db, lesson_slug) is None
    lesson = content_service.upsert_lesson(db, payload)
    db.commit()
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return LessonRead.model_validate(lesson)


@router.delete("/lessons/{lesson_slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson(lesson_slug: str, db: Annotated[Session, Depends(get_db)]) -> None:
    try:
        deleted = content_service.delete_lesson(db, lesson_slug)
    except content_service.ContentConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lesson not found.")
    db.commit()


@router.get("/lessons/{lesson_slug}/content-blocks")
def list_content_blocks(
    lesson_slug: str,
    db: Annotated[Session, Depends(get_db)],
    kind: str | None = None,
) -> list[ContentBlockRead]:
    lesson = _require_lesson(db, lesson_slug)
    display = content_service.get_display_content(db, lesson.slug)
    assert display is not None
    blocks = display.flip_cards + display.participants + display.clauses
    if kind:
        blocks = [b for b in blocks if b.kind == kind]
    return blocks


@router.put("/lessons/{lesson_slug}/content-blocks/{slug}")
def put_content_block(
    lesson_slug: str,
    slug: str,
    payload: ContentBlockWrite,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> ContentBlockRead:
    lesson = _require_lesson(db, lesson_slug)
    _require_slug_match(slug, payload.slug)
    created = db.scalar(select(ContentBlock.id).where(ContentBlock.slug == slug)) is None
    block = content_service.upsert_content_block(db, lesson.id, payload)
    db.commit()
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return ContentBlockRead.model_validate(block)


@router.delete(
    "/lessons/{lesson_slug}/content-blocks/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_content_block(
    lesson_slug: str, slug: str, db: Annotated[Session, Depends(get_db)]
) -> None:
    lesson = _require_lesson(db, lesson_slug)
    if not content_service.delete_content_block(db, slug, lesson_id=lesson.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Content block not found.")
    db.commit()


@router.put("/lessons/{lesson_slug}/map-regions/{slug}")
def put_map_region(
    lesson_slug: str,
    slug: str,
    payload: MapRegionWrite,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> MapRegionRead:
    lesson = _require_lesson(db, lesson_slug)
    _require_slug_match(slug, payload.slug)
    created = db.scalar(select(MapRegion.id).where(MapRegion.slug == slug)) is None
    region = content_service.upsert_map_region(db, lesson.id, payload)
    db.commit()
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return MapRegionRead.model_validate(region)


@router.delete(
    "/lessons/{lesson_slug}/map-regions/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_map_region(
    lesson_slug: str, slug: str, db: Annotated[Session, Depends(get_db)]
) -> None:
    lesson = _require_lesson(db, lesson_slug)
    if not content_service.delete_map_region(db, slug, lesson_id=lesson.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Map region not found.")
    db.commit()


@router.get("/lessons/{lesson_slug}/activities")
def list_activities(
    lesson_slug: str, db: Annotated[Session, Depends(get_db)]
) -> list[ActivityRead]:
    """Activities with their answer key (the public bundle carries none)."""
    lesson = _require_lesson(db, lesson_slug)
    return [
        ActivityRead.model_validate(a)
        for a in content_service.list_activities(db, lesson.id)
    ]


@router.put("/lessons/{lesson_slug}/activities/{slug}")
def put_activity(
    lesson_slug: str,
    slug: str,
    payload: ActivityWrite,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> ActivityRead:
    lesson = _require_lesson(db, lesson_slug)
    _require_slug_match(slug, payload.slug)
    created = db.scalar(select(Activity.id).where(Activity.slug == slug)) is None
    try:
        activity = content_service.upsert_activity(db, lesson.id, payload)
    except content_service.ContentConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))
    db.commit()
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return ActivityRead.model_validate(activity)


@router.delete(
    "/lessons/{lesson_slug}/activities/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_activity(
    lesson_slug: str, slug: str, db: Annotated[Session, Depends(get_db)]
) -> None:
    lesson = _require_lesson(db, lesson_slug)
    try:
        deleted = content_service.delete_activity(db, slug, lesson_id=lesson.id)
    except content_service.ContentConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Activity not found.")
    db.commit()
