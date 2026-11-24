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

from tests.conftest import (
    CSRF_HEADERS,
    TEST_DATABASE_URL,
    TEST_SESSION_SECRET,
    ensure_database,
)

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
    monkeypatch.setenv("SESSION_SECRET", TEST_SESSION_SECRET)
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


def ops(client: TestClient, **payload: object):
    return client.post("/internal/ops", json=payload)


def test_invite_admin_end_to_end(ops_client):
    assert ops(ops_client, task="migrate").status_code == 200

    response = ops(ops_client, task="invite-admin", email="Prof@Escola.Test")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["task"] == "invite-admin"
    invite = body["invite"]
    assert invite["email"] == "prof@escola.test" and invite["created"] is True
    assert invite["expires_at"]
    path, _, token = invite["setup_path"].partition("#")
    assert path == "/admin/definir-senha" and len(token) >= 43

    listed = ops(ops_client, task="list-admins").json()["admins"]
    assert listed == [
        {
            "email": "prof@escola.test",
            "is_active": True,
            "has_password": False,
            "invite_pending": True,
            "last_login_at": None,
        }
    ]

    # The teacher opens the link, chooses a password and signs in.
    password = "senha-de-teste-123"
    assert (
        ops_client.post(
            "/api/v1/auth/password",
            json={"token": token, "password": password},
            headers=CSRF_HEADERS,
        ).status_code
        == 204
    )
    signed = ops_client.post(
        "/api/v1/auth/login",
        json={"email": "prof@escola.test", "password": password},
        headers=CSRF_HEADERS,
    )
    assert signed.status_code == 200
    assert ops_client.get("/api/v1/reports/classes").status_code == 200

    # Inviting again is the password reset: same account, a new link.
    again = ops(ops_client, task="invite-admin", email="prof@escola.test", expires_in_hours=1)
    assert again.json()["invite"]["created"] is False
    assert again.json()["invite"]["setup_path"] != invite["setup_path"]
    admin = ops(ops_client, task="list-admins").json()["admins"][0]
    assert admin["has_password"] is True and admin["invite_pending"] is True
    assert admin["last_login_at"] is not None

    # Deactivating shuts the account and its sessions at once.
    assert ops(ops_client, task="deactivate-admin", email="prof@escola.test").json() == {
        "task": "deactivate-admin",
        "deactivated": True,
    }
    assert ops_client.get("/api/v1/reports/classes").status_code == 401
    admin = ops(ops_client, task="list-admins").json()["admins"][0]
    assert admin == {**admin, "is_active": False, "has_password": False, "invite_pending": False}
    assert (
        ops(ops_client, task="deactivate-admin", email="ninguem@escola.test").json()["deactivated"]
        is False
    )


def test_invite_from_the_command_line(ops_client, capsys: pytest.CaptureFixture[str]):
    from app import invite_admin

    assert ops(ops_client, task="migrate").status_code == 200

    assert invite_admin.main(["Prof@Escola.Test", "--hours", "2"]) == 0
    printed = capsys.readouterr().out
    assert "Created prof@escola.test." in printed
    token = printed.split("/admin/definir-senha#")[1].split()[0]
    assert (
        ops_client.post(
            "/api/v1/auth/password",
            json={"token": token, "password": "senha-de-teste-123"},
            headers=CSRF_HEADERS,
        ).status_code
        == 204
    )

    assert invite_admin.main(["prof@escola.test"]) == 0
    assert "Re-invited prof@escola.test." in capsys.readouterr().out

    with pytest.raises(SystemExit) as bad_email:
        invite_admin.main(["sem-arroba"])
    assert bad_email.value.code == 2


def test_command_line_invite_needs_the_secret(ops_client, monkeypatch: pytest.MonkeyPatch):
    from app import invite_admin

    monkeypatch.delenv("SESSION_SECRET")
    get_settings.cache_clear()
    with pytest.raises(SystemExit) as disabled:
        invite_admin.main(["prof@escola.test"])
    assert disabled.value.code == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"task": "invite-admin"},
        {"task": "invite-admin", "email": ""},
        {"task": "invite-admin", "email": "sem-arroba"},
        {"task": "invite-admin", "email": "a@b.c", "expires_in_hours": 0},
        {"task": "invite-admin", "email": "a@b.c", "expires_in_hours": 169},
        {"task": "deactivate-admin"},
    ],
)
def test_account_tasks_validate_their_input(ops_client, payload):
    assert ops_client.post("/internal/ops", json=payload).status_code == 422


def test_invite_is_refused_without_the_secret(ops_client, monkeypatch: pytest.MonkeyPatch):
    assert ops(ops_client, task="migrate").status_code == 200
    monkeypatch.delenv("SESSION_SECRET")
    get_settings.cache_clear()
    response = ops(ops_client, task="invite-admin", email="prof@escola.test")
    assert response.status_code == 503
    assert "SESSION_SECRET" in response.json()["detail"]
    assert ops(ops_client, task="list-admins").json()["admins"] == []


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
