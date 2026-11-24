from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_DIR = Path(__file__).resolve().parent
SESSION_SECRET_MIN_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://trincheiras:trincheiras@localhost:5432/trincheiras"
    # Empty token disables every /api/v1/admin and /api/v1/reports endpoint.
    admin_token: str = ""
    # Keys the digests of session and invite tokens (HMAC-SHA256); the database
    # only ever stores those digests. Empty disables teacher sign-in and the
    # /admin area outright: there is deliberately no default. Rotating it signs
    # everyone out and voids outstanding invite links.
    session_secret: str = ""
    # A session lasts this long from sign-in (no sliding renewal).
    session_hours: int = 12
    # Dates on the admin pages and in CSV exports are shown in this zone.
    display_timezone: str = "America/Sao_Paulo"
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

    @field_validator("session_secret")
    @classmethod
    def _secret_is_long_enough(cls, v: str) -> str:
        v = v.strip()
        if v and len(v) < SESSION_SECRET_MIN_LENGTH:
            raise ValueError(
                f"SESSION_SECRET must have at least {SESSION_SECRET_MIN_LENGTH} characters"
            )
        return v

    @property
    def sign_in_enabled(self) -> bool:
        return bool(self.session_secret)

    @property
    def secure_cookies(self) -> bool:
        # Local development and the e2e stack run on plain http://localhost,
        # where WebKit drops Secure cookies.
        return self.app_env not in ("dev", "test")

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
