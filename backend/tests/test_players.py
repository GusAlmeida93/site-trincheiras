import pytest


def test_create_player(client):
    response = client.post(
        "/api/v1/players",
        json={
            "name": "Ana Carolina Souza",
            "class_group": "9º A",
            "recruit_number": "TRN-240715-0042",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["name"] == "Ana Carolina Souza"
    assert body["class_group"] == "9º A"
    assert body["recruit_number"] == "TRN-240715-0042"
    assert body["created_at"]


def test_create_player_without_recruit_number(client):
    response = client.post(
        "/api/v1/players", json={"name": "João Silva", "class_group": "9º B"}
    )
    assert response.status_code == 201
    assert response.json()["recruit_number"] is None


def test_create_player_normalizes_whitespace(client):
    response = client.post(
        "/api/v1/players", json={"name": "  Ana   Souza  ", "class_group": " 9º  A "}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Ana Souza"
    assert body["class_group"] == "9º A"


@pytest.mark.parametrize(
    "payload",
    [
        {"class_group": "9º A"},  # missing name
        {"name": "Ana"},  # missing class_group
        {"name": "   ", "class_group": "9º A"},  # blank name
        {"name": "Ana", "class_group": ""},  # blank class_group
    ],
)
def test_create_player_validation(client, payload):
    assert client.post("/api/v1/players", json=payload).status_code == 422
