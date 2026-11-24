"""Deploy-time operations. Mounted exclusively when OPS_MODE=true (see main.py).

On AWS the ops Lambda runs this same image with OPS_MODE=true and no public
URL. `aws lambda invoke --payload '{"task": "migrate"}'` reaches this endpoint
through the Lambda Web Adapter, which POSTs non-HTTP event payloads to
AWS_LWA_PASS_THROUGH_PATH. The database sits in private subnets, so this is
the only way to run migrations against it.
"""

from typing import Literal

from alembic import command
from alembic.config import Config
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.config import APP_DIR
from app.db import get_session_factory
from app.seed.loader import seed_all

router = APIRouter(prefix="/internal", tags=["ops"])

BACKEND_DIR = APP_DIR.parent


class OpsRequest(BaseModel):
    task: Literal["migrate", "seed", "migrate-and-seed", "status"]


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


@router.post("/ops", include_in_schema=False)
def run_ops(request: OpsRequest) -> dict[str, object]:
    result: dict[str, object] = {"task": request.task}

    if request.task in ("migrate", "migrate-and-seed"):
        command.upgrade(_alembic_config(), "head")
        result["migrated"] = True

    if request.task in ("seed", "migrate-and-seed"):
        session = get_session_factory()()
        try:
            result["seeded"] = seed_all(session)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    result["status"] = _status()
    return result
