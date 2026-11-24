import os
from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Base
from app.seed.loader import seed_all

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://trincheiras:trincheiras@localhost:5432/trincheiras_test",
)


def ensure_database(url: str) -> None:
    """Create the database if missing (connects to the maintenance DB)."""
    base, _, dbname = url.rpartition("/")
    admin = create_engine(f"{base}/postgres", isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            exists = conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": dbname},
            )
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{dbname}"'))
    finally:
        admin.dispose()


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    ensure_database(TEST_DATABASE_URL)
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(engine: Engine) -> Generator[Session, None, None]:
    # Outer transaction rolled back after every test; commits inside request
    # handlers become savepoints, so tests stay isolated without truncation.
    with engine.connect() as conn:
        outer = conn.begin()
        session = Session(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            session.close()
            outer.rollback()


@pytest.fixture()
def app_instance(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> Generator[FastAPI, None, None]:
    monkeypatch.setenv("ADMIN_TOKEN", "test-token")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    # Dev-mode asset tags keep page tests independent of a frontend build.
    monkeypatch.setenv("VITE_DEV_SERVER", "http://localhost:5173")
    get_settings.cache_clear()

    from app.main import create_app

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield app
    get_settings.cache_clear()


@pytest.fixture()
def client(app_instance: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(app_instance) as test_client:
        yield test_client


@pytest.fixture()
def admin_headers() -> dict[str, str]:
    return {"X-Admin-Token": "test-token"}


@pytest.fixture()
def seeded_content(db_session: Session) -> dict[str, int]:
    return seed_all(db_session)


@pytest.fixture()
def player(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/players",
        json={"name": "Ana Carolina Souza", "class_group": "9º A"},
    )
    assert response.status_code == 201
    return response.json()


class AnswerKey:
    """Ids and right answers of the seeded activities, read through the admin API.

    The public bundle carries no slugs of choices and no answers, so tests
    that need "the option trench-1-opt-2" resolve it here.
    """

    def __init__(self, activities: list[dict]) -> None:
        self.activities = {a["slug"]: a for a in activities}
        self.questions = {q["slug"]: q for a in activities for q in a["questions"]}
        self.options = {
            o["slug"]: o for q in self.questions.values() for o in q["options"]
        }
        self.documents = {d["slug"]: d for a in activities for d in a["documents"]}

    def question_id(self, slug: str) -> int:
        return self.questions[slug]["id"]

    def option_id(self, slug: str) -> int:
        return self.options[slug]["id"]

    def document_id(self, slug: str) -> int:
        return self.documents[slug]["id"]


@pytest.fixture()
def answer_key(
    client: TestClient, seeded_content: dict[str, int], admin_headers: dict[str, str]
) -> AnswerKey:
    response = client.get(
        "/api/v1/admin/lessons/tratado-de-versalhes/activities", headers=admin_headers
    )
    assert response.status_code == 200
    return AnswerKey(response.json())
