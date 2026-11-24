"""The teacher's area at /admin: server-rendered, read-only pages.

Every change (sign in, set password, sign out, delete) happens in the browser
through fetch against the JSON API: behind CloudFront a plain HTML form post
is refused before it reaches the app (it lacks the body hash), so these pages
never accept a POST.

Redirects are relative on purpose. Behind CloudFront the Host header is the
Lambda URL's, so an absolute URL built from the request would point there.
"""

from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models import AdminUser
from app.security import current_session_user
from app.services import accounts
from app.services import reports as reports_service

router = APIRouter(prefix="/admin", tags=["admin-pages"], include_in_schema=False)

SIGN_IN_PATH = "/admin/entrar"
HOME_PATH = "/admin"


class SignInRequired(Exception):
    pass


class SignInDisabled(Exception):
    pass


def _render(
    request: Request, template: str, context: dict[str, object], status_code: int = 200
) -> Response:
    return request.app.state.templates.TemplateResponse(
        request, f"admin/{template}", context, status_code=status_code
    )


def _message(
    request: Request, title: str, text: str, status_code: int, admin: AdminUser | None = None
) -> Response:
    return _render(
        request,
        "message.html",
        {"title": title, "text": text, "admin_email": admin.email if admin else None},
        status_code,
    )


def install(app: FastAPI) -> None:
    @app.exception_handler(SignInRequired)
    async def _to_sign_in(request: Request, exc: SignInRequired) -> Response:
        return RedirectResponse(SIGN_IN_PATH, status_code=303)

    @app.exception_handler(SignInDisabled)
    async def _disabled(request: Request, exc: SignInDisabled) -> Response:
        return _message(
            request,
            "Área do professor indisponível",
            "O acesso de professores não está configurado neste servidor "
            "(falta a variável SESSION_SECRET).",
            503,
        )


def require_enabled(settings: Annotated[Settings, Depends(get_settings)]) -> None:
    if not settings.sign_in_enabled:
        raise SignInDisabled


def signed_in_admin(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AdminUser:
    if not settings.sign_in_enabled:
        raise SignInDisabled
    user = current_session_user(request, settings, db)
    if user is None:
        raise SignInRequired
    return user


Admin = Annotated[AdminUser, Depends(signed_in_admin)]


@router.get("/entrar", response_class=HTMLResponse, dependencies=[Depends(require_enabled)])
def sign_in_page(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    if current_session_user(request, settings, db) is not None:
        return RedirectResponse(HOME_PATH, status_code=303)
    return _render(request, "sign_in.html", {"admin_email": None})


@router.get(
    "/definir-senha", response_class=HTMLResponse, dependencies=[Depends(require_enabled)]
)
def set_password_page(request: Request) -> Response:
    return _render(
        request,
        "set_password.html",
        {"admin_email": None, "password_min_length": accounts.PASSWORD_MIN_LENGTH},
    )


# Both spellings are routes: Starlette's own trailing-slash redirect is
# absolute and would send the browser to the Lambda URL.
@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def classes_page(
    request: Request, admin: Admin, db: Annotated[Session, Depends(get_db)]
) -> Response:
    return _render(
        request,
        "classes.html",
        {
            "admin_email": admin.email,
            "section": "classes",
            "classes": reports_service.class_summaries(db),
        },
    )


@router.get("/turma", response_class=HTMLResponse)
def class_page(
    request: Request,
    admin: Admin,
    db: Annotated[Session, Depends(get_db)],
    nome: str = "",
) -> Response:
    players = reports_service.player_score_summaries(db, class_group=nome) if nome else []
    if not players:
        return _message(
            request,
            "Turma não encontrada",
            "Não há alunos alistados nesta turma. Ela pode ter sido apagada.",
            404,
            admin,
        )
    return _render(
        request,
        "class.html",
        {
            "admin_email": admin.email,
            "section": "classes",
            "class_group": nome,
            "players": players,
            "answers_count": sum(p.answers_count for p in players),
        },
    )


@router.get("/alunos/{player_id}", response_class=HTMLResponse)
def player_page(
    request: Request,
    player_id: int,
    admin: Admin,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    player = reports_service.player_score_summary(db, player_id)
    if player is None:
        return _message(
            request,
            "Aluno não encontrado",
            "Este aluno não existe. Ele pode ter sido apagado.",
            404,
            admin,
        )
    answers = reports_service.player_answers(db, player_id) or []
    by_activity: dict[str, dict[str, object]] = {}
    for row in answers:
        entry = by_activity.setdefault(
            row.activity_slug,
            {"title": row.activity_title, "answers": 0, "correct": 0, "score": 0},
        )
        entry["answers"] += 1  # type: ignore[operator]
        entry["correct"] += int(row.is_correct)  # type: ignore[operator]
        entry["score"] += row.score_delta  # type: ignore[operator]
    return _render(
        request,
        "player.html",
        {
            "admin_email": admin.email,
            "section": "classes",
            "player": player,
            "answers": answers,
            "by_activity": list(by_activity.values()),
        },
    )


@router.get("/atividades", response_class=HTMLResponse)
def activities_page(
    request: Request,
    admin: Admin,
    db: Annotated[Session, Depends(get_db)],
    turma: str = "",
) -> Response:
    return _render(
        request,
        "activities.html",
        {
            "admin_email": admin.email,
            "section": "activities",
            "class_group": turma,
            "class_groups": [c.class_group for c in reports_service.class_summaries(db)],
            "activities": reports_service.activity_summaries(db, class_group=turma or None),
        },
    )


def local_datetime_filter(timezone_name: str):  # type: ignore[no-untyped-def]
    zone = ZoneInfo(timezone_name)

    def datahora(value) -> str:  # type: ignore[no-untyped-def]
        return value.astimezone(zone).strftime("%d/%m/%Y %H:%M") if value else "—"

    return datahora


def percent(part: int, whole: int) -> str:
    return f"{round(100 * part / whole)}%" if whole else "—"
