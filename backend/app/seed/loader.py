import json
from importlib import resources
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.activities import ActivityWrite
from app.schemas.content import ContentBlockWrite, LessonWrite
from app.schemas.map import MapRegionWrite
from app.services import content as content_service


def load_fixture(name: str) -> Any:
    ref = resources.files("app.seed").joinpath("fixtures", name)
    return json.loads(ref.read_text(encoding="utf-8"))


def seed_all(session: Session) -> dict[str, int]:
    """Idempotent: upserts by slug, safe to run on every deploy."""
    lesson = content_service.upsert_lesson(
        session, LessonWrite.model_validate(load_fixture("lesson.json"))
    )

    blocks = [
        ContentBlockWrite.model_validate(raw)
        for raw in load_fixture("content_blocks.json")
    ]
    for block in blocks:
        content_service.upsert_content_block(session, lesson.id, block)

    regions = [MapRegionWrite.model_validate(raw) for raw in load_fixture("map.json")]
    for region in regions:
        content_service.upsert_map_region(session, lesson.id, region)

    activities = [
        ActivityWrite.model_validate(raw) for raw in load_fixture("activities.json")
    ]
    for activity in activities:
        content_service.upsert_activity(session, lesson.id, activity)

    return {
        "lessons": 1,
        "content_blocks": len(blocks),
        "map_regions": len(regions),
        "map_features": sum(len(r.features) for r in regions),
        "activities": len(activities),
        "questions": sum(len(a.questions) for a in activities),
        "question_options": sum(len(q.options) for a in activities for q in a.questions),
        "match_documents": sum(len(a.documents) for a in activities),
    }
