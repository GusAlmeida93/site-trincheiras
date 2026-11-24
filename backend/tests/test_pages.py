from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_db

MANIFEST = Path(__file__).resolve().parents[1] / "app/static/dist/.vite/manifest.json"


def test_index_renders_seeded_content(client, seeded_content):
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    assert "O Tratado de Versalhes: Paz ou Pausa?" in html
    assert 'data-lesson-slug="tratado-de-versalhes"' in html
    # SSR content pulled from the database:
    assert "Georges Clemenceau" in html  # participant
    assert "A Cláusula de Culpa" in html  # clause title
    assert "GAVETA 05" in html  # war-room drawer
    assert 'data-intel="causas"' in html  # flip card
    assert "Trincheira 1: A Nova Fronteira" in html  # first trench question
    assert html.count("enlist-avatar-option") == 20
    # Clause icon SVG must render un-escaped:
    assert '<svg viewBox="0 0 24 24"' in html
    # Dev-mode Vite tags (VITE_DEV_SERVER set in conftest):
    assert "@vite/client" in html


def test_index_gives_no_answers_away(client, answer_key):
    html = client.get("/").text

    assert "data-doc-id=" in html  # the cards are there...
    for slug in answer_key.documents:  # ...without the slugs that pair them
        assert slug not in html
    for question in answer_key.questions.values():
        if question["feedback_correct"]:
            assert question["feedback_correct"] not in html


def test_index_503_when_not_seeded(client):
    response = client.get("/")
    assert response.status_code == 503


@pytest.mark.skipif(not MANIFEST.exists(), reason="frontend has not been built")
def test_index_emits_manifest_assets_in_prod_mode(db_session, seeded_content, monkeypatch):
    monkeypatch.delenv("VITE_DEV_SERVER", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused:unused@localhost/unused")
    get_settings.cache_clear()

    from app.main import create_app

    app = create_app()

    def override_get_db() -> Generator:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            html = client.get("/").text
        assert '<link rel="stylesheet" href="/static/dist/assets/' in html
        assert '<script type="module" src="/static/dist/assets/' in html
        assert "@vite/client" not in html
    finally:
        get_settings.cache_clear()
