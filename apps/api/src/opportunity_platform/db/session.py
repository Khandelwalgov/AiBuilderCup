from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from opportunity_platform.core.config import settings
from opportunity_platform.core.database import connect_args

engine = create_engine(
    settings().database_url,
    pool_pre_ping=True,
    pool_size=3,
    max_overflow=0,
    pool_timeout=10,
    connect_args=connect_args(settings().database_provider),
)


def get_session():
    with Session(engine) as session:
        yield session
