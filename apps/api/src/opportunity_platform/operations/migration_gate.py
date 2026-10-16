"""Default read-only schema gate. Upgrades only with explicit release authorization."""

import argparse
import json

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, pool, text

from alembic import command
from opportunity_platform.core.config import settings
from opportunity_platform.core.database import connect_args, validate_neon_url


def verify_head(connection, expected):
    # Missing metadata is a failure, never a reason to initialize/stamp the database.
    connection.execute(text("SET TRANSACTION READ ONLY"))
    revisions = set(connection.execute(text("SELECT version_num FROM alembic_version")).scalars())
    if revisions != set(expected):
        raise RuntimeError("Database revision mismatch; approve a separate schema operation")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["verify", "upgrade"], default="verify")
    parser.add_argument("--approve-upgrade", action="store_true")
    args = parser.parse_args(argv)
    if args.mode == "upgrade" and not args.approve_upgrade:
        parser.error("Upgrade requires explicit --approve-upgrade")
    config = Config("alembic.ini")
    current = settings()
    if current.database_provider == "neon":
        validate_neon_url(current.database_url, direct=True)
    if args.mode == "upgrade":
        command.upgrade(config, "head")
    engine = create_engine(
        current.database_url,
        poolclass=pool.NullPool,
        connect_args=connect_args(current.database_provider),
    )
    try:
        with engine.connect() as connection:
            verify_head(connection, ScriptDirectory.from_config(config).get_heads())
    finally:
        engine.dispose()
    print(json.dumps({"schema_gate": "passed", "mode": args.mode, "data_initialization": False}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit(
            "Schema gate failed; credentials and database diagnostics withheld."
        ) from None
