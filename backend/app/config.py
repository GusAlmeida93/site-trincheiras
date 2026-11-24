from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://trincheiras:trincheiras@localhost:5432/trincheiras"
    # Empty token disables every /api/v1/admin and /api/v1/reports endpoint.
    admin_token: str = ""
    app_env: str = "dev"  # dev | test | prod
    # False opens one connection per request and closes it afterwards. Lambda
    # needs that: a frozen sandbox would otherwise hold a pooled connection
    # open, and Aurora only auto-pauses once no user connection is left.
    db_pool: bool = True
    # Seconds one connection attempt may take, and how long to keep retrying
    # failed attempts overall. A paused Aurora cluster needs ~15 s to resume
    # (30 s or more after a day asleep); 0 retries nothing.
    db_connect_timeout: int = 10
    db_connect_retry_seconds: int = 0
    # Mounts POST /internal/ops (migrate / seed). Only ever set on the ops
    # Lambda, which has no public URL and is invoked through IAM.
    ops_mode: bool = False
    default_lesson_slug: str = "tratado-de-versalhes"
    # e.g. http://localhost:5173 — when set, pages load assets from the Vite dev server.
    vite_dev_server: str = ""
    static_dir: Path = APP_DIR / "static"
    templates_dir: Path = APP_DIR / "templates"

    @field_validator("database_url")
    @classmethod
    def _normalize_driver(cls, v: str) -> str:
        # Bare postgres:// or postgresql:// URLs make SQLAlchemy pick psycopg2,
        # which is not installed; force the psycopg (v3) driver.
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v.removeprefix(prefix)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
