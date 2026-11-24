"""Deleting students and classes."""

from sqlalchemy import func, select

from app.models import Answer, Player

from tests.conftest import CSRF_HEADERS


def counts(db_session) -> tuple[int, int]:
    return (
        db_session.scalar(select(func.count()).select_from(Player)),
        db_session.scalar(select(func.count()).select_from(Answer)),
    )


def test_delete_a_student_and_their_answers(client, db_session, results, admin_headers):
    assert counts(db_session) == (3, 6)

    response = client.delete(f"/api/v1/admin/players/{results['ana']}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == {"players_deleted": 1, "answers_deleted": 3}

    # Nothing of Ana is left, and nobody else lost anything: not Bruno, not
    # Carla, not the answer given without enlisting.
    assert counts(db_session) == (2, 3)
    assert db_session.scalar(select(Player.id).where(Player.id == results["ana"])) is None
    assert (
        db_session.scalar(
            select(func.count()).select_from(Answer).where(Answer.player_id == results["ana"])
        )
        == 0
    )
    assert db_session.scalar(
        select(func.count()).select_from(Answer).where(Answer.player_id.is_(None))
    ) == 1

    names = [row["name"] for row in client.get("/api/v1/reports/players", headers=admin_headers).json()]
    assert names == ["Bruno Lima", "Carla Dias"]
    assert (
        client.delete(f"/api/v1/admin/players/{results['ana']}", headers=admin_headers).status_code
        == 404
    )


def test_delete_a_student_without_answers(client, db_session, admin_headers, player):
    response = client.delete(f"/api/v1/admin/players/{player['id']}", headers=admin_headers)
    assert response.json() == {"players_deleted": 1, "answers_deleted": 0}


def test_delete_a_class(client, db_session, results, admin_headers):
    response = client.delete(
        "/api/v1/admin/players", params={"class_group": "9º A"}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json() == {"players_deleted": 2, "answers_deleted": 4}

    assert counts(db_session) == (1, 2)  # Carla and her answer; the anonymous answer
    classes = client.get("/api/v1/reports/classes", headers=admin_headers).json()
    assert [c["class_group"] for c in classes] == ["9º B"]

    again = client.delete(
        "/api/v1/admin/players", params={"class_group": "9º A"}, headers=admin_headers
    )
    assert again.status_code == 404


def test_class_name_must_match_exactly(client, db_session, results, admin_headers):
    for name in ("9º", "9º a", "9", "%"):
        response = client.delete(
            "/api/v1/admin/players", params={"class_group": name}, headers=admin_headers
        )
        assert response.status_code == 404
    assert counts(db_session) == (3, 6)


def test_there_is_no_delete_everything(client, db_session, results, admin_headers):
    assert client.delete("/api/v1/admin/players", headers=admin_headers).status_code == 422
    assert (
        client.delete(
            "/api/v1/admin/players", params={"class_group": ""}, headers=admin_headers
        ).status_code
        == 422
    )
    assert counts(db_session) == (3, 6)


def test_a_signed_in_teacher_can_delete(signed_in, db_session, results):
    # Without the custom header the cookie alone changes nothing.
    assert signed_in.delete(f"/api/v1/admin/players/{results['bruno']}").status_code == 403
    assert counts(db_session) == (3, 6)

    response = signed_in.delete(
        f"/api/v1/admin/players/{results['bruno']}", headers=CSRF_HEADERS
    )
    assert response.status_code == 200
    assert response.json() == {"players_deleted": 1, "answers_deleted": 1}

    response = signed_in.delete(
        "/api/v1/admin/players", params={"class_group": "9º B"}, headers=CSRF_HEADERS
    )
    assert response.json() == {"players_deleted": 1, "answers_deleted": 1}
    assert counts(db_session) == (1, 4)


def test_deleting_frees_the_questions_for_content_edits(
    client, db_session, seeded_content, admin_headers, player
):
    """Content cannot drop a question that has answers; deleting the students
    who gave them is the way out, so it must really remove the answers."""
    bundle = client.get("/api/v1/lessons/tratado-de-versalhes/bundle").json()
    question = bundle["activities"][0]["questions"][0]
    db_session.add(
        Answer(
            player_id=player["id"],
            question_id=question["id"],
            selected_value="x",
            is_correct=False,
            score_delta=0,
        )
    )
    db_session.commit()
    assert (
        client.delete(
            "/api/v1/admin/lessons/tratado-de-versalhes", headers=admin_headers
        ).status_code
        == 409
    )
    client.delete(f"/api/v1/admin/players/{player['id']}", headers=admin_headers)
    assert (
        client.delete(
            "/api/v1/admin/lessons/tratado-de-versalhes", headers=admin_headers
        ).status_code
        == 204
    )
