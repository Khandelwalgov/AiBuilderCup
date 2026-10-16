from sqlalchemy import create_engine, pool

from alembic import context
from opportunity_platform.core.config import settings
from opportunity_platform.core.database import connect_args, validate_neon_url
from opportunity_platform.db.models import Base

config = context.config
target_metadata = Base.metadata
if context.is_offline_mode():
    context.configure(
        url=settings().database_url, target_metadata=target_metadata, literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    if settings().database_provider == "neon":
        validate_neon_url(settings().database_url, direct=True)
    engine = create_engine(
        settings().database_url,
        poolclass=pool.NullPool,
        connect_args=connect_args(settings().database_provider),
    )
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
