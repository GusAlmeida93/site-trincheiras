from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.routers import (
    admin_content,
    admin_pages,
    admin_players,
    answers,
    auth,
    health,
    lessons_public,
    pages,
    players,
    reports,
)
from app.vite import vite_asset


PRIVATE_PATHS = ("/admin", "/api/v1/admin", "/api/v1/reports", "/api/v1/auth")


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
    templates.env.globals["percent"] = admin_pages.percent
    templates.env.filters["datahora"] = admin_pages.local_datetime_filter(
        settings.display_timezone
    )
    app.state.templates = templates

    app.include_router(health.router)
    app.include_router(pages.router)
    app.include_router(players.router)
    app.include_router(answers.router)
    app.include_router(lessons_public.router)
    app.include_router(admin_content.router)
    app.include_router(admin_players.router)
    app.include_router(reports.router)
    app.include_router(auth.router)
    app.include_router(admin_pages.router)
    admin_pages.install(app)

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
        # Student results and session cookies must never sit in a cache, and
        # the back button after signing out must not show them again.
        elif request.url.path.startswith(PRIVATE_PATHS):
            response.headers["Cache-Control"] = "no-store"
            if request.url.path.startswith("/admin"):
                # No other site may put these pages (and their delete
                # buttons) in a frame.
                response.headers["X-Frame-Options"] = "DENY"
                response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        return response

    app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

    return app


app = create_app()
