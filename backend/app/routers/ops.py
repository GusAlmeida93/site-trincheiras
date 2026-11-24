"""Deploy-time operations. Mounted exclusively when OPS_MODE=true (see main.py).

On AWS the ops Lambda runs this same image with OPS_MODE=true and no public
URL. `aws lambda invoke --payload '{"task": "migrate"}'` reaches this endpoint
through the Lambda Web Adapter, which POSTs non-HTTP event payloads to
AWS_LWA_PASS_THROUGH_PATH. The database sits in private subnets, so this is
the only way to run migrations against it.

Teacher accounts are managed here too, because there is no public sign-up:

    {"task": "invite-admin", "email": "prof@example.com"}
        Creates the account (or re-invites it) and returns `setup_path`, a
        one-time link where the teacher sets their own password. Also the
        password reset. Optional "expires_in_hours" (default 48, at most 168).
    {"task": "deactivate-admin", "email": "prof@example.com"}
    {"task": "list-admins"}
"""

from collections.abc import Callable
from typing import Literal, TypeVar

from alembic import command
from alembic.config import Config
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import APP_DIR, get_settings
from app.db import get_session_factory
from app.seed.loader import seed_all
from app.services import accounts

T = TypeVar("T")

router = APIRouter(prefix="/internal", tags=["ops"])

BACKEND_DIR = APP_DIR.parent


ACCOUNT_TASKS = ("invite-admin", "deactivate-admin")


class OpsRequest(BaseModel):
    task: Literal[
        "migrate",
        "seed",
        "migrate-and-seed",
        "status",
        "invite-admin",
        "deactivate-admin",
        "list-admins",
    ]
    email: str | None = Field(default=None, max_length=accounts.EMAIL_MAX_LENGTH)
    expires_in_hours: int = Field(
        default=accounts.INVITE_DEFAULT_HOURS, ge=1, le=accounts.INVITE_MAX_HOURS
    )

    @model_validator(mode="after")
    def _account_tasks_need_an_email(self) -> "OpsRequest":
        if self.task in ACCOUNT_TASKS:
            if not self.email:
                raise ValueError(f'"{self.task}" needs an "email"')
            accounts.normalize_email(self.email)
        return self


def _alembic_config() -> Config:
    config = Config()
    # No ini file on purpose: alembic's fileConfig() call would replace the
    # server's logging setup mid-request.
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return config


def _status() -> dict[str, object]:
    session = get_session_factory()()
    try:
        revision = session.scalar(text("SELECT version_num FROM alembic_version"))
        lessons = session.scalar(text("SELECT count(*) FROM lessons"))
        players = session.scalar(text("SELECT count(*) FROM players"))
        answers = session.scalar(text("SELECT count(*) FROM answers"))
    finally:
        session.close()
    return {"revision": revision, "lessons": lessons, "players": players, "answers": answers}


def _in_transaction(work: Callable[[Session], T]) -> T:
    session = get_session_factory()()
    try:
        value = work(session)
        session.commit()
        return value
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _invite(request: OpsRequest) -> dict[str, object]:
    secret = get_settings().session_secret
    if not secret:
        # Without the secret the web function could not check the link either.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sign-in is disabled (SESSION_SECRET is not configured).",
        )
    assert request.email is not None
    email = request.email
    invite = _in_transaction(
        lambda session: accounts.invite_admin(
            session, secret, email, request.expires_in_hours
        )
    )
    return {
        "email": invite.email,
        "created": invite.created,
        # Append to the site address and hand it to the teacher. It works once.
        "setup_path": invite.setup_path,
        "expires_at": invite.expires_at.isoformat(),
    }


@router.post("/ops", include_in_schema=False)
def run_ops(request: OpsRequest) -> dict[str, object]:
    result: dict[str, object] = {"task": request.task}

    if request.task == "invite-admin":
        result["invite"] = _invite(request)
        return result

    if request.task == "deactivate-admin":
        assert request.email is not None
        email = request.email
        result["deactivated"] = _in_transaction(
            lambda session: accounts.deactivate_admin(session, email)
        )
        return result

    if request.task == "list-admins":
        result["admins"] = _in_transaction(accounts.list_admins)
        return result

    if request.task in ("migrate", "migrate-and-seed"):
        command.upgrade(_alembic_config(), "head")
        result["migrated"] = True

    if request.task in ("seed", "migrate-and-seed"):
        result["seeded"] = _in_transaction(seed_all)

    result["status"] = _status()
    return result
