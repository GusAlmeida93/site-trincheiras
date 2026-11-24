"""The ops endpoint exists only on the ops Lambda (OPS_MODE=true)."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import NullPool, QueuePool

from app import db as db_module
from app.config import Settings, get_settings
from app.db import build_engine

from tests.conftest import TEST_DATABASE_URL, ensure_database

OPS_DB_URL = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/trincheiras_ops_test"


def test_ops_endpoint_is_absent_by_default(client):
    response = client.post("/internal/ops", json={"task": "status"})
    assert response.status_code == 404


@pytest.fixture()
def ops_client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    ensure_database(OPS_DB_URL)
    engine = create_engine(OPS_DB_URL)
    with engine.connect() as conn:
        conn.exec_driver_sql("DROP SCHEMA public CASCADE")
        conn.exec_driver_sql("CREATE SCHEMA public")
        conn.commit()
    engine.dispose()

    monkeypatch.setenv("DATABASE_URL", OPS_DB_URL)
    monkeypatch.setenv("OPS_MODE", "true")
    monkeypatch.setenv("DB_POOL", "false")
    monkeypatch.setenv("VITE_DEV_SERVER", "http://localhost:5173")
    monkeypatch.setattr(db_module, "_engine", None)
    monkeypatch.setattr(db_module, "_session_factory", None)
    get_settings.cache_clear()

    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client

    db_module.get_engine().dispose()
    get_settings.cache_clear()


def test_migrate_and_seed_from_an_empty_database(ops_client):
    response = ops_client.post("/internal/ops", json={"task": "migrate-and-seed"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["migrated"] is True
    assert body["seeded"]["lessons"] == 1
    assert body["status"]["revision"]
    assert body["status"]["lessons"] == 1
    assert body["status"]["players"] == 0

    # Both steps are idempotent: a second deploy changes nothing.
    again = ops_client.post("/internal/ops", json={"task": "migrate-and-seed"})
    assert again.status_code == 200, again.text
    assert again.json()["status"] == body["status"]

    # The page renders from what the ops task wrote.
    assert ops_client.get("/").status_code == 200


def test_unknown_task_is_rejected(ops_client):
    assert ops_client.post("/internal/ops", json={"task": "drop"}).status_code == 422


def test_pool_is_disabled_on_request():
    pooled = build_engine(Settings(database_url=TEST_DATABASE_URL))
    unpooled = build_engine(Settings(database_url=TEST_DATABASE_URL, db_pool=False))
    assert isinstance(pooled.pool, QueuePool)
    assert isinstance(unpooled.pool, NullPool)


def test_connect_retries_until_the_database_answers(monkeypatch: pytest.MonkeyPatch):
    engine = build_engine(
        Settings(database_url=TEST_DATABASE_URL, db_pool=False, db_connect_retry_seconds=30)
    )
    real_connect = engine.dialect.connect
    calls = {"count": 0}

    def flaky_connect(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] < 3:
            raise engine.dialect.loaded_dbapi.OperationalError("database is resuming")
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(engine.dialect, "connect", flaky_connect)
    monkeypatch.setattr(db_module, "_pause", lambda _seconds: None)

    with engine.connect() as conn:
        assert conn.scalar(text("SELECT 1")) == 1
    assert calls["count"] == 3


def test_connect_gives_up_when_the_retry_budget_is_spent(monkeypatch: pytest.MonkeyPatch):
    engine = build_engine(
        Settings(
            database_url="postgresql+psycopg://nobody:nothing@127.0.0.1:1/none",
            db_pool=False,
            db_connect_timeout=1,
            db_connect_retry_seconds=1,
        )
    )
    pauses: list[float] = []
    monkeypatch.setattr(db_module, "_pause", pauses.append)

    with pytest.raises(OperationalError):
        engine.connect()
    assert pauses, "expected at least one retry before giving up"
