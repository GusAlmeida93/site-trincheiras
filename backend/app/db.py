import logging
import time
from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Engine is created lazily on first use: the process must boot (and /healthz
# must answer) even when the database is unreachable.
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _pause(seconds: float) -> None:
    time.sleep(seconds)


def build_engine(settings: Settings) -> Engine:
    options: dict[str, Any] = {
        "connect_args": {"connect_timeout": settings.db_connect_timeout},
    }
    if settings.db_pool:
        options.update(pool_pre_ping=True, pool_size=5, max_overflow=5)
    else:
        options["poolclass"] = NullPool
    engine = create_engine(settings.database_url, **options)

    if settings.db_connect_retry_seconds > 0:
        retry_for = settings.db_connect_retry_seconds

        @event.listens_for(engine, "do_connect")
        def connect_with_retry(dialect, _record, cargs, cparams):  # type: ignore[no-untyped-def]
            # A database that is waking up (Aurora resuming from auto-pause)
            # refuses or times out the first attempts; keep trying until the
            # budget runs out, then let the last error surface.
            deadline = time.monotonic() + retry_for
            attempt = 0
            while True:
                attempt += 1
                try:
                    return dialect.connect(*cargs, **cparams)
                except dialect.loaded_dbapi.OperationalError as exc:
                    if time.monotonic() >= deadline:
                        raise
                    logger.warning("database connect attempt %d failed: %s", attempt, exc)
                    _pause(min(2.0, max(0.0, deadline - time.monotonic())))

    return engine


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = build_engine(get_settings())
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
