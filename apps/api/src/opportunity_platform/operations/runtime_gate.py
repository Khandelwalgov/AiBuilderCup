"""Read-only application/worker privilege gate after an approved schema operation."""

import json

from sqlalchemy import create_engine, pool, text

from opportunity_platform.core.config import settings
from opportunity_platform.core.database import connect_args

REQUIRED = {
    "policy_embeddings": ["SELECT", "INSERT", "UPDATE"],
    "inference_reservations": ["SELECT", "INSERT", "UPDATE"],
    "sources": ["SELECT", "INSERT", "UPDATE"],
    "source_snapshots": ["SELECT", "INSERT", "UPDATE"],
    "ingestion_runs": ["SELECT", "INSERT", "UPDATE"],
    "opportunities": ["SELECT", "INSERT", "UPDATE"],
    "opportunity_versions": ["SELECT", "INSERT", "UPDATE"],
    "audit_events": ["SELECT", "INSERT"],
}


def verify(connection):
    connection.execute(text("SET TRANSACTION READ ONLY"))
    for table, privileges in REQUIRED.items():
        for privilege in privileges:
            if not connection.scalar(
                text("SELECT has_table_privilege(current_user, :name, :privilege)"),
                {"name": table, "privilege": privilege},
            ):
                raise RuntimeError(
                    f"Application role lacks {privilege} on {table}; approved grants required"
                )
    ddl = connection.scalar(
        text("SELECT has_schema_privilege(current_user, current_schema(), 'CREATE')")
    )
    return {
        "runtime_privileges": "passed",
        "runtime_role_can_create_in_schema": bool(ddl),
        "profile_data_read": False,
    }


def main():
    config = settings()
    engine = create_engine(
        config.database_url,
        poolclass=pool.NullPool,
        connect_args=connect_args(config.database_provider),
    )
    try:
        with engine.connect() as connection:
            print(json.dumps(verify(connection)))
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        raise SystemExit(str(error)) from None
    except Exception:
        raise SystemExit("Application privilege gate failed; credentials withheld.") from None
