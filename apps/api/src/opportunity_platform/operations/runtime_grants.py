"""Explicit migration-identity DML grants on the two additive intelligence tables only."""

import argparse
import json
import re

from sqlalchemy import create_engine, pool, text

TABLES = ("policy_embeddings", "inference_reservations")


def validate_role(role):
    if not isinstance(role, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", role):
        raise ValueError("An explicit ordinary PostgreSQL role identifier is required")
    return role


def grant(connection, role):
    validate_role(role)
    ordinary = connection.scalar(
        text("""
        SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=:role
          AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolbypassrls)
        AND current_user <> :role
        AND NOT has_schema_privilege(:role, current_schema(), 'CREATE')
    """),
        {"role": role},
    )
    if not ordinary:
        raise ValueError("Runtime role must exist, lack DDL/admin privileges and differ from owner")
    quoted = connection.dialect.identifier_preparer.quote(role)
    for table in TABLES:
        connection.execute(text(f"GRANT SELECT, INSERT, UPDATE ON TABLE {table} TO {quoted}"))
    return {"runtime_dml_grants": "applied", "tables": list(TABLES), "ddl_granted": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-role", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approved-project")
    args = parser.parse_args(argv)
    validate_role(args.runtime_role)
    if not args.execute:
        print(
            json.dumps(
                {
                    "mode": "plan",
                    "tables": list(TABLES),
                    "privileges": ["SELECT", "INSERT", "UPDATE"],
                    "ddl_granted": False,
                }
            )
        )
        return 0
    if args.approved_project != args.project:
        parser.error("Explicit matching --approved-project required")
    from opportunity_platform.core.config import settings
    from opportunity_platform.core.database import connect_args, validate_neon_url

    config = settings()
    if config.firebase_project_id != args.project or config.database_provider != "neon":
        parser.error("Approved production Neon migration context required")
    validate_neon_url(config.database_url, direct=True)
    engine = create_engine(
        config.database_url,
        poolclass=pool.NullPool,
        connect_args=connect_args(config.database_provider),
    )
    try:
        with engine.begin() as connection:
            print(json.dumps(grant(connection, args.runtime_role)))
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit(
            "Runtime grant step failed; credentials and SQL diagnostics withheld."
        ) from None
