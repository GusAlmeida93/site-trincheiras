import pytest


@pytest.fixture()
def bundle(client, seeded_content):
    response = client.get("/api/v1/lessons/tratado-de-versalhes/bundle")
    assert response.status_code == 200
    return response.json()


def test_unknown_lesson_404(client, seeded_content):
    assert client.get("/api/v1/lessons/nope/bundle").status_code == 404


def test_bundle_lesson(bundle):
    assert bundle["lesson"]["slug"] == "tratado-de-versalhes"
    assert bundle["lesson"]["title"] == "O Tratado de Versalhes: Paz ou Pausa?"


def test_bundle_map_regions(bundle):
    regions = bundle["map_regions"]
    assert [r["slug"] for r in regions] == ["europe", "africa", "asia-pacific"]
    assert sum(len(r["features"]) for r in regions) == 13
    for region in regions:
        for feature in region["features"]:
            if feature["shape"] == "circle":
                assert feature["radius_m"] is not None
                assert len(feature["coordinates"]) == 2
            else:
                assert feature["radius_m"] is None
                assert len(feature["coordinates"]) >= 3
    saar = next(f for f in regions[0]["features"] if f["slug"] == "sarre")
    assert saar["radius_m"] == 80000


def test_bundle_war_room(bundle):
    war = next(a for a in bundle["activities"] if a["slug"] == "war-room")
    assert war["kind"] == "match"
    assert war["config"] == {
        "points_correct": 10,
        "points_wrong": -5,
        "max_penalized_errors": 2,
    }
    assert [q["slug"] for q in war["questions"]] == [f"drawer-{i}" for i in range(1, 6)]
    docs = war["documents"]
    assert [d["slug"] for d in docs] == ["doc-3", "doc-4", "doc-1", "doc-5", "doc-2"]
    # Bijection: doc-N pairs with drawer-N.
    assert {d["slug"]: d["correct_question_slug"] for d in docs} == {
        f"doc-{i}": f"drawer-{i}" for i in range(1, 6)
    }


def test_bundle_trench(bundle):
    trench = next(a for a in bundle["activities"] if a["slug"] == "trench-mission")
    assert trench["kind"] == "quiz"
    assert len(trench["questions"]) == 7
    for question in trench["questions"]:
        assert len(question["options"]) == 3
        assert sum(1 for o in question["options"] if o["is_correct"]) == 1
        assert question["feedback_correct"]
    first = trench["questions"][0]
    correct = next(o for o in first["options"] if o["is_correct"])
    assert correct["label"] == "França"
