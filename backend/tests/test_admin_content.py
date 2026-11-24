import pytest

LESSON = "tratado-de-versalhes"

NEW_CLAUSE = {
    "kind": "clause",
    "slug": "article-999",
    "position": 7,
    "data": {
        "article_key": "999",
        "icon_svg": "<svg viewBox='0 0 24 24'></svg>",
        "number": "Artigo 999",
        "title": "Artigo de Teste",
        "quote": "Texto original.",
        "impact": "Impacto de teste.",
    },
}


def test_admin_requires_token(client, seeded_content):
    assert client.get("/api/v1/admin/lessons").status_code == 401
    assert (
        client.get(
            "/api/v1/admin/lessons", headers={"X-Admin-Token": "wrong"}
        ).status_code
        == 403
    )


def test_admin_disabled_without_configured_token(
    db_session, seeded_content, monkeypatch
):
    from collections.abc import Generator

    from fastapi.testclient import TestClient

    from app.config import get_settings
    from app.db import get_db

    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    monkeypatch.setenv("VITE_DEV_SERVER", "http://localhost:5173")
    get_settings.cache_clear()
    from app.main import create_app

    app = create_app()

    def override() -> Generator:
        yield db_session

    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/lessons", headers={"X-Admin-Token": "anything"}
            )
        assert response.status_code == 403
        assert "disabled" in response.json()["detail"]
    finally:
        get_settings.cache_clear()


def test_list_lessons(client, seeded_content, admin_headers):
    response = client.get("/api/v1/admin/lessons", headers=admin_headers)
    assert response.status_code == 200
    assert [lesson["slug"] for lesson in response.json()] == [LESSON]


def test_put_content_block_creates_then_updates(client, seeded_content, admin_headers):
    url = f"/api/v1/admin/lessons/{LESSON}/content-blocks/article-999"

    created = client.put(url, json=NEW_CLAUSE, headers=admin_headers)
    assert created.status_code == 201

    updated_payload = {**NEW_CLAUSE, "data": {**NEW_CLAUSE["data"], "title": "Editado"}}
    updated = client.put(url, json=updated_payload, headers=admin_headers)
    assert updated.status_code == 200
    assert updated.json()["data"]["title"] == "Editado"

    # The new clause shows up in the public page.
    page = client.get("/")
    assert "Editado" in page.text


def test_put_content_block_rejects_bad_data_shape(client, seeded_content, admin_headers):
    bad = {**NEW_CLAUSE, "data": {"article_key": "999"}}  # missing required fields
    response = client.put(
        f"/api/v1/admin/lessons/{LESSON}/content-blocks/article-999",
        json=bad,
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_put_slug_mismatch_rejected(client, seeded_content, admin_headers):
    response = client.put(
        f"/api/v1/admin/lessons/{LESSON}/content-blocks/other-slug",
        json=NEW_CLAUSE,
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_delete_content_block(client, seeded_content, admin_headers):
    url = f"/api/v1/admin/lessons/{LESSON}/content-blocks/article-999"
    client.put(url, json=NEW_CLAUSE, headers=admin_headers)
    assert client.delete(url, headers=admin_headers).status_code == 204
    assert client.delete(url, headers=admin_headers).status_code == 404


def test_activity_update_preserves_question_ids(client, seeded_content, admin_headers):
    bundle = client.get(f"/api/v1/lessons/{LESSON}/bundle").json()
    trench = next(a for a in bundle["activities"] if a["slug"] == "trench-mission")
    original_ids = {q["slug"]: q["id"] for q in trench["questions"]}

    payload = {
        "slug": "trench-mission",
        "kind": "quiz",
        "title": trench["title"],
        "position": 1,
        "config": trench["config"],
        "questions": [
            {
                "slug": q["slug"],
                "kind": "multiple_choice",
                "position": q["position"],
                "title": q["title"],
                "prompt": q["prompt"] + " (rev. 2)",
                "feedback_correct": q["feedback_correct"],
                "options": [
                    {
                        "slug": o["slug"],
                        "position": o["position"],
                        "label": o["label"],
                        "is_correct": o["is_correct"],
                    }
                    for o in q["options"]
                ],
            }
            for q in trench["questions"]
        ],
        "documents": [],
    }
    response = client.put(
        f"/api/v1/admin/lessons/{LESSON}/activities/trench-mission",
        json=payload,
        headers=admin_headers,
    )
    assert response.status_code == 200
    updated = response.json()
    assert {q["slug"]: q["id"] for q in updated["questions"]} == original_ids
    assert all(q["prompt"].endswith("(rev. 2)") for q in updated["questions"])


def test_removing_answered_question_conflicts(client, seeded_content, admin_headers, player):
    bundle = client.get(f"/api/v1/lessons/{LESSON}/bundle").json()
    trench = next(a for a in bundle["activities"] if a["slug"] == "trench-mission")
    first = trench["questions"][0]
    client.post(
        "/api/v1/answers",
        json={
            "player_id": player["id"],
            "question_id": first["id"],
            "selected_value": "trench-1-opt-2",
            "is_correct": True,
            "score_delta": 10,
        },
    )

    payload = {
        "slug": "trench-mission",
        "kind": "quiz",
        "title": trench["title"],
        "position": 1,
        "config": trench["config"],
        "questions": [
            {
                "slug": q["slug"],
                "kind": "multiple_choice",
                "position": q["position"],
                "title": q["title"],
                "prompt": q["prompt"],
                "feedback_correct": q["feedback_correct"],
                "options": [
                    {
                        "slug": o["slug"],
                        "position": o["position"],
                        "label": o["label"],
                        "is_correct": o["is_correct"],
                    }
                    for o in q["options"]
                ],
            }
            for q in trench["questions"]
            if q["slug"] != first["slug"]  # try to drop the answered question
        ],
        "documents": [],
    }
    response = client.put(
        f"/api/v1/admin/lessons/{LESSON}/activities/trench-mission",
        json=payload,
        headers=admin_headers,
    )
    assert response.status_code == 409


def test_delete_lesson_with_answers_conflicts(client, seeded_content, admin_headers, player):
    bundle = client.get(f"/api/v1/lessons/{LESSON}/bundle").json()
    question_id = bundle["activities"][0]["questions"][0]["id"]
    client.post(
        "/api/v1/answers",
        json={
            "player_id": player["id"],
            "question_id": question_id,
            "selected_value": "doc-1",
            "is_correct": True,
        },
    )
    response = client.delete(f"/api/v1/admin/lessons/{LESSON}", headers=admin_headers)
    assert response.status_code == 409


@pytest.mark.parametrize("kind_filter,expected", [("clause", 7), ("flip_card", 4), (None, 15)])
def test_list_content_blocks(client, seeded_content, admin_headers, kind_filter, expected):
    params = {"kind": kind_filter} if kind_filter else {}
    response = client.get(
        f"/api/v1/admin/lessons/{LESSON}/content-blocks",
        params=params,
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert len(response.json()) == expected
