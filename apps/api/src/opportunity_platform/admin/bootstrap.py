"""Privileged operator command; no HTTP endpoint grants administrator access."""

import argparse

import firebase_admin
from firebase_admin import auth
from sqlalchemy.orm import Session

from opportunity_platform.core.config import settings
from opportunity_platform.db.models import AuditEvent
from opportunity_platform.db.session import engine
from opportunity_platform.profiles.service import account

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Grant or revoke a DB admin role after verifying a Firebase user exists. "
            "Requires operator DB and Firebase ADC permissions."
        )
    )
    parser.add_argument("--uid", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--revoke", action="store_true")
    args = parser.parse_args()
    if not settings().firebase_project_id:
        parser.error("Set FIREBASE_PROJECT_ID and Application Default Credentials first.")
    if args.project_id != settings().firebase_project_id:
        parser.error("--project-id must match the configured FIREBASE_PROJECT_ID.")
    app = firebase_admin.initialize_app(options={"projectId": settings().firebase_project_id})
    identity = auth.get_user(args.uid, app=app)
    if identity.disabled and not args.revoke:
        parser.error("Cannot grant access to a disabled account.")
    with Session(engine) as session:
        user = account(session, identity.uid)
        user.is_admin = not args.revoke
        session.add(
            AuditEvent(
                actor_id=user.id,
                action="operator_admin_revoked" if args.revoke else "operator_admin_granted",
                object_id=user.id,
                details={"method": "privileged_local_cli"},
            )
        )
        session.commit()
    print("Administrator role updated; the operator action was audited.")
