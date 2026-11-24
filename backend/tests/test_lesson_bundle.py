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
    assert [q["slug"] for q in war["questions"]] == [f"drawer-{i}" for i in range(1, 6)]
    docs = war["documents"]
    assert len(docs) == 5
    assert [d["position"] for d in docs] == [0, 1, 2, 3, 4]
    assert docs[2]["body"].startswith("Wilson defendia paz negociada")
    assert set(docs[0]) == {"id", "position", "body"}


def test_bundle_trench(bundle):
    trench = next(a for a in bundle["activities"] if a["slug"] == "trench-mission")
    assert trench["kind"] == "quiz"
    assert len(trench["questions"]) == 7
    for question in trench["questions"]:
        assert set(question) == {
            "id",
            "slug",
            "kind",
            "position",
            "title",
            "prompt",
            "options",
        }
        assert len(question["options"]) == 3
        for option in question["options"]:
            assert set(option) == {"id", "position", "label"}
    assert [o["label"] for o in trench["questions"][0]["options"]] == [
        "Polônia",
        "França",
        "Áustria",
    ]


# --- the bundle must not give the answers away -------------------------------


def _keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _keys(item)


def test_bundle_has_no_answer_fields(bundle):
    keys = set(_keys(bundle["activities"]))
    assert keys.isdisjoint(
        {"is_correct", "correct_question_slug", "correct_question_id", "feedback_correct", "config"}
    )


def test_bundle_text_reveals_no_answers(client, answer_key):
    text = client.get("/api/v1/lessons/tratado-de-versalhes/bundle").text

    # Slugs of choices are author-facing names: in the seed, doc-N belongs in
    # drawer-N, so a document slug alone would give its drawer away.
    for slug in [*answer_key.documents, *answer_key.options]:
        assert f'"{slug}"' not in text
    # Feedback texts restate the right answer.
    for question in answer_key.questions.values():
        if question["feedback_correct"]:
            assert question["feedback_correct"] not in text


def test_bundle_ids_do_not_pair_documents_with_drawers(bundle, answer_key):
    # Sorting documents and drawers by id (or by position) must not line the
    # right pairs up.
    war = next(a for a in bundle["activities"] if a["slug"] == "war-room")
    drawer_ids = sorted(q["id"] for q in war["questions"])
    slug_by_id = {q["id"]: q["slug"] for q in war["questions"]}
    correct_drawer = {
        d["id"]: d["correct_question_slug"] for d in answer_key.documents.values()
    }
    for key in ("id", "position"):
        documents = sorted(war["documents"], key=lambda d: d[key])
        lined_up = [
            correct_drawer[doc["id"]] == slug_by_id[drawer_id]
            for doc, drawer_id in zip(documents, drawer_ids)
        ]
        assert not any(lined_up)


def test_admin_activities_keep_the_answer_key(client, seeded_content, admin_headers):
    url = "/api/v1/admin/lessons/tratado-de-versalhes/activities"
    assert client.get(url).status_code == 401

    response = client.get(url, headers=admin_headers)
    assert response.status_code == 200
    activities = {a["slug"]: a for a in response.json()}

    war = activities["war-room"]
    assert war["config"] == {
        "points_correct": 10,
        "points_wrong": -5,
        "max_penalized_errors": 2,
    }
    assert [d["slug"] for d in war["documents"]] == ["doc-3", "doc-4", "doc-1", "doc-5", "doc-2"]
    # Bijection: doc-N pairs with drawer-N.
    assert {d["slug"]: d["correct_question_slug"] for d in war["documents"]} == {
        f"doc-{i}": f"drawer-{i}" for i in range(1, 6)
    }

    trench = activities["trench-mission"]
    for question in trench["questions"]:
        assert sum(1 for o in question["options"] if o["is_correct"]) == 1
        assert question["feedback_correct"]
    correct = next(o for o in trench["questions"][0]["options"] if o["is_correct"])
    assert correct["label"] == "França"

    assert client.get(
        "/api/v1/admin/lessons/nope/activities", headers=admin_headers
    ).status_code == 404
