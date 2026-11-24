from sqlalchemy import func, select

from app.models import Answer, ContentBlock, MapFeature, Question, QuestionOption
from app.seed.loader import seed_all
from app.services import content as content_service


def _counts(session):
    return {
        model.__tablename__: session.scalar(select(func.count()).select_from(model))
        for model in (ContentBlock, MapFeature, Question, QuestionOption)
    }


def test_seed_is_idempotent(db_session, seeded_content):
    first = _counts(db_session)
    seed_all(db_session)
    assert _counts(db_session) == first
    assert first == {
        "content_blocks": 15,
        "map_features": 13,
        "questions": 12,
        "question_options": 21,
    }


def test_seed_restores_mutated_content(db_session, seeded_content):
    block = db_session.scalar(
        select(ContentBlock).where(ContentBlock.slug == "article-231")
    )
    original_title = block.data["title"]
    block.data = {**block.data, "title": "Vandalized"}
    db_session.flush()

    seed_all(db_session)
    db_session.expire_all()

    block = db_session.scalar(
        select(ContentBlock).where(ContentBlock.slug == "article-231")
    )
    assert block.data["title"] == original_title == "A Cláusula de Culpa"


def test_seed_preserves_answers_on_reseed(db_session, seeded_content):
    question = db_session.scalar(select(Question).where(Question.slug == "trench-1"))
    db_session.add(
        Answer(
            question_id=question.id,
            selected_value="trench-1-opt-2",
            is_correct=True,
            score_delta=10,
        )
    )
    db_session.flush()

    seed_all(db_session)

    count = db_session.scalar(select(func.count()).select_from(Answer))
    assert count == 1
    # Question id must be stable across reseeds (diffed, not recreated).
    still_there = db_session.scalar(select(Question).where(Question.id == question.id))
    assert still_there is not None and still_there.slug == "trench-1"


def test_display_content_grouping(db_session, seeded_content):
    display = content_service.get_display_content(db_session, "tratado-de-versalhes")
    assert display is not None
    assert [b.slug for b in display.flip_cards] == [
        "causes",
        "main-points",
        "consequences",
        "reactions",
    ]
    assert len(display.participants) == 4
    assert [c.data["number"] for c in display.clauses] == [
        "Artigo 51",
        "Artigo 119",
        "Artigo 160",
        "Artigo 231",
        "Artigo 232",
        "Artigo 42",
        "Artigo 87",
    ]
    assert display.war_room is not None and display.war_room.slug == "war-room"
    assert display.trench is not None and len(display.trench.questions) == 7
