"""Test-only endpoints. Mounted exclusively when APP_ENV=test (see main.py)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models import Activity, Answer, Player, Question
from app.security import require_sign_in_enabled
from app.services import accounts

router = APIRouter(prefix="/api/v1/test", tags=["test-support"])


@router.post("/reset", include_in_schema=False)
def reset_volatile_data(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    # Content (lessons/questions/...) is seeded and stable; only the rows the
    # e2e suite creates get wiped between specs.
    db.execute(
        text(
            "TRUNCATE players, answers, admin_users, admin_sessions, login_throttles "
            "RESTART IDENTITY CASCADE"
        )
    )
    db.commit()
    return {"status": "reset"}


class InviteRequest(BaseModel):
    email: str


@router.post(
    "/admin-invite",
    include_in_schema=False,
    dependencies=[Depends(require_sign_in_enabled)],
)
def invite_admin(
    payload: InviteRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    # Stands in for the invite-admin ops task, which only exists on the ops
    # Lambda: same service call, so the browser suite walks the real flow
    # (open the link, choose a password, sign in). Anyone who can reach this
    # can make themselves a teacher, which is why the whole router is mounted
    # only when APP_ENV=test.
    invite = accounts.invite_admin(db, settings.session_secret, payload.email)
    db.commit()
    return {"email": invite.email, "setup_path": invite.setup_path}


@router.post("/sample-results", include_in_schema=False)
def sample_results(db: Annotated[Session, Depends(get_db)]) -> dict[str, dict[str, int]]:
    # Two classes with recorded answers, written straight to the tables so the
    # admin specs do not depend on how the lesson page submits and scores.
    questions = db.execute(
        select(Question.id, Activity.kind)
        .join(Activity, Question.activity_id == Activity.id)
        .order_by(Activity.position, Question.position)
    ).all()
    quiz = [q.id for q in questions if q.kind == "quiz"]
    match = [q.id for q in questions if q.kind == "match"]

    def enlist(name: str, class_group: str, number: str) -> Player:
        player = Player(name=name, class_group=class_group, recruit_number=number)
        db.add(player)
        db.flush()
        return player

    def answer(player: Player, question_id: int, value: str, correct: bool, delta: int) -> None:
        db.add(
            Answer(
                player_id=player.id,
                question_id=question_id,
                selected_value=value,
                is_correct=correct,
                score_delta=delta,
            )
        )

    ana = enlist("Ana Souza", "9º A", "TRN-000001-0001")
    bruno = enlist("Bruno Lima", "9º A", "TRN-000002-0002")
    carla = enlist("Carla Dias", "9º B", "TRN-000003-0003")
    answer(ana, quiz[0], "trench-1-opt-1", False, -5)
    answer(ana, quiz[0], "trench-1-opt-2", True, 10)
    answer(ana, quiz[1], "trench-2-opt-1", True, 10)
    answer(bruno, quiz[0], "trench-1-opt-2", True, 10)
    answer(carla, match[0], "doc-1", True, 10)
    db.commit()
    return {"players": {"ana": ana.id, "bruno": bruno.id, "carla": carla.id}}
