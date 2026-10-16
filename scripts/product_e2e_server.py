"""Test-only local server: real Firebase emulator auth, disposable DB schema and private files.

Never imports or overrides authentication. No live sources/providers or application-schema writes.
"""

import os
import shutil
import signal
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

if (
    os.environ.get("ENVIRONMENT") != "development"
    or os.environ.get("FIREBASE_PROJECT_ID") != "demo-opportunity-completion"
    or os.environ.get("FIREBASE_AUTH_EMULATOR_HOST") != "127.0.0.1:19299"
):
    raise SystemExit("An explicitly local fictional Firebase emulator is required.")
from opportunity_platform.core.config import settings

original = settings().database_url
schema = "product_e2e_" + uuid.uuid4().hex
admin = create_engine(original)
with admin.begin() as connection:
    connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
root = Path(tempfile.mkdtemp(prefix="opportunity-fictional-documents-"))
os.environ["DATABASE_URL"] = (
    make_url(original)
    .update_query_dict({"options": f"-csearch_path={schema}"})
    .render_as_string(hide_password=False)
)
os.environ["DOCUMENT_LOCAL_ROOT"] = str(root)
os.environ["DOCUMENT_STORAGE_BACKEND"] = "local"
os.environ["DOCUMENT_UPLOADS_ENABLED"] = "true"
os.environ["AI_INGESTION_LIVE_ENABLED"] = "false"
os.environ["AI_ASSISTANT_LIVE_ENABLED"] = "false"
os.environ["OPENAI_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
settings.cache_clear()
try:
    from sqlalchemy.orm import Session

    from opportunity_platform.db.models import (
        Base,
        Opportunity,
        OpportunityVersion,
        Person,
        ProfileFact,
        Requirement,
        RequirementEvidence,
        Source,
        User,
    )
    from opportunity_platform.db.session import engine

    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        reviewer = User(firebase_uid="fictional-local-policy-reviewer", is_admin=True)
        session.add(reviewer)
        session.flush()
        source = Source(
            name="FICTIONAL documentary policy — emulator test only",
            authority="Fictional authority",
            is_synthetic=True,
            status="verified",
            url="https://example.invalid/fictional-policy",
            last_successful_check_at=now,
        )
        session.add(source)
        session.flush()
        for index in [1, 2, 3, 4, 5]:
            op = Opportunity(
                source_id=source.id,
                source_key=f"fictional-documentary-{index}",
                category="education",
                is_synthetic=True,
            )
            session.add(op)
            session.flush()
            version = OpportunityVersion(
                opportunity_id=op.id,
                version=1,
                publication_state="published",
                status="verified",
                title=f"FICTIONAL scholarship {index}",
                summary="Fictional readiness exercise; no actual scholarship or award.",
                issuer="Fictional authority",
                source_url=source.url,
                last_verified_at=now,
                reviewer_id=reviewer.id,
                country="IN",
            )
            session.add(version)
            session.flush()
            op.published_version_id = version.id
            if index in {4, 5}:
                kind = "business" if index == 4 else "household"
                op.category = kind
                version.category = kind
                version.title = f"FICTIONAL {kind} opportunity"
                condition = (
                    {"op": "eq", "fact": "business_registered", "value": True}
                    if index == 4
                    else {
                        "op": "lte",
                        "fact": "annual_household_income",
                        "value": 300000,
                        "income_period": "2026-27",
                        "income_definition": "fictional-household",
                    }
                )
                req = Requirement(
                    version_id=version.id,
                    description=f"FICTIONAL {kind} condition",
                    subject_context=kind,
                    kind="eligibility",
                    application_context="all",
                    rule={"op": "condition", "condition": condition, "children": []},
                )
                session.add(req)
                session.flush()
                session.add(
                    RequirementEvidence(
                        requirement_id=req.id,
                        source_url=source.url,
                        page="1",
                        passage=f"FICTIONAL test-only condition: {condition}",
                    )
                )
                continue
            if index == 3:
                course = Requirement(
                    version_id=version.id,
                    description="FICTIONAL currently studying postgraduate course",
                    subject_context="person",
                    kind="eligibility",
                    application_context="all",
                    rule={
                        "op": "condition",
                        "condition": {
                            "op": "eq",
                            "fact": "current_education_level",
                            "value": "postgraduate",
                        },
                        "children": [],
                    },
                )
                session.add(course)
                session.flush()
                session.add(
                    RequirementEvidence(
                        requirement_id=course.id,
                        source_url=source.url,
                        page="1",
                        passage="FICTIONAL policy: currently enrolled in a postgraduate course.",
                    )
                )
                continue
            age = Requirement(
                version_id=version.id,
                description="FICTIONAL minimum age is eighteen",
                subject_context="person",
                kind="eligibility",
                application_context="all",
                rule={
                    "op": "condition",
                    "condition": {"op": "gte", "fact": "age", "value": 18},
                    "children": [],
                },
            )
            session.add(age)
            session.flush()
            session.add(
                RequirementEvidence(
                    requirement_id=age.id,
                    source_url=source.url,
                    page="1",
                    passage="FICTIONAL policy: applicants must be at least eighteen.",
                )
            )
            req = Requirement(
                version_id=version.id,
                description="FICTIONAL parental income certificate needed",
                subject_context="person",
                kind="document",
                application_context="all",
                rule={
                    "op": "condition",
                    "condition": {
                        "op": "document",
                        "fact": "has_income_certificate",
                        "income_period": "fictional-2026",
                        "income_definition": "parental",
                    },
                    "children": [],
                },
            )
            session.add(req)
            session.flush()
            session.add(
                RequirementEvidence(
                    requirement_id=req.id,
                    source_url=source.url,
                    page="1",
                    passage="FICTIONAL parental income certificate for the 2026 test period.",
                )
            )
        # Fictional legacy record deliberately bypasses modern input validation at seed time.
        # It reproduces pre-existing hidden study answers, never real application data.
        import firebase_admin
        from firebase_admin import auth

        try:
            firebase_app = firebase_admin.get_app()
        except ValueError:
            firebase_app = firebase_admin.initialize_app(
                options={"projectId": "demo-opportunity-completion"}
            )
        try:
            auth.create_user(
                uid="fictional-legacy-education",
                email="legacy-education@example.invalid",
                password="Fictional-Only-123",
                app=firebase_app,
            )
        except auth.UidAlreadyExistsError:
            pass
        legacy_user = User(firebase_uid="fictional-legacy-education")
        session.add(legacy_user)
        session.flush()
        legacy = Person(user_id=legacy_user.id, display_name="Fictional legacy graduate")
        session.add(legacy)
        session.flush()
        for key, value in {
            "student_status": False,
            "education_level": "undergraduate",
            "enrollment_mode": "full_time",
            "school_recognized_or_government": True,
        }.items():
            session.add(
                ProfileFact(
                    person_id=legacy.id,
                    key=key,
                    value=value,
                    origin="user_supplied",
                    verification="unverified",
                    context={},
                )
            )
        session.commit()
    import uvicorn

    class DisposableServer(uvicorn.Server):
        @contextmanager
        def capture_signals(self):
            # Uvicorn normally re-raises SIGTERM before our outer finally can run.
            # Test-only process: finish graceful shutdown, then clean our own resources.
            previous = {
                sig: signal.signal(sig, self.handle_exit) for sig in (signal.SIGINT, signal.SIGTERM)
            }
            try:
                yield
            finally:
                for sig, handler in previous.items():
                    signal.signal(sig, handler)

    DisposableServer(
        uvicorn.Config(
            "opportunity_platform.main:app", host="127.0.0.1", port=18210, access_log=False
        )
    ).run()
finally:
    if "engine" in locals():
        engine.dispose()
    with admin.begin() as connection:
        connection.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
    admin.dispose()
    shutil.rmtree(root)
