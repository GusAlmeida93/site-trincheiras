import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings


def require_admin(
    x_admin_token: Annotated[str | None, Header()] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
) -> None:
    if not settings.admin_token:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Admin API is disabled (ADMIN_TOKEN is not configured).",
        )
    if x_admin_token is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Admin-Token header.",
        )
    if not secrets.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Invalid admin token.")
