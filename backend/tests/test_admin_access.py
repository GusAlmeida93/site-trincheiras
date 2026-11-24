"""Every admin and report route, tried with each kind of credential.

The routes are read from the app's OpenAPI document, so a route added later
is covered without anyone remembering to list it here.
"""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.models import AdminSession
from app.services import accounts

from tests.conftest import CSRF_HEADERS

PROTECTED_PREFIXES = ("/api/v1/admin", "/api/v1/reports")
SAFE_METHODS = {"GET"}
PATH_VALUES = {"player_id": "999999", "lesson_slug": "nenhuma", "slug": "nenhum"}
TOKEN = {"X-Admin-Token": "test-token"}


def _protected_routes() -> list[tuple[str, str]]:
    from app.main import create_app

    try:
        paths = create_app().openapi()["paths"]
    finally:
        get_settings.cache_clear()
    return sorted(
        (method.upper(), path)
        for path, operations in paths.items()
        if path.startswith(PROTECTED_PREFIXES)
        for method in operations
        if method in ("get", "put", "post", "patch", "delete")
    )


ROUTES = _protected_routes()


def test_the_route_list_is_what_we_think_it_is():
    assert len(ROUTES) >= 18
    assert ("DELETE", "/api/v1/admin/players/{player_id}") in ROUTES
    assert ("DELETE", "/api/v1/admin/players") in ROUTES
    assert ("PUT", "/api/v1/admin/lessons/{lesson_slug}") in ROUTES
    assert ("GET", "/api/v1/reports/players.csv") in ROUTES
    assert ("GET", "/api/v1/reports/players/{player_id}/answers") in ROUTES


def call(client, method: str, path: str, headers: dict[str, str] | None = None):
    # Nothing here exists (unknown ids, an empty body), so an authorized call
    # ends in 404 or 422 and changes nothing: only the gate is under test.
    return client.request(
        method,
        path.format(**PATH_VALUES),
        params={"class_group": "Turma inexistente"},
        json={} if method in ("PUT", "POST", "PATCH") else None,
        headers=headers or {},
    )


@pytest.mark.parametrize("method, path", ROUTES, ids=[f"{m} {p}" for m, p in ROUTES])
def test_access_control(client, db_session, teacher, seeded_content, method, path):
    from tests.conftest import sign_in

    # Nobody.
    assert call(client, method, path).status_code == 401
    # The custom header alone is not a credential.
    assert call(client, method, path, CSRF_HEADERS).status_code == 401

    # The shared token, for scripts.
    assert call(client, method, path, {"X-Admin-Token": "wrong"}).status_code == 403
    assert call(client, method, path, TOKEN).status_code not in (401, 403)

    # A teacher's session.
    assert sign_in(client).status_code == 200
    with_header = call(client, method, path, CSRF_HEADERS)
    assert with_header.status_code not in (401, 403), with_header.text
    bare = call(client, method, path)
    if method in SAFE_METHODS:
        assert bare.status_code not in (401, 403)
    else:
        # A cookie alone must not be able to change anything (CSRF).
        assert bare.status_code == 403
        assert "X-Requested-With" in bare.json()["detail"]
    # A wrong token is refused even alongside a valid session.
    assert call(client, method, path, {"X-Admin-Token": "wrong"}).status_code == 403
    assert with_header.headers["cache-control"] == "no-store"

    # An expired session.
    session = db_session.scalar(select(AdminSession))
    session.expires_at = accounts.now() - timedelta(seconds=1)
    db_session.commit()
    assert call(client, method, path, CSRF_HEADERS).status_code == 401
