"""Lesson-content domain service.

Single owner of lessons, content blocks, map regions/features, activities,
questions, options and match documents. Feeds the Jinja pages, the public
JSON bundle, the admin CRUD API and the seed pipeline — all writes go through
the same slug-keyed upserts so seeding and admin edits behave identically.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Activity,
    Answer,
    ContentBlock,
    Lesson,
    MapFeature,
    MapRegion,
    MatchDocument,
    Question,
    QuestionOption,
)
from app.schemas.activities import ActivityWrite, LessonBundle, PublicActivity
from app.schemas.content import (
    ContentBlockRead,
    ContentBlockWrite,
    LessonRead,
    LessonWrite,
)
from app.schemas.map import MapRegionRead, MapRegionWrite


class ContentConflictError(Exception):
    """Raised when a change would orphan recorded answers."""


# --- lessons ---------------------------------------------------------------


def get_lesson_by_slug(session: Session, slug: str) -> Lesson | None:
    return session.scalar(select(Lesson).where(Lesson.slug == slug))


def list_lessons(session: Session) -> list[Lesson]:
    return list(session.scalars(select(Lesson).order_by(Lesson.position, Lesson.id)))


def delete_lesson(session: Session, slug: str) -> bool:
    lesson = get_lesson_by_slug(session, slug)
    if lesson is None:
        return False
    answer_count = session.scalar(
        select(func.count())
        .select_from(Answer)
        .join(Question, Answer.question_id == Question.id)
        .join(Activity, Question.activity_id == Activity.id)
        .where(Activity.lesson_id == lesson.id)
    )
    if answer_count:
        raise ContentConflictError(
            f"lesson '{slug}' has recorded answers and cannot be removed"
        )
    session.delete(lesson)
    session.flush()
    return True


def upsert_lesson(session: Session, data: LessonWrite) -> Lesson:
    lesson = get_lesson_by_slug(session, data.slug)
    if lesson is None:
        lesson = Lesson(slug=data.slug)
        session.add(lesson)
    lesson.title = data.title
    lesson.description = data.description
    lesson.position = data.position
    lesson.is_published = data.is_published
    session.flush()
    return lesson


# --- content blocks --------------------------------------------------------


def upsert_content_block(
    session: Session, lesson_id: int, data: ContentBlockWrite
) -> ContentBlock:
    block = session.scalar(select(ContentBlock).where(ContentBlock.slug == data.slug))
    if block is None:
        block = ContentBlock(slug=data.slug)
        session.add(block)
    block.lesson_id = lesson_id
    block.kind = data.kind
    block.position = data.position
    # Always replace the whole dict: in-place JSONB mutation is invisible to
    # SQLAlchemy's change tracking.
    block.data = dict(data.data)
    session.flush()
    return block


def delete_content_block(
    session: Session, slug: str, lesson_id: int | None = None
) -> bool:
    stmt = select(ContentBlock).where(ContentBlock.slug == slug)
    if lesson_id is not None:
        stmt = stmt.where(ContentBlock.lesson_id == lesson_id)
    block = session.scalar(stmt)
    if block is None:
        return False
    session.delete(block)
    session.flush()
    return True


# --- map -------------------------------------------------------------------


def upsert_map_region(
    session: Session, lesson_id: int, data: MapRegionWrite
) -> MapRegion:
    region = session.scalar(
        select(MapRegion)
        .where(MapRegion.slug == data.slug)
        .options(selectinload(MapRegion.features))
    )
    if region is None:
        region = MapRegion(slug=data.slug)
        session.add(region)
    region.lesson_id = lesson_id
    region.name = data.name
    region.center_lat = data.center_lat
    region.center_lng = data.center_lng
    region.zoom = data.zoom
    region.note = data.note
    region.position = data.position

    existing = {f.slug: f for f in region.features}
    incoming_slugs = {f.slug for f in data.features}
    for slug, feature in list(existing.items()):
        if slug not in incoming_slugs:
            region.features.remove(feature)
    for fd in data.features:
        feature = existing.get(fd.slug)
        if feature is None:
            feature = MapFeature(slug=fd.slug)
            region.features.append(feature)
        feature.name = fd.name
        feature.description = fd.description
        feature.producer = fd.producer
        feature.ceded_to = fd.ceded_to
        feature.shape = fd.shape
        feature.fill_color = fd.fill_color
        feature.coordinates = list(fd.coordinates)
        feature.radius_m = fd.radius_m
        feature.position = fd.position
    session.flush()
    return region


def delete_map_region(
    session: Session, slug: str, lesson_id: int | None = None
) -> bool:
    stmt = select(MapRegion).where(MapRegion.slug == slug)
    if lesson_id is not None:
        stmt = stmt.where(MapRegion.lesson_id == lesson_id)
    region = session.scalar(stmt)
    if region is None:
        return False
    session.delete(region)
    session.flush()
    return True


# --- activities ------------------------------------------------------------


def _question_has_answers(session: Session, question_id: int) -> bool:
    count = session.scalar(
        select(func.count()).select_from(Answer).where(Answer.question_id == question_id)
    )
    return bool(count)


def upsert_activity(session: Session, lesson_id: int, data: ActivityWrite) -> Activity:
    activity = session.scalar(
        select(Activity)
        .where(Activity.slug == data.slug)
        .options(
            selectinload(Activity.questions).selectinload(Question.options),
            selectinload(Activity.documents),
        )
    )
    if activity is None:
        activity = Activity(slug=data.slug)
        session.add(activity)
    activity.lesson_id = lesson_id
    activity.kind = data.kind
    activity.title = data.title
    activity.position = data.position
    activity.config = dict(data.config)

    # Questions are diffed by slug (never delete/recreate): answers FK to
    # questions with RESTRICT, so replacing a played question must fail
    # loudly rather than silently orphan telemetry.
    existing_q = {q.slug: q for q in activity.questions}
    incoming_q_slugs = {q.slug for q in data.questions}
    for slug, question in list(existing_q.items()):
        if slug not in incoming_q_slugs:
            if _question_has_answers(session, question.id):
                raise ContentConflictError(
                    f"question '{slug}' has recorded answers and cannot be removed"
                )
            activity.questions.remove(question)
    session.flush()

    for qd in data.questions:
        question = existing_q.get(qd.slug)
        if question is None:
            question = Question(slug=qd.slug)
            activity.questions.append(question)
        question.kind = qd.kind
        question.position = qd.position
        question.title = qd.title
        question.prompt = qd.prompt
        question.feedback_correct = qd.feedback_correct

        existing_o = {o.slug: o for o in question.options}
        incoming_o_slugs = {o.slug for o in qd.options}
        for slug, option in list(existing_o.items()):
            if slug not in incoming_o_slugs:
                question.options.remove(option)
        # Two-phase position write: (question_id, position) is unique, and a
        # reorder inside one flush could transiently collide.
        session.flush()
        for option in question.options:
            option.position = -(option.position + 1)
        session.flush()
        for od in qd.options:
            option = existing_o.get(od.slug)
            if option is None:
                option = QuestionOption(slug=od.slug)
                question.options.append(option)
            option.position = od.position
            option.label = od.label
            option.is_correct = od.is_correct
    session.flush()

    question_by_slug = {q.slug: q for q in activity.questions}
    existing_d = {d.slug: d for d in activity.documents}
    incoming_d_slugs = {d.slug for d in data.documents}
    for slug, document in list(existing_d.items()):
        if slug not in incoming_d_slugs:
            activity.documents.remove(document)
    for dd in data.documents:
        document = existing_d.get(dd.slug)
        if document is None:
            document = MatchDocument(slug=dd.slug)
            activity.documents.append(document)
        document.body = dd.body
        document.position = dd.position
        document.correct_question = question_by_slug[dd.correct_question_slug]
    session.flush()
    return activity


def delete_activity(
    session: Session, slug: str, lesson_id: int | None = None
) -> bool:
    stmt = (
        select(Activity)
        .where(Activity.slug == slug)
        .options(selectinload(Activity.questions))
    )
    if lesson_id is not None:
        stmt = stmt.where(Activity.lesson_id == lesson_id)
    activity = session.scalar(stmt)
    if activity is None:
        return False
    for question in activity.questions:
        if _question_has_answers(session, question.id):
            raise ContentConflictError(
                f"activity '{slug}' has recorded answers and cannot be removed"
            )
    session.delete(activity)
    session.flush()
    return True


# --- reads -----------------------------------------------------------------


def _load_map_regions(session: Session, lesson_id: int) -> list[MapRegion]:
    return list(
        session.scalars(
            select(MapRegion)
            .where(MapRegion.lesson_id == lesson_id)
            .order_by(MapRegion.position, MapRegion.id)
            .options(selectinload(MapRegion.features))
        )
    )


def _load_activities(session: Session, lesson_id: int) -> list[Activity]:
    return list(
        session.scalars(
            select(Activity)
            .where(Activity.lesson_id == lesson_id)
            .order_by(Activity.position, Activity.id)
            .options(
                selectinload(Activity.questions).selectinload(Question.options),
                selectinload(Activity.documents).selectinload(
                    MatchDocument.correct_question
                ),
            )
        )
    )


def list_activities(session: Session, lesson_id: int) -> list[Activity]:
    """Full activities, answers included. Admin use only."""
    return _load_activities(session, lesson_id)


def get_lesson_bundle(session: Session, lesson_slug: str) -> LessonBundle | None:
    """The student-facing bundle: activities without their answers."""
    lesson = get_lesson_by_slug(session, lesson_slug)
    if lesson is None or not lesson.is_published:
        return None
    return LessonBundle(
        lesson=LessonRead.model_validate(lesson),
        map_regions=[
            MapRegionRead.model_validate(r) for r in _load_map_regions(session, lesson.id)
        ],
        activities=[
            PublicActivity.model_validate(a) for a in _load_activities(session, lesson.id)
        ],
    )


@dataclass
class DisplayContent:
    """Everything the Jinja page needs to server-render a lesson."""

    lesson: LessonRead
    flip_cards: list[ContentBlockRead]
    participants: list[ContentBlockRead]
    clauses: list[ContentBlockRead]
    map_regions: list[MapRegionRead]
    # Public views: the page is as student-facing as the bundle.
    war_room: PublicActivity | None
    trench: PublicActivity | None


def get_display_content(session: Session, lesson_slug: str) -> DisplayContent | None:
    bundle = get_lesson_bundle(session, lesson_slug)
    if bundle is None:
        return None
    blocks = [
        ContentBlockRead.model_validate(b)
        for b in session.scalars(
            select(ContentBlock)
            .where(ContentBlock.lesson_id == bundle.lesson.id)
            .order_by(ContentBlock.position, ContentBlock.id)
        )
    ]
    by_kind: dict[str, list[ContentBlockRead]] = {}
    for block in blocks:
        by_kind.setdefault(block.kind, []).append(block)
    activities_by_kind = {a.kind: a for a in bundle.activities}
    return DisplayContent(
        lesson=bundle.lesson,
        flip_cards=by_kind.get("flip_card", []),
        participants=by_kind.get("participant", []),
        clauses=by_kind.get("clause", []),
        map_regions=bundle.map_regions,
        war_room=activities_by_kind.get("match"),
        trench=activities_by_kind.get("quiz"),
    )
