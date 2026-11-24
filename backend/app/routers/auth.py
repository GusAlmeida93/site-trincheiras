"""Teacher sign-in. JSON only, reached with fetch (see security.py for why).

Every POST here must carry `X-Requested-With: trincheiras-admin`.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.schemas.auth import LoginRequest, PasswordSetRequest, SessionRead
from app.security import (
    clear_session_cookie,
    current_session_user,
    require_csrf_header,
    require_sign_in_enabled,
    session_token,
    set_session_cookie,
)
from app.services import accounts

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
    dependencies=[Depends(require_sign_in_enabled)],
)

_BAD_CREDENTIALS = "Invalid e-mail or password."


@router.post("/login", dependencies=[Depends(require_csrf_header)])
def login(
    payload: LoginRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionRead:
    """Signs a teacher in and sets the session cookie.

    Needs the header `X-Requested-With: trincheiras-admin`. Five failures for
    an e-mail lock it for 15 minutes (429 with Retry-After).
    """
    try:
        email = accounts.normalize_email(payload.email)
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_BAD_CREDENTIALS)

    retry_after = accounts.throttle_retry_after(db, email)
    if retry_after > 0:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    user = accounts.verify_credentials(db, email, payload.password)
    if user is None:
        accounts.record_failure(db, email)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_BAD_CREDENTIALS)

    accounts.clear_failures(db, email)
    token, expires_at = accounts.create_session(
        db, settings.session_secret, user, settings.session_hours
    )
    db.commit()
    set_session_cookie(response, settings, token)
    return SessionRead(email=user.email, expires_at=expires_at)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf_header)],
)
def logout(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Ends this browser's session on the server and clears the cookie."""
    token = session_token(request, settings)
    if token is not None:
        accounts.end_session(db, settings.session_secret, token)
        db.commit()
    clear_session_cookie(response, settings)


@router.post(
    "/password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf_header)],
)
def set_password(
    payload: PasswordSetRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Redeems a setup link from the invite-admin ops task (first password or reset).

    `token` is the part of the link after "#". It works once; using it signs
    the teacher out of every browser.
    """
    user = accounts.set_password(
        db, settings.session_secret, payload.token, payload.password
    )
    if user is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="This setup link is invalid, was already used, or has expired.",
        )
    db.commit()


@router.get("/session")
def read_session(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionRead:
    user = current_session_user(request, settings, db)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not signed in.")
    return SessionRead(email=user.email)
