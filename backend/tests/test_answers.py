import pytest


@pytest.fixture()
def question_id(client, seeded_content):
    bundle = client.get("/api/v1/lessons/tratado-de-versalhes/bundle").json()
    trench = next(a for a in bundle["activities"] if a["slug"] == "trench-mission")
    return trench["questions"][0]["id"]


def test_record_answer_with_player(client, player, question_id):
    response = client.post(
        "/api/v1/answers",
        json={
            "player_id": player["id"],
            "question_id": question_id,
            "selected_value": "trench-1-opt-2",
            "is_correct": True,
            "score_delta": 10,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["player_id"] == player["id"]
    assert body["question_id"] == question_id
    assert body["is_correct"] is True
    assert body["score_delta"] == 10


def test_record_answer_anonymous(client, question_id):
    response = client.post(
        "/api/v1/answers",
        json={
            "question_id": question_id,
            "selected_value": "trench-1-opt-1",
            "is_correct": False,
            "score_delta": -5,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["player_id"] is None
    assert body["score_delta"] == -5


def test_record_answer_score_delta_defaults_to_zero(client, question_id):
    response = client.post(
        "/api/v1/answers",
        json={
            "question_id": question_id,
            "selected_value": "trench-1-opt-1",
            "is_correct": False,
        },
    )
    assert response.status_code == 201
    assert response.json()["score_delta"] == 0


def test_record_answer_unknown_question(client, seeded_content):
    response = client.post(
        "/api/v1/answers",
        json={"question_id": 999999, "selected_value": "x", "is_correct": False},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Question not found."


def test_record_answer_unknown_player(client, question_id):
    response = client.post(
        "/api/v1/answers",
        json={
            "player_id": 999999,
            "question_id": question_id,
            "selected_value": "x",
            "is_correct": False,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Player not found."


def test_record_answer_validation(client):
    assert (
        client.post(
            "/api/v1/answers", json={"selected_value": "x", "is_correct": True}
        ).status_code
        == 422
    )
