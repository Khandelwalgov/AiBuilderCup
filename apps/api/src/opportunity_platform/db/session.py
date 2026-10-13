from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from opportunity_platform.core.config import settings

engine = create_engine(
    settings().database_url,
    pool_pre_ping=True,
    pool_size=3,
    max_overflow=0,
    pool_timeout=10,
    connect_args={"connect_timeout": 10},
)


def get_session():
    with Session(engine) as session:
        yield session
