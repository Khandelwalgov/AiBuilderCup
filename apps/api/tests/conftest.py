import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from opportunity_platform.db.models import Base
from opportunity_platform.db.session import get_session
from opportunity_platform.main import app
from opportunity_platform.seed import seed


@pytest.fixture
def db():
    # PostgreSQL only; isolated schema, no truncation of application data.
    url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://opportunity:local-development-only@localhost:5432/opportunity",
    )
    admin = create_engine(url)
    schema = "test_" + uuid.uuid4().hex
    with admin.begin() as conn:
        conn.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session, Path(__file__).resolve().parents[3] / "data/fixtures/opportunities.json")
        yield session
    engine.dispose()
    with admin.begin() as conn:
        conn.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
    admin.dispose()


@pytest.fixture
def client(db, monkeypatch):
    from opportunity_platform.core.config import settings

    monkeypatch.setattr(settings(), "enable_development_catalogue", True)
    app.dependency_overrides[get_session] = lambda: db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def isolated_provider_configuration(monkeypatch):
    from opportunity_platform.core.config import settings

    monkeypatch.setattr(settings(), "ai_extraction_provider", "gemini")
