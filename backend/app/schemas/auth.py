from datetime import datetime

from pydantic import BaseModel, Field

from app.services.accounts import (
    EMAIL_MAX_LENGTH,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
)


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=EMAIL_MAX_LENGTH)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class PasswordSetRequest(BaseModel):
    # The part after "#" in the setup link.
    token: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)


class SessionRead(BaseModel):
    email: str
    expires_at: datetime | None = None
