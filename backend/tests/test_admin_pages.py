"""The server-rendered pages under /admin."""

import pytest

from app.models import Player

PRIVATE_PAGES = ["/admin", "/admin/", "/admin/turma?nome=9%C2%BA%20A", "/admin/alunos/1", "/admin/atividades"]


@pytest.mark.parametrize("path", PRIVATE_PAGES)
def test_private_pages_send_strangers_to_sign_in(client, results, path):
    response = client.get(path, follow_redirects=False)
    assert response.status_code == 303
    # Relative on purpose: behind CloudFront the request host is the Lambda URL.
    assert response.headers["location"] == "/admin/entrar"
    assert response.headers["cache-control"] == "no-store"
    assert "Ana Souza" not in response.text


def test_sign_in_page(client):
    response = client.get("/admin/entrar")
    assert response.status_code == 200
    html = response.text
    assert 'id="sign-in-form"' in html and 'method="post"' in html
    assert 'autocomplete="current-password"' in html
    assert "src/admin/main.ts" in html  # the admin bundle, not the lesson's
    assert "src/main.ts" not in html
    assert 'id="sign-out"' not in html
    assert 'name="robots" content="noindex, nofollow"' in html
    assert response.headers["cache-control"] == "no-store"
    # The delete confirmation must not be framed by another site.
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["content-security-policy"] == "frame-ancestors 'none'"
    assert "x-frame-options" not in client.get("/healthz").headers


def test_set_password_page_does_not_need_a_session(client):
    response = client.get("/admin/definir-senha")
    assert response.status_code == 200
    assert 'id="set-password-form"' in response.text
    assert 'minlength="10"' in response.text


def test_pages_accept_no_form_posts(client):
    # Changes go through fetch to the JSON API; a form post has nowhere to land.
    assert client.post("/admin/entrar", data={"email": "a@b.c", "password": "x"}).status_code == 405
    assert client.post("/admin/definir-senha", data={"password": "x"}).status_code == 405


def test_signed_in_teacher_skips_the_sign_in_page(signed_in):
    response = signed_in.get("/admin/entrar", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/admin"


@pytest.mark.parametrize("path", ["/admin", "/admin/"])
def test_classes_page(signed_in, results, path):
    response = signed_in.get(path, follow_redirects=False)
    assert response.status_code == 200
    html = response.text
    assert "prof@escola.test" in html and 'id="sign-out"' in html
    assert '<a href="/admin/turma?nome=9%C2%BA%20A">9º A</a>' in html
    assert '<a href="/admin/turma?nome=9%C2%BA%20B">9º B</a>' in html
    assert "(50%)" in html  # 2 of 4 answers in 9º A
    assert response.headers["cache-control"] == "no-store"


def test_classes_page_without_students(signed_in, seeded_content):
    assert "Nenhum aluno se alistou ainda." in signed_in.get("/admin").text


def test_class_page(signed_in, results):
    response = signed_in.get("/admin/turma", params={"nome": "9º A"})
    assert response.status_code == 200
    html = response.text
    assert f'<a href="/admin/alunos/{results["ana"]}">Ana Souza</a>' in html
    assert "Bruno Lima" in html and "Carla Dias" not in html
    assert 'href="/api/v1/reports/players.csv?class_group=9%C2%BA%20A"' in html
    assert f'data-delete-url="/api/v1/admin/players/{results["ana"]}"' in html
    assert 'data-delete-url="/api/v1/admin/players?class_group=9%C2%BA%20A"' in html
    assert "Serão apagados 2 aluno(s) e 4 resposta(s) desta turma." in html
    assert 'id="confirm-dialog"' in html


@pytest.mark.parametrize("params", [{"nome": "9º Z"}, {}])
def test_unknown_class_page(signed_in, results, params):
    response = signed_in.get("/admin/turma", params=params)
    assert response.status_code == 404
    assert "Turma não encontrada" in response.text


def test_player_page(signed_in, results):
    response = signed_in.get(f"/admin/alunos/{results['ana']}")
    assert response.status_code == 200
    html = response.text
    assert "Ana Souza" in html and "TRN-000001-0001" in html
    assert '<dd id="player-score">15</dd>' in html
    assert "Trincheira 1: A Nova Fronteira" in html
    assert html.count('class="tag tag-ok"') == 2 and html.count('class="tag tag-bad"') == 1
    assert "+10" in html and "-5" in html
    assert "trench-1-opt-1" not in html  # the option's text is shown, not its slug
    assert f'data-delete-url="/api/v1/admin/players/{results["ana"]}"' in html


def test_player_page_without_answers_and_unknown_player(signed_in, db_session, results):
    davi = Player(name="Davi Reis", class_group="9º A")
    db_session.add(davi)
    db_session.commit()
    assert "ainda não respondeu" in signed_in.get(f"/admin/alunos/{davi.id}").text
    assert signed_in.get("/admin/alunos/999999").status_code == 404
    assert signed_in.get("/admin/alunos/abc").status_code == 422


def test_activities_page(signed_in, results):
    response = signed_in.get("/admin/atividades")
    assert response.status_code == 200
    html = response.text
    assert "Todas as turmas" in html
    assert 'data-activity="trench-mission"' in html and 'data-activity="war-room"' in html
    assert "2 aluno(s) · 5 resposta(s)" in html
    assert '<option value="9º A" >9º A</option>' in html

    filtered = signed_in.get("/admin/atividades", params={"turma": "9º B"}).text
    assert "Turma 9º B" in filtered
    assert '<option value="9º B" selected>9º B</option>' in filtered
    assert "0 aluno(s) · 0 resposta(s)" in filtered


def test_student_typed_text_is_escaped(signed_in, db_session, results):
    evil = Player(name="<script>alert(1)</script>", class_group='9º "X"<b>')
    db_session.add(evil)
    db_session.commit()
    for path, params in (
        ("/admin", {}),
        ("/admin/turma", {"nome": evil.class_group}),
        (f"/admin/alunos/{evil.id}", {}),
        ("/admin/atividades", {"turma": evil.class_group}),
    ):
        html = signed_in.get(path, params=params).text
        assert "<script>alert(1)</script>" not in html
        assert '"X"<b>' not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in signed_in.get(
        "/admin/turma", params={"nome": evil.class_group}
    ).text
