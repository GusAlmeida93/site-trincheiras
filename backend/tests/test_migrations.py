"""Prove the Alembic baseline and the ORM models describe the same schema."""

import os

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

from app.config import get_settings
from app.models import Base

from tests.conftest import TEST_DATABASE_URL, ensure_database

MIGRATION_DB_URL = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/trincheiras_migration_test"


@pytest.fixture()
def alembic_config(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", MIGRATION_DB_URL)
    get_settings.cache_clear()
    yield Config("alembic.ini")
    get_settings.cache_clear()


def test_upgrade_downgrade_upgrade_matches_models(alembic_config):
    ensure_database(MIGRATION_DB_URL)
    engine = create_engine(MIGRATION_DB_URL)
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("DROP SCHEMA public CASCADE")
            conn.exec_driver_sql("CREATE SCHEMA public")
            conn.commit()

        command.upgrade(alembic_config, "head")
        command.downgrade(alembic_config, "base")
        command.upgrade(alembic_config, "head")

        with engine.connect() as conn:
            context = MigrationContext.configure(
                conn,
                opts={"compare_type": True, "compare_server_default": True},
            )
            diff = compare_metadata(context, Base.metadata)
        assert diff == [], f"models and migrations diverge: {diff}"
    finally:
        engine.dispose()
