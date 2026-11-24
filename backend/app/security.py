"""Who may call the admin and report APIs.

Two credentials are accepted:

* `X-Admin-Token` matching ADMIN_TOKEN, for scripts and tests.
* The session cookie a teacher gets by signing in at /admin.

A cookie rides along on requests the teacher never meant to make, so a
session-authenticated request that changes something must also carry the
header `X-Requested-With: trincheiras-admin`. A page on another site cannot
add a custom header without a CORS preflight, and this app answers none; the
cookie is SameSite=Lax as well, so cross-site POSTs arrive without it. The
check deliberately ignores Origin and Host: behind CloudFront the app sees the
Lambda URL's host, and the public address changes when the domain is attached.
"""

import secrets
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models import AdminUser
from app.services import accounts

CSRF_HEADER = "X-Requested-With"
CSRF_VALUE = "trincheiras-admin"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


@dataclass(frozen=True)
class AdminPrincipal:
    via: Literal["token", "session"]
    email: str | None = None


def session_cookie_name(settings: Settings) -> str:
    # The __Host- prefix makes browsers refuse the cookie unless it is Secure,
    # host-only and Path=/, so no other host of the domain can plant one. It
    # needs https, hence the plain name on http://localhost.
    return "__Host-trincheiras_admin" if settings.secure_cookies else "trincheiras_admin"


def set_session_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=session_cookie_name(settings),
        value=token,
        max_age=settings.session_hours * 3600,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookies,
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=session_cookie_name(settings),
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookies,
    )


def session_token(request: Request, settings: Settings) -> str | None:
    return request.cookies.get(session_cookie_name(settings)) or None


def current_session_user(
    request: Request, settings: Settings, db: Session
) -> AdminUser | None:
    if not settings.sign_in_enabled:
        return None
    token = session_token(request, settings)
    if token is None:
        return None
    return accounts.get_session_user(db, settings.session_secret, token)


def require_csrf_header(request: Request) -> None:
    if request.headers.get(CSRF_HEADER) != CSRF_VALUE:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=f"Missing {CSRF_HEADER}: {CSRF_VALUE} header.",
        )


def require_sign_in_enabled(
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    if not settings.sign_in_enabled:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sign-in is disabled (SESSION_SECRET is not configured).",
        )


def require_admin(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    x_admin_token: Annotated[str | None, Header()] = None,
) -> AdminPrincipal:
    if x_admin_token is not None:
        if not settings.admin_token:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Token access is disabled (ADMIN_TOKEN is not configured).",
            )
        if not secrets.compare_digest(
            x_admin_token.encode(), settings.admin_token.encode()
        ):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Invalid admin token.")
        return AdminPrincipal(via="token")

    user = current_session_user(request, settings, db)
    if user is not None:
        if request.method not in SAFE_METHODS:
            require_csrf_header(request)
        return AdminPrincipal(via="session", email=user.email)

    if not settings.admin_token and not settings.sign_in_enabled:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Admin API is disabled (ADMIN_TOKEN and SESSION_SECRET are not configured).",
        )
    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="Sign in at /admin or send the X-Admin-Token header.",
    )
