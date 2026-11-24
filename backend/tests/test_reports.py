import pytest


@pytest.fixture()
def played_session(client, answer_key):
    """Two players in different classes with a few answers each."""
    ana = client.post(
        "/api/v1/players", json={"name": "Ana Souza", "class_group": "9º A"}
    ).json()
    bia = client.post(
        "/api/v1/players", json={"name": "Bia Lima", "class_group": "9º B"}
    ).json()

    def answer(player, question_slug, choice_id):
        response = client.post(
            "/api/v1/answers",
            json={
                "player_id": player["id"],
                "question_id": answer_key.question_id(question_slug),
                "choice_id": choice_id,
            },
        )
        assert response.status_code == 201

    # The server scores these: -5, +10, +10 for Ana and +10 for Bia.
    answer(ana, "trench-1", answer_key.option_id("trench-1-opt-1"))
    answer(ana, "trench-1", answer_key.option_id("trench-1-opt-2"))
    answer(ana, "trench-2", answer_key.option_id("trench-2-opt-1"))
    answer(bia, "drawer-1", answer_key.document_id("doc-1"))
    return {"ana": ana, "bia": bia}


def test_reports_require_admin(client, played_session):
    assert client.get("/api/v1/reports/players").status_code == 401


def test_player_score_summaries(client, played_session, admin_headers):
    response = client.get("/api/v1/reports/players", headers=admin_headers)
    assert response.status_code == 200
    by_name = {row["name"]: row for row in response.json()}
    ana = by_name["Ana Souza"]
    assert ana["answers_count"] == 3
    assert ana["correct_count"] == 2
    assert ana["total_score"] == 15
    assert ana["last_answer_at"] is not None
    bia = by_name["Bia Lima"]
    assert bia["total_score"] == 10


def test_player_score_summaries_class_filter(client, played_session, admin_headers):
    response = client.get(
        "/api/v1/reports/players",
        params={"class_group": "9º B"},
        headers=admin_headers,
    )
    names = [row["name"] for row in response.json()]
    assert names == ["Bia Lima"]


def test_player_answers_listing(client, played_session, admin_headers):
    ana = played_session["ana"]
    response = client.get(
        f"/api/v1/reports/players/{ana['id']}/answers", headers=admin_headers
    )
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 3
    assert rows[0]["question_slug"] == "trench-1"
    assert rows[0]["activity_slug"] == "trench-mission"
    assert client.get(
        "/api/v1/reports/players/999999/answers", headers=admin_headers
    ).status_code == 404


def test_answers_listing_with_filters_and_paging(client, played_session, admin_headers):
    response = client.get(
        "/api/v1/reports/answers",
        params={"activity": "trench-mission", "limit": 2, "offset": 0},
        headers=admin_headers,
    )
    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 3
    assert len(page["items"]) == 2
    assert all(row["activity_slug"] == "trench-mission" for row in page["items"])

    response = client.get(
        "/api/v1/reports/answers",
        params={"class_group": "9º B"},
        headers=admin_headers,
    )
    page = response.json()
    assert page["total"] == 1
    assert page["items"][0]["player_name"] == "Bia Lima"
