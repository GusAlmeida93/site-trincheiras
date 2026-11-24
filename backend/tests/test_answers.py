import pytest
from sqlalchemy import func, select

from app.models import Activity, Answer, Lesson

FEEDBACK_TRENCH_1 = "Correto. A Alsácia-Lorena voltou para a França pelo Tratado de Versalhes."


@pytest.fixture()
def submit(client):
    def _submit(**body):
        return client.post("/api/v1/answers", json=body)

    return _submit


def stored_answers(db_session):
    return list(db_session.scalars(select(Answer).order_by(Answer.id)))


# --- quiz ------------------------------------------------------------------


def test_correct_quiz_answer_is_scored_and_recorded(submit, player, answer_key, db_session):
    response = submit(
        player_id=player["id"],
        question_id=answer_key.question_id("trench-1"),
        choice_id=answer_key.option_id("trench-1-opt-2"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body == {
        "id": body["id"],
        "player_id": player["id"],
        "question_id": answer_key.question_id("trench-1"),
        "choice_id": answer_key.option_id("trench-1-opt-2"),
        "is_correct": True,
        "score_delta": 10,
        "feedback": FEEDBACK_TRENCH_1,
    }

    [row] = stored_answers(db_session)
    assert row.id == body["id"]
    assert row.player_id == player["id"]
    # The stored value stays the slug, so reports read as before.
    assert row.selected_value == "trench-1-opt-2"
    assert row.is_correct is True
    assert row.score_delta == 10


def test_wrong_quiz_answer_costs_points_and_gets_no_feedback(submit, player, answer_key, db_session):
    response = submit(
        player_id=player["id"],
        question_id=answer_key.question_id("trench-1"),
        choice_id=answer_key.option_id("trench-1-opt-1"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["is_correct"] is False
    assert body["score_delta"] == -5
    assert body["feedback"] is None

    [row] = stored_answers(db_session)
    assert (row.selected_value, row.is_correct, row.score_delta) == ("trench-1-opt-1", False, -5)


@pytest.mark.parametrize(
    "claim",
    [
        {"is_correct": True},
        {"score_delta": 1000},
        {"is_correct": True, "score_delta": 1000},
        {"selected_value": "trench-1-opt-2"},
    ],
)
def test_client_reported_verdicts_are_rejected(submit, player, answer_key, db_session, claim):
    response = submit(
        player_id=player["id"],
        question_id=answer_key.question_id("trench-1"),
        choice_id=answer_key.option_id("trench-1-opt-1"),
        **claim,
    )
    assert response.status_code == 422
    assert stored_answers(db_session) == []


# --- error cap -------------------------------------------------------------


def test_error_cap_per_question(submit, player, answer_key):
    question = answer_key.question_id("trench-1")
    wrong = [answer_key.option_id("trench-1-opt-1"), answer_key.option_id("trench-1-opt-3")]

    def attempt(choice_id):
        response = submit(player_id=player["id"], question_id=question, choice_id=choice_id)
        assert response.status_code == 201
        return response.json()["score_delta"]

    # Two penalized errors, then wrong answers are free (seed: max 2).
    assert [attempt(wrong[0]), attempt(wrong[1]), attempt(wrong[0]), attempt(wrong[1])] == [
        -5,
        -5,
        0,
        0,
    ]
    # The correct answer still scores in full...
    assert attempt(answer_key.option_id("trench-1-opt-2")) == 10
    # ...and closes the round: a replay of the mission is penalized afresh.
    assert [attempt(wrong[0]), attempt(wrong[0]), attempt(wrong[0])] == [-5, -5, 0]


def test_error_cap_is_counted_per_question_and_per_player(submit, client, player, answer_key):
    other = client.post(
        "/api/v1/players", json={"name": "Bia Lima", "class_group": "9º B"}
    ).json()
    q1 = answer_key.question_id("trench-1")
    q1_wrong = answer_key.option_id("trench-1-opt-1")

    for _ in range(3):
        submit(player_id=player["id"], question_id=q1, choice_id=q1_wrong)

    # Another question for the same player starts at zero errors.
    response = submit(
        player_id=player["id"],
        question_id=answer_key.question_id("trench-2"),
        choice_id=answer_key.option_id("trench-2-opt-2"),
    )
    assert response.json()["score_delta"] == -5
    # And so does the same question for another player.
    response = submit(player_id=other["id"], question_id=q1, choice_id=q1_wrong)
    assert response.json()["score_delta"] == -5


def test_scoring_follows_the_activity_config(submit, player, answer_key, db_session):
    activity = db_session.scalar(select(Activity).where(Activity.slug == "trench-mission"))
    activity.config = {"points_correct": 20, "points_wrong": -7, "max_penalized_errors": 1}
    db_session.flush()

    question = answer_key.question_id("trench-1")
    deltas = [
        submit(player_id=player["id"], question_id=question, choice_id=choice).json()[
            "score_delta"
        ]
        for choice in (
            answer_key.option_id("trench-1-opt-1"),
            answer_key.option_id("trench-1-opt-3"),
            answer_key.option_id("trench-1-opt-2"),
        )
    ]
    assert deltas == [-7, 0, 20]


def test_prior_errors_from_the_client_are_ignored_for_enlisted_players(
    submit, player, answer_key
):
    # A client cannot talk its way out of a penalty by claiming the cap is used up.
    response = submit(
        player_id=player["id"],
        question_id=answer_key.question_id("trench-1"),
        choice_id=answer_key.option_id("trench-1-opt-1"),
        prior_errors=99,
    )
    assert response.json()["score_delta"] == -5


# --- match (war room) ------------------------------------------------------


def test_document_in_its_drawer_is_correct(submit, player, answer_key, db_session):
    response = submit(
        player_id=player["id"],
        question_id=answer_key.question_id("drawer-1"),
        choice_id=answer_key.document_id("doc-1"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["is_correct"] is True
    assert body["score_delta"] == 10
    [row] = stored_answers(db_session)
    assert row.selected_value == "doc-1"


def test_document_in_another_drawer_is_wrong(submit, player, answer_key, db_session):
    response = submit(
        player_id=player["id"],
        question_id=answer_key.question_id("drawer-2"),
        choice_id=answer_key.document_id("doc-1"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["is_correct"] is False
    assert body["score_delta"] == -5
    [row] = stored_answers(db_session)
    assert (row.selected_value, row.is_correct) == ("doc-1", False)


def test_error_cap_is_per_drawer(submit, player, answer_key):
    def drop(document, drawer):
        response = submit(
            player_id=player["id"],
            question_id=answer_key.question_id(drawer),
            choice_id=answer_key.document_id(document),
        )
        return response.json()["score_delta"]

    # Different wrong documents all count against the same drawer.
    assert [drop("doc-1", "drawer-2"), drop("doc-3", "drawer-2"), drop("doc-4", "drawer-2")] == [
        -5,
        -5,
        0,
    ]
    # Another drawer has its own count.
    assert drop("doc-1", "drawer-3") == -5
    assert drop("doc-2", "drawer-2") == 10


# --- unknown values --------------------------------------------------------


def test_option_of_another_question_is_rejected(submit, player, answer_key, db_session):
    response = submit(
        player_id=player["id"],
        question_id=answer_key.question_id("trench-1"),
        choice_id=answer_key.option_id("trench-2-opt-1"),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "The choice does not belong to this question."
    assert stored_answers(db_session) == []


def test_unknown_option_is_rejected(submit, answer_key):
    response = submit(question_id=answer_key.question_id("trench-1"), choice_id=999999)
    assert response.status_code == 422
    assert response.json()["detail"] == "The choice does not belong to this question."


def test_unknown_document_is_rejected(submit, answer_key):
    response = submit(question_id=answer_key.question_id("drawer-1"), choice_id=999999)
    assert response.status_code == 422


def test_document_of_another_activity_is_rejected(
    submit, client, player, answer_key, admin_headers, db_session
):
    response = client.put(
        "/api/v1/admin/lessons/tratado-de-versalhes/activities/second-match",
        headers=admin_headers,
        json={
            "slug": "second-match",
            "kind": "match",
            "title": "Outra sala",
            "position": 5,
            "questions": [{"slug": "other-drawer", "kind": "match_drawer", "prompt": "?"}],
            "documents": [
                {"slug": "other-doc", "body": "...", "correct_question_slug": "other-drawer"}
            ],
        },
    )
    assert response.status_code == 201
    foreign_document_id = response.json()["documents"][0]["id"]

    response = submit(
        player_id=player["id"],
        question_id=answer_key.question_id("drawer-1"),
        choice_id=foreign_document_id,
    )
    assert response.status_code == 422
    assert stored_answers(db_session) == []


def test_unknown_question(submit, seeded_content):
    response = submit(question_id=999999, choice_id=1)
    assert response.status_code == 404
    assert response.json()["detail"] == "Question not found."


def test_unknown_player(submit, answer_key):
    response = submit(
        player_id=999999,
        question_id=answer_key.question_id("trench-1"),
        choice_id=answer_key.option_id("trench-1-opt-2"),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Player not found."


def test_questions_of_an_unpublished_lesson_cannot_be_probed(submit, answer_key, db_session):
    lesson = db_session.scalar(select(Lesson).where(Lesson.slug == "tratado-de-versalhes"))
    lesson.is_published = False
    db_session.flush()

    response = submit(
        question_id=answer_key.question_id("trench-1"),
        choice_id=answer_key.option_id("trench-1-opt-2"),
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"choice_id": 1},
        {"question_id": 1},
        {"question_id": 0, "choice_id": 1},
        {"question_id": 1, "choice_id": 2**31},
        {"question_id": 1, "choice_id": 1, "prior_errors": -1},
        {"question_id": 1, "choice_id": "trench-1-opt-2"},
    ],
)
def test_request_validation(client, body):
    assert client.post("/api/v1/answers", json=body).status_code == 422


# --- anonymous play --------------------------------------------------------


def test_anonymous_answer_is_judged_but_not_recorded(submit, answer_key, db_session):
    response = submit(
        question_id=answer_key.question_id("trench-1"),
        choice_id=answer_key.option_id("trench-1-opt-2"),
    )
    # 200, not 201: nothing was created.
    assert response.status_code == 200
    assert response.json() == {
        "id": None,
        "player_id": None,
        "question_id": answer_key.question_id("trench-1"),
        "choice_id": answer_key.option_id("trench-1-opt-2"),
        "is_correct": True,
        "score_delta": 10,
        "feedback": FEEDBACK_TRENCH_1,
    }
    assert stored_answers(db_session) == []


def test_anonymous_error_cap_uses_the_browsers_count(submit, answer_key, db_session):
    def wrong(prior_errors):
        response = submit(
            question_id=answer_key.question_id("drawer-2"),
            choice_id=answer_key.document_id("doc-1"),
            prior_errors=prior_errors,
        )
        assert response.status_code == 200
        assert response.json()["is_correct"] is False
        return response.json()["score_delta"]

    assert [wrong(0), wrong(1), wrong(2), wrong(3)] == [-5, -5, 0, 0]
    assert stored_answers(db_session) == []


def test_anonymous_requests_cannot_claim_a_score(submit, answer_key, db_session):
    response = submit(
        question_id=answer_key.question_id("trench-1"),
        choice_id=answer_key.option_id("trench-1-opt-1"),
        is_correct=True,
        score_delta=500,
    )
    assert response.status_code == 422
    assert db_session.scalar(select(func.count()).select_from(Answer)) == 0


# --- retries ---------------------------------------------------------------


def test_retry_of_a_recorded_attempt_is_not_recorded_twice(submit, player, answer_key, db_session):
    attempt = {
        "player_id": player["id"],
        "question_id": answer_key.question_id("trench-1"),
        "choice_id": answer_key.option_id("trench-1-opt-1"),
    }
    first = submit(**attempt)
    assert first.status_code == 201

    # The browser never saw that response and sends the attempt again.
    retry = submit(**attempt, retry={"elapsed_ms": 31_000})
    assert retry.status_code == 200
    assert retry.json() == first.json()
    assert len(stored_answers(db_session)) == 1


def test_retry_of_a_lost_attempt_is_recorded(submit, player, answer_key, db_session):
    response = submit(
        player_id=player["id"],
        question_id=answer_key.question_id("trench-1"),
        choice_id=answer_key.option_id("trench-1-opt-2"),
        retry={"elapsed_ms": 4_000},
    )
    assert response.status_code == 201
    assert response.json()["score_delta"] == 10
    assert len(stored_answers(db_session)) == 1


def test_retry_does_not_match_an_answer_the_browser_already_received(
    submit, player, answer_key, db_session
):
    attempt = {
        "player_id": player["id"],
        "question_id": answer_key.question_id("trench-1"),
        "choice_id": answer_key.option_id("trench-1-opt-1"),
    }
    acknowledged = submit(**attempt).json()

    # Same wrong option clicked again; that request was lost and is retried.
    retry = submit(
        **attempt, retry={"elapsed_ms": 2_000, "after_answer_id": acknowledged["id"]}
    )
    assert retry.status_code == 201
    assert retry.json()["id"] != acknowledged["id"]
    assert len(stored_answers(db_session)) == 2


def test_retry_does_not_match_a_different_choice(submit, player, answer_key, db_session):
    question = answer_key.question_id("trench-1")
    submit(
        player_id=player["id"],
        question_id=question,
        choice_id=answer_key.option_id("trench-1-opt-1"),
    )
    retry = submit(
        player_id=player["id"],
        question_id=question,
        choice_id=answer_key.option_id("trench-1-opt-3"),
        retry={"elapsed_ms": 2_000},
    )
    assert retry.status_code == 201
    assert len(stored_answers(db_session)) == 2


def test_retries_do_not_use_up_the_error_cap(submit, player, answer_key):
    attempt = {
        "player_id": player["id"],
        "question_id": answer_key.question_id("trench-1"),
        "choice_id": answer_key.option_id("trench-1-opt-1"),
    }
    first = submit(**attempt).json()
    for _ in range(3):
        assert submit(**attempt, retry={"elapsed_ms": 1_000}).json()["id"] == first["id"]

    after = {"after_answer_id": first["id"]}
    second = submit(**attempt, retry={"elapsed_ms": 0, **after}).json()
    assert second["score_delta"] == -5  # only the second error, still penalized
    third = submit(**attempt, retry={"elapsed_ms": 0, "after_answer_id": second["id"]}).json()
    assert third["score_delta"] == 0


def test_anonymous_retry_is_simply_judged_again(submit, answer_key, db_session):
    response = submit(
        question_id=answer_key.question_id("trench-1"),
        choice_id=answer_key.option_id("trench-1-opt-2"),
        retry={"elapsed_ms": 40_000},
    )
    assert response.status_code == 200
    assert response.json()["score_delta"] == 10
    assert stored_answers(db_session) == []


# --- concurrency -----------------------------------------------------------


def test_a_retry_waits_for_the_first_send_still_in_flight(engine):
    """Two connections, as two Lambda sandboxes would be.

    The first send has inserted its answer but not committed when the retry
    arrives. The retry must wait and then find that answer rather than insert
    a second one. Uses committed data, so it cleans the tables itself.
    """
    import threading

    from sqlalchemy import text
    from sqlalchemy.orm import Session

    from app.models import Base, Player, Question, QuestionOption
    from app.schemas.answers import AnswerCreate, AnswerRetry
    from app.seed.loader import seed_all
    from app.services import answers as answers_service

    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    first = Session(engine)
    try:
        with Session(engine) as setup:
            seed_all(setup)
            player = Player(name="Ana Souza", class_group="9º A")
            setup.add(player)
            setup.commit()
            attempt = {
                "player_id": player.id,
                "question_id": setup.scalar(
                    select(Question.id).where(Question.slug == "trench-1")
                ),
                "choice_id": setup.scalar(
                    select(QuestionOption.id).where(QuestionOption.slug == "trench-1-opt-1")
                ),
            }

        first_outcome = answers_service.submit_answer(first, AnswerCreate(**attempt))
        assert first_outcome.created

        retry_outcome = []

        def send_retry():
            with Session(engine) as second:
                retry_outcome.append(
                    answers_service.submit_answer(
                        second, AnswerCreate(**attempt, retry=AnswerRetry(elapsed_ms=30_000))
                    )
                )
                second.commit()

        thread = threading.Thread(target=send_retry)
        thread.start()
        thread.join(timeout=0.5)
        waited = thread.is_alive()

        first.commit()
        thread.join(timeout=10)
        assert not thread.is_alive()
        assert waited, "the retry should have waited for the first send"

        [outcome] = retry_outcome
        assert outcome.created is False
        assert outcome.answer_id == first_outcome.answer_id
        with Session(engine) as check:
            assert check.scalar(select(func.count()).select_from(Answer)) == 1
    finally:
        # An open transaction would block the TRUNCATE below.
        first.close()
        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
