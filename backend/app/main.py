from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.routers import (
    admin_content,
    answers,
    health,
    lessons_public,
    pages,
    players,
    reports,
)
from app.vite import vite_asset


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Trincheiras Lesson Platform",
        version="1.0.0",
        description=(
            "Interactive history-lesson platform: lesson content, player "
            "registration, answer telemetry, and teacher reporting."
        ),
    )

    templates = Jinja2Templates(directory=str(settings.templates_dir))
    templates.env.globals["vite_asset"] = vite_asset
    app.state.templates = templates

    app.include_router(health.router)
    app.include_router(pages.router)
    app.include_router(players.router)
    app.include_router(answers.router)
    app.include_router(lessons_public.router)
    app.include_router(admin_content.router)
    app.include_router(reports.router)

    if settings.app_env == "test":
        from app.routers import test_support

        app.include_router(test_support.router)

    if settings.ops_mode:
        from app.routers import ops

        app.include_router(ops.router)

    @app.middleware("http")
    async def immutable_dist_cache(request: Request, call_next):
        response = await call_next(request)
        # Vite output is content-hashed — safe to cache forever.
        if request.url.path.startswith("/static/dist/") and response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

    app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

    return app


app = create_app()
