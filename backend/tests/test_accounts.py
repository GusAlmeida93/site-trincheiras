"""Teacher accounts: invite -> set password -> sign in -> sign out."""

from datetime import timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.config import Settings
from app.models import AdminSession, AdminUser, LoginThrottle
from app.services import accounts

from tests.conftest import (
    CSRF_HEADERS,
    TEACHER_EMAIL,
    TEACHER_PASSWORD,
    TEST_SESSION_SECRET,
    sign_in,
)

COOKIE = "trincheiras_admin"
OTHER_PASSWORD = "outra-senha-de-teste-456"


def set_password(client, token, password=TEACHER_PASSWORD):
    return client.post(
        "/api/v1/auth/password",
        json={"token": token, "password": password},
        headers=CSRF_HEADERS,
    )


def the_user(db_session, email=TEACHER_EMAIL) -> AdminUser:
    return db_session.scalar(select(AdminUser).where(AdminUser.email == email))


# --- invite and set password -------------------------------------------------


def test_invite_creates_an_account_that_cannot_sign_in_yet(client, db_session, invite_token):
    token = invite_token("  Prof@Escola.TEST ")

    user = the_user(db_session)
    assert user.email == TEACHER_EMAIL  # normalized
    assert user.is_active and user.password_hash is None
    # Only a keyed digest of the link is stored.
    assert user.setup_token_hash != token and len(user.setup_token_hash) == 64
    assert user.setup_token_hash == accounts.token_digest(TEST_SESSION_SECRET, "setup", token)
    assert user.setup_token_expires_at > accounts.now() + timedelta(hours=47)

    assert sign_in(client, password="").status_code == 422
    assert sign_in(client, password="qualquer-coisa").status_code == 401


def test_setting_the_password_enables_sign_in(client, db_session, invite_token):
    assert set_password(client, invite_token()).status_code == 204

    user = the_user(db_session)
    assert user.password_hash.startswith("$argon2id$")
    assert TEACHER_PASSWORD not in user.password_hash
    assert user.setup_token_hash is None and user.setup_token_expires_at is None

    response = sign_in(client)
    assert response.status_code == 200
    assert response.json()["email"] == TEACHER_EMAIL
    assert client.get("/api/v1/auth/session").json()["email"] == TEACHER_EMAIL


def test_a_setup_link_works_only_once(client, invite_token):
    token = invite_token()
    assert set_password(client, token).status_code == 204
    again = set_password(client, token, OTHER_PASSWORD)
    assert again.status_code == 400
    assert sign_in(client, password=OTHER_PASSWORD).status_code == 401
    assert sign_in(client).status_code == 200


def test_an_expired_setup_link_is_refused(client, db_session, invite_token):
    token = invite_token(expires_in_hours=1)
    user = the_user(db_session)
    user.setup_token_expires_at = accounts.now() - timedelta(seconds=1)
    db_session.commit()

    assert set_password(client, token).status_code == 400
    assert the_user(db_session).password_hash is None


def test_unknown_token_and_weak_password_are_refused(client, db_session, invite_token):
    token = invite_token()
    assert set_password(client, "not-the-token").status_code == 400
    assert set_password(client, token, "curta").status_code == 422
    assert the_user(db_session).password_hash is None
    # The failed tries did not burn the link.
    assert set_password(client, token).status_code == 204


def test_reinviting_replaces_the_link_and_resets_the_password(
    client, db_session, teacher, invite_token
):
    assert sign_in(client).status_code == 200
    old_cookie = client.cookies.get(COOKIE)

    first = invite_token()
    second = invite_token()
    assert db_session.scalar(select(func.count()).select_from(AdminUser)) == 1
    # Until the new link is used, nothing changes for the teacher.
    assert client.get("/api/v1/auth/session").status_code == 200
    assert set_password(client, first, OTHER_PASSWORD).status_code == 400

    assert set_password(client, second, OTHER_PASSWORD).status_code == 204
    # A new password signs out every browser...
    client.cookies.set(COOKIE, old_cookie)
    assert client.get("/api/v1/auth/session").status_code == 401
    # ...and replaces the old one.
    assert sign_in(client).status_code == 401
    assert sign_in(client, password=OTHER_PASSWORD).status_code == 200


def test_setting_a_password_lifts_a_lock_out(client, teacher, invite_token):
    for _ in range(accounts.LOGIN_MAX_FAILURES):
        assert sign_in(client, password="errada-errada").status_code == 401
    assert sign_in(client).status_code == 429

    assert set_password(client, invite_token(), OTHER_PASSWORD).status_code == 204
    assert sign_in(client, password=OTHER_PASSWORD).status_code == 200


# --- sign in -----------------------------------------------------------------


def test_sign_in_sets_a_locked_down_cookie(client, db_session, teacher):
    response = sign_in(client, email="PROF@escola.test")
    assert response.status_code == 200

    cookie = response.headers["set-cookie"]
    name, _, rest = cookie.partition("=")
    value = rest.split(";")[0]
    attributes = {part.strip().lower() for part in rest.split(";")[1:]}
    assert name == COOKIE
    assert {"httponly", "samesite=lax", "path=/", "max-age=43200"} <= attributes
    assert "secure" not in attributes  # http://localhost in dev and e2e
    assert not any(a.startswith("domain") for a in attributes)

    # The cookie value itself is not in the database, only its keyed digest.
    session = db_session.scalar(select(AdminSession))
    assert session.token_hash == accounts.token_digest(TEST_SESSION_SECRET, "session", value)
    assert session.token_hash != value
    assert response.headers["cache-control"] == "no-store"
    assert the_user(db_session).last_login_at is not None


def test_cookie_is_secure_and_host_bound_outside_local_development(
    make_app, invite_token
):
    from fastapi.testclient import TestClient

    with TestClient(make_app(APP_ENV="prod")) as client:
        assert set_password(client, invite_token()).status_code == 204
        cookie = sign_in(client).headers["set-cookie"]
    name, _, rest = cookie.partition("=")
    attributes = {part.strip().lower() for part in rest.split(";")[1:]}
    assert name == "__Host-trincheiras_admin"
    assert {"secure", "httponly", "samesite=lax", "path=/"} <= attributes
    assert not any(a.startswith("domain") for a in attributes)


@pytest.mark.parametrize(
    "email, password",
    [
        (TEACHER_EMAIL, "senha-errada-123"),
        ("ninguem@escola.test", TEACHER_PASSWORD),
        ("isto nao e um email", TEACHER_PASSWORD),
    ],
)
def test_bad_credentials_get_the_same_answer(client, teacher, email, password):
    response = sign_in(client, email=email, password=password)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid e-mail or password."
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize("path", ["login", "logout", "password"])
def test_auth_changes_need_the_custom_header(client, teacher, path):
    body = {"email": TEACHER_EMAIL, "password": TEACHER_PASSWORD, "token": "x" * 43}
    assert client.post(f"/api/v1/auth/{path}", json=body).status_code == 403
    wrong = {"X-Requested-With": "XMLHttpRequest"}
    assert client.post(f"/api/v1/auth/{path}", json=body, headers=wrong).status_code == 403


def test_deactivated_account_is_shut_out(client, db_session, signed_in):
    assert accounts.deactivate_admin(db_session, TEACHER_EMAIL) is True
    db_session.commit()

    assert signed_in.get("/api/v1/auth/session").status_code == 401
    assert signed_in.get("/api/v1/reports/players").status_code == 401
    assert sign_in(client).status_code == 401
    assert accounts.deactivate_admin(db_session, "ninguem@escola.test") is False


def test_reinviting_a_deactivated_account_needs_a_new_password(
    client, db_session, teacher, invite_token
):
    accounts.deactivate_admin(db_session, TEACHER_EMAIL)
    db_session.commit()
    token = invite_token()
    # The old password must not come back to life with the account.
    assert sign_in(client).status_code == 401
    assert set_password(client, token, OTHER_PASSWORD).status_code == 204
    assert sign_in(client, password=OTHER_PASSWORD).status_code == 200


# --- throttling --------------------------------------------------------------


def fail(client, email=TEACHER_EMAIL, times=1):
    for _ in range(times):
        assert sign_in(client, email=email, password="errada-errada").status_code == 401


def test_sign_in_is_throttled_after_repeated_failures(client, db_session, teacher):
    fail(client, times=accounts.LOGIN_MAX_FAILURES)

    # Locked: even the right password is refused, and nothing is counted.
    locked = sign_in(client)
    assert locked.status_code == 429
    assert 0 < int(locked.headers["retry-after"]) <= accounts.LOGIN_WINDOW.total_seconds()
    assert "set-cookie" not in locked.headers
    assert db_session.scalar(select(LoginThrottle.failures)) == accounts.LOGIN_MAX_FAILURES

    # The counter lives in the database, per e-mail: another account is unaffected.
    assert sign_in(client, email="outra@escola.test").status_code == 401

    # When the window has passed, signing in works again.
    throttle = db_session.get(LoginThrottle, TEACHER_EMAIL)
    throttle.window_started_at = accounts.now() - accounts.LOGIN_WINDOW - timedelta(seconds=1)
    db_session.commit()
    assert sign_in(client).status_code == 200
    assert db_session.get(LoginThrottle, TEACHER_EMAIL, populate_existing=True) is None


def test_unknown_emails_are_throttled_too(client, teacher):
    # Otherwise a 429 would reveal which e-mails have an account.
    fail(client, email="ninguem@escola.test", times=accounts.LOGIN_MAX_FAILURES)
    assert sign_in(client, email="ninguem@escola.test").status_code == 429


def test_a_successful_sign_in_resets_the_counter(client, teacher):
    fail(client, times=accounts.LOGIN_MAX_FAILURES - 1)
    assert sign_in(client).status_code == 200
    fail(client, times=accounts.LOGIN_MAX_FAILURES - 1)
    assert sign_in(client).status_code == 200


def test_a_finished_window_starts_a_new_count(client, db_session, teacher):
    fail(client, times=accounts.LOGIN_MAX_FAILURES - 1)
    throttle = db_session.get(LoginThrottle, TEACHER_EMAIL)
    throttle.window_started_at = accounts.now() - accounts.LOGIN_WINDOW - timedelta(seconds=1)
    db_session.commit()

    fail(client)
    assert (
        db_session.scalar(
            select(LoginThrottle.failures).where(LoginThrottle.key == TEACHER_EMAIL)
        )
        == 1
    )
    assert sign_in(client).status_code == 200


# --- sign out and expiry -----------------------------------------------------


def test_sign_out_ends_the_session_on_the_server(client, db_session, signed_in):
    cookie = signed_in.cookies.get(COOKIE)
    assert signed_in.get("/api/v1/reports/players").status_code == 200

    response = signed_in.post("/api/v1/auth/logout", json={}, headers=CSRF_HEADERS)
    assert response.status_code == 204
    assert f"{COOKIE}=" in response.headers["set-cookie"]
    assert "max-age=0" in response.headers["set-cookie"].lower()
    assert db_session.scalar(select(func.count()).select_from(AdminSession)) == 0

    # A copy of the cookie taken before signing out is worthless now.
    client.cookies.set(COOKIE, cookie)
    assert client.get("/api/v1/auth/session").status_code == 401
    assert client.get("/api/v1/reports/players").status_code == 401
    # Signing out twice is harmless.
    assert client.post("/api/v1/auth/logout", json={}, headers=CSRF_HEADERS).status_code == 204


def test_sign_out_only_ends_that_browser(client, db_session, signed_in):
    first = signed_in.cookies.get(COOKIE)
    signed_in.cookies.clear()
    assert sign_in(signed_in).status_code == 200  # a second browser
    assert signed_in.post("/api/v1/auth/logout", json={}, headers=CSRF_HEADERS).status_code == 204

    signed_in.cookies.set(COOKIE, first)
    assert signed_in.get("/api/v1/auth/session").status_code == 200


def test_a_session_expires(client, db_session, signed_in):
    assert signed_in.get("/api/v1/auth/session").status_code == 200
    session = db_session.scalar(select(AdminSession))
    assert session.expires_at - session.created_at < timedelta(hours=12, minutes=1)
    session.expires_at = accounts.now() - timedelta(seconds=1)
    db_session.commit()

    assert signed_in.get("/api/v1/auth/session").status_code == 401
    assert signed_in.get("/api/v1/reports/players").status_code == 401
    assert signed_in.get("/admin", follow_redirects=False).status_code == 303

    # The next sign-in sweeps expired rows away.
    assert sign_in(signed_in).status_code == 200
    assert db_session.scalar(select(func.count()).select_from(AdminSession)) == 1


def test_a_forged_cookie_is_not_a_session(client, teacher):
    client.cookies.set(COOKIE, "x" * 43)
    assert client.get("/api/v1/auth/session").status_code == 401
    assert client.get("/api/v1/reports/players").status_code == 401


# --- the secret --------------------------------------------------------------


def test_sign_in_stays_off_without_a_secret(make_app, db_session, results):
    from fastapi.testclient import TestClient

    with TestClient(make_app(SESSION_SECRET=None)) as client:
        for path in ("login", "logout", "password"):
            response = client.post(f"/api/v1/auth/{path}", json={}, headers=CSRF_HEADERS)
            assert response.status_code == 503
            assert "SESSION_SECRET" in response.json()["detail"]
        assert client.get("/api/v1/auth/session").status_code == 503
        for page in ("/admin", "/admin/entrar", "/admin/definir-senha", "/admin/atividades"):
            response = client.get(page, follow_redirects=False)
            assert response.status_code == 503
            assert "indisponível" in response.text

        # A cookie is never honoured, but the token still is.
        client.cookies.set(COOKIE, "x" * 43)
        assert client.get("/api/v1/reports/players").status_code == 401
        assert (
            client.get("/api/v1/reports/players", headers={"X-Admin-Token": "test-token"}).status_code
            == 200
        )

    with pytest.raises(accounts.SignInDisabledError):
        accounts.invite_admin(db_session, "", TEACHER_EMAIL)


def test_a_short_secret_is_a_configuration_error():
    with pytest.raises(ValidationError):
        Settings(session_secret="too-short")
    assert Settings(session_secret="").sign_in_enabled is False
    assert Settings(session_secret="x" * 32).sign_in_enabled is True


def test_token_only_and_fully_disabled_configurations(make_app, results):
    from fastapi.testclient import TestClient

    with TestClient(make_app(ADMIN_TOKEN=None)) as client:
        # Sessions on, token off: a token is refused, anonymous is asked to sign in.
        assert client.get("/api/v1/reports/players").status_code == 401
        refused = client.get("/api/v1/reports/players", headers={"X-Admin-Token": "x"})
        assert refused.status_code == 403 and "disabled" in refused.json()["detail"]

    with TestClient(make_app(ADMIN_TOKEN=None, SESSION_SECRET=None)) as client:
        response = client.get("/api/v1/reports/players")
        assert response.status_code == 403 and "disabled" in response.json()["detail"]
