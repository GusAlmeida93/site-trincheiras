"""The report endpoints behind the teacher's pages."""

import csv
import io

from app.models import Player


def test_class_summaries(client, results, admin_headers):
    response = client.get("/api/v1/reports/classes", headers=admin_headers)
    assert response.status_code == 200
    a, b = response.json()
    assert a == {
        "class_group": "9º A",
        "players_count": 2,
        "answers_count": 4,
        "correct_count": 2,
        "total_score": 10,
        "last_answer_at": a["last_answer_at"],
    }
    assert a["last_answer_at"] is not None
    assert (b["class_group"], b["players_count"], b["total_score"]) == ("9º B", 1, 10)


def test_a_class_with_no_answers_is_still_listed(client, db_session, results, admin_headers):
    db_session.add(Player(name="Davi Reis", class_group="9º C"))
    db_session.commit()
    c = client.get("/api/v1/reports/classes", headers=admin_headers).json()[-1]
    assert c == {
        "class_group": "9º C",
        "players_count": 1,
        "answers_count": 0,
        "correct_count": 0,
        "total_score": 0,
        "last_answer_at": None,
    }


def test_activity_summary_for_everyone(client, results, admin_headers):
    response = client.get("/api/v1/reports/activities", headers=admin_headers)
    assert response.status_code == 200
    by_slug = {a["activity_slug"]: a for a in response.json()}
    assert list(by_slug) == ["war-room", "trench-mission"]  # lesson order

    trench = by_slug["trench-mission"]
    assert trench["title"] and trench["kind"] == "quiz"
    # Ana and Bruno; the anonymous answer adds an attempt but no student.
    assert (trench["players_count"], trench["answers_count"], trench["correct_count"]) == (2, 5, 3)
    assert len(trench["questions"]) == 7
    q1 = trench["questions"][0]
    assert q1["question_slug"] == "trench-1"
    assert (q1["answers_count"], q1["correct_count"]) == (4, 2)
    # Ana answered twice but is one student; Bruno never got it right.
    assert (q1["players_count"], q1["players_correct_count"]) == (2, 1)
    # A question nobody reached is listed with zeros, not dropped.
    assert trench["questions"][4]["answers_count"] == 0
    assert trench["questions"][4]["players_count"] == 0

    assert by_slug["war-room"]["players_count"] == 1


def test_activity_summary_for_one_class(client, results, admin_headers):
    response = client.get(
        "/api/v1/reports/activities", params={"class_group": "9º B"}, headers=admin_headers
    )
    by_slug = {a["activity_slug"]: a for a in response.json()}
    assert by_slug["trench-mission"]["answers_count"] == 0
    assert by_slug["trench-mission"]["players_count"] == 0
    assert len(by_slug["trench-mission"]["questions"]) == 7
    assert by_slug["war-room"]["answers_count"] == 1
    assert by_slug["war-room"]["questions"][0]["players_correct_count"] == 1


def test_answer_rows_carry_titles_and_the_chosen_text(client, results, admin_headers):
    rows = client.get(
        f"/api/v1/reports/players/{results['ana']}/answers", headers=admin_headers
    ).json()
    assert len(rows) == 3  # the joins for labels must not multiply rows
    first = rows[0]
    assert first["activity_title"]
    assert first["question_title"] == "Trincheira 1: A Nova Fronteira"
    assert first["selected_value"] == "trench-1-opt-1"
    assert first["selected_label"] and first["selected_label"] != first["selected_value"]

    carla = client.get(
        f"/api/v1/reports/players/{results['carla']}/answers", headers=admin_headers
    ).json()
    assert carla[0]["selected_label"]  # a match answer resolves to the document text


def parse_csv(response) -> list[list[str]]:
    assert response.content.startswith(b"\xef\xbb\xbf")  # BOM, so Excel reads UTF-8
    text = response.content.decode("utf-8-sig")
    assert "\r\n" in text
    return list(csv.reader(io.StringIO(text), delimiter=";"))


def test_class_csv(client, results, admin_headers):
    response = client.get(
        "/api/v1/reports/players.csv", params={"class_group": "9º A"}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    disposition = response.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="turma-9o-a.csv"')
    assert "filename*=UTF-8''turma-9%C2%BA%20A.csv" in disposition
    assert response.headers["cache-control"] == "no-store"

    header, ana, bruno = parse_csv(response)
    assert header[:6] == ["Nome", "Turma", "Nº de recruta", "Alistamento", "Respostas", "Acertos"]
    assert header[-2:] == ["Pontuação total", "Última resposta"]
    assert len(header) == 10 and all(h.startswith("Pontos: ") for h in header[6:8])
    # war-room then trench-mission, as on the lesson page.
    assert ana[:3] == ["Ana Souza", "9º A", "TRN-000001-0001"]
    assert ana[4:9] == ["3", "2", "0", "15", "15"]
    assert bruno[:3] == ["Bruno Lima", "9º A", ""]
    assert bruno[4:9] == ["1", "0", "0", "-5", "-5"]
    # Local time, dd/mm/yyyy hh:mm.
    assert len(ana[3]) == 16 and ana[3][2] == "/" and ana[9][13] == ":"


def test_class_csv_defuses_spreadsheet_formulas(client, db_session, results, admin_headers):
    db_session.add(
        Player(name='=HYPERLINK("http://x";"clique")', class_group="9º A", recruit_number="+55")
    )
    db_session.commit()
    rows = parse_csv(
        client.get(
            "/api/v1/reports/players.csv", params={"class_group": "9º A"}, headers=admin_headers
        )
    )
    evil = rows[1]
    assert evil[0] == "'=HYPERLINK(\"http://x\";\"clique\")"
    assert evil[2] == "'+55"


def test_class_csv_needs_an_existing_class(client, results, admin_headers):
    assert (
        client.get(
            "/api/v1/reports/players.csv", params={"class_group": "9º Z"}, headers=admin_headers
        ).status_code
        == 404
    )
    assert client.get("/api/v1/reports/players.csv", headers=admin_headers).status_code == 422
