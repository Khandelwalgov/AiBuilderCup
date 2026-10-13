"""Exercise the real migration chain without touching application tables."""

import os
import uuid

from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command
from opportunity_platform.core.config import settings


def test_phase_one_records_survive_upgrade_and_downgrade(monkeypatch):
    url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://opportunity:local-development-only@localhost:5432/opportunity",
    )
    root = create_engine(url)
    schema = "migration_test_" + uuid.uuid4().hex
    with root.begin() as conn:
        conn.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
    scoped = root.url.update_query_dict({"options": f"-csearch_path={schema}"})
    monkeypatch.setattr(settings(), "database_url", scoped.render_as_string(hide_password=False))
    engine = create_engine(scoped)
    config = Config("alembic.ini")
    try:
        command.upgrade(config, "57d3f03c34e3")
        identifier = uuid.uuid4()
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (id, firebase_uid, language, notification_preferences) "
                    "VALUES (:id, 'synthetic-migration-user', 'en', '{}')"
                ),
                {"id": identifier},
            )
        command.upgrade(config, "head")
        with engine.connect() as conn:
            assert conn.scalar(text("SELECT count(*) FROM users")) == 1
            assert (
                conn.scalar(text("SELECT is_admin FROM users WHERE id=:id"), {"id": identifier})
                is False
            )
        command.check(config)
        command.downgrade(config, "57d3f03c34e3")
        with engine.connect() as conn:
            assert conn.scalar(text("SELECT id FROM users")) == identifier
        command.upgrade(config, "head")
    finally:
        engine.dispose()
        with root.begin() as conn:
            conn.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        root.dispose()
