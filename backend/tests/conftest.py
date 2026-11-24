import os
from collections.abc import Callable, Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Activity, Answer, Base, Player, Question
from app.seed.loader import seed_all
from app.services import accounts

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://trincheiras:trincheiras@localhost:5432/trincheiras_test",
)
# Throwaway values; they only ever exist inside the test database.
TEST_SESSION_SECRET = "test-session-secret-0123456789-abcdefghij"
TEACHER_EMAIL = "prof@escola.test"
TEACHER_PASSWORD = "senha-de-teste-123"
# What the admin pages send with every change (see app/security.py).
CSRF_HEADERS = {"X-Requested-With": "trincheiras-admin"}


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


DEFAULT_ENV = {
    "ADMIN_TOKEN": "test-token",
    "SESSION_SECRET": TEST_SESSION_SECRET,
    "APP_ENV": "test",
    "DATABASE_URL": TEST_DATABASE_URL,
    # Dev-mode asset tags keep page tests independent of a frontend build.
    "VITE_DEV_SERVER": "http://localhost:5173",
}


@pytest.fixture()
def make_app(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> Generator[Callable[..., FastAPI], None, None]:
    """Builds the app on the test transaction; keyword arguments override
    environment variables (None removes one)."""

    def build(**overrides: str | None) -> FastAPI:
        for name, value in {**DEFAULT_ENV, **overrides}.items():
            if value is None:
                monkeypatch.delenv(name, raising=False)
            else:
                monkeypatch.setenv(name, value)
        get_settings.cache_clear()

        from app.main import create_app

        app = create_app()

        def override_get_db() -> Generator[Session, None, None]:
            yield db_session

        app.dependency_overrides[get_db] = override_get_db
        return app

    yield build
    get_settings.cache_clear()


@pytest.fixture()
def app_instance(make_app: Callable[..., FastAPI]) -> FastAPI:
    return make_app()


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


@pytest.fixture()
def invite_token(db_session: Session) -> Callable[..., str]:
    """What the invite-admin ops task does; returns the token from the link."""

    def invite(email: str = TEACHER_EMAIL, **kwargs: int) -> str:
        link = accounts.invite_admin(db_session, TEST_SESSION_SECRET, email, **kwargs)
        db_session.commit()
        path, _, token = link.setup_path.partition("#")
        assert path == "/admin/definir-senha" and token
        return token

    return invite


@pytest.fixture()
def teacher(client: TestClient, invite_token: Callable[..., str]) -> dict[str, str]:
    """An invited teacher who has already chosen a password (not signed in)."""
    response = client.post(
        "/api/v1/auth/password",
        json={"token": invite_token(), "password": TEACHER_PASSWORD},
        headers=CSRF_HEADERS,
    )
    assert response.status_code == 204, response.text
    return {"email": TEACHER_EMAIL, "password": TEACHER_PASSWORD}


def sign_in(client: TestClient, email: str = TEACHER_EMAIL, password: str = TEACHER_PASSWORD):
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
        headers=CSRF_HEADERS,
    )


@pytest.fixture()
def signed_in(client: TestClient, teacher: dict[str, str]) -> TestClient:
    """The client, carrying a teacher's session cookie."""
    assert sign_in(client).status_code == 200
    return client


@pytest.fixture()
def results(db_session: Session, seeded_content: dict[str, int]) -> dict[str, int]:
    """Ana and Bruno in 9º A, Carla in 9º B, with answers written straight to
    the table (reports must not depend on how answers get submitted)."""
    rows = db_session.execute(
        select(Question.slug, Question.id).join(Activity, Question.activity_id == Activity.id)
    ).all()
    question = {slug: id_ for slug, id_ in rows}

    def enlist(name: str, class_group: str, number: str | None = None) -> Player:
        player = Player(name=name, class_group=class_group, recruit_number=number)
        db_session.add(player)
        db_session.flush()
        return player

    def answer(player: Player | None, slug: str, value: str, correct: bool, delta: int) -> None:
        db_session.add(
            Answer(
                player_id=player.id if player else None,
                question_id=question[slug],
                selected_value=value,
                is_correct=correct,
                score_delta=delta,
            )
        )

    ana = enlist("Ana Souza", "9º A", "TRN-000001-0001")
    bruno = enlist("Bruno Lima", "9º A")
    carla = enlist("Carla Dias", "9º B", "TRN-000003-0003")
    answer(ana, "trench-1", "trench-1-opt-1", False, -5)
    answer(ana, "trench-1", "trench-1-opt-2", True, 10)
    answer(ana, "trench-2", "trench-2-opt-1", True, 10)
    answer(bruno, "trench-1", "trench-1-opt-3", False, -5)
    answer(carla, "drawer-1", "doc-1", True, 10)
    answer(None, "trench-1", "trench-1-opt-2", True, 10)  # played without enlisting
    db_session.commit()
    return {"ana": ana.id, "bruno": bruno.id, "carla": carla.id}
