"""Explicit one-time administrator bootstrap for an existing authenticated profile.

Only a protected operator job may execute this. No users are created; ordinary API
routes never call it. Subsequent administrators require the normal authorized process.
"""

import argparse
import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from opportunity_platform.core.config import settings
from opportunity_platform.db.models import AuditEvent, Person, User


def bootstrap(session, target_uid, *, execute=False, confirmed=False):
    session.execute(select(func.pg_advisory_xact_lock(837455021)))
    target = session.scalar(select(User).where(User.firebase_uid == target_uid))
    has_profile = (
        target is not None
        and session.scalar(select(Person.id).where(Person.user_id == target.id)) is not None
    )
    admins = (
        session.scalar(select(func.count()).select_from(User).where(User.is_admin.is_(True))) or 0
    )
    if target is None or not has_profile:
        raise ValueError("Select an existing authenticated account with a saved personal profile")
    if admins and not target.is_admin:
        raise ValueError("Bootstrap is closed after the first administrator exists")
    if execute and not confirmed:
        raise ValueError("Explicit first-administrator security authorization is required")
    if execute and not target.is_admin:
        target.is_admin = True
        session.add(
            AuditEvent(
                actor_id=target.id,
                action="operator_authorized_first_admin",
                object_id=target.id,
                details={"boundary": "protected production operator job", "publication": "none"},
            )
        )
        session.flush()
    return {
        "mode": "execute" if execute else "plan",
        "target_exists_with_profile": True,
        "administrator_present": bool(admins),
        "policies_published": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-uid", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-first-admin", action="store_true")
    parser.add_argument("--approved-project")
    args = parser.parse_args(argv)
    config = settings()
    if args.execute and not (
        config.process_role == "ingestion_worker"
        and args.approved_project == config.firebase_project_id
    ):
        parser.error("Only an explicitly approved operator worker may bootstrap production roles")
    from opportunity_platform.db.session import engine

    with Session(engine) as session:
        report = bootstrap(
            session, args.target_uid, execute=args.execute, confirmed=args.confirm_first_admin
        )
        if args.execute:
            session.commit()
        else:
            session.rollback()
        print(json.dumps(report))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit(
            "Administrator bootstrap stopped; no account details are logged."
        ) from None
