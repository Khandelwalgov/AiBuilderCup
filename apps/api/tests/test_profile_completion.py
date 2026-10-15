import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import AuditEvent, ProfileFact
from opportunity_platform.eligibility.rules import FactInput
from opportunity_platform.profiles.service import ProfileWrite, save_profile
from opportunity_platform.subjects import service as subjects


def test_repeat_save_preserves_fact_identity_and_audit_and_partial_changes(db):
    payload = ProfileWrite(
        display_name="Fictional learner",
        facts=[FactInput(key="age", value=20), FactInput(key="student_status", value=True)],
    )
    first = save_profile(db, "profile-completion", payload)
    rows = {f.key: f.id for f in first.facts}
    before_count = db.scalar(select(func.count()).select_from(AuditEvent))
    repeated = save_profile(db, "profile-completion", payload)
    assert {f.key: f.id for f in repeated.facts} == rows
    assert repeated.revision == first.revision
    assert db.scalar(select(func.count()).select_from(AuditEvent)) == before_count
    evidence = ProfileFact(
        person_id=first.id,
        key="has_income_certificate",
        value=True,
        origin="verified_document",
        verification="verified",
        context={},
    )
    db.add(evidence)
    db.commit()
    changed = save_profile(
        db,
        "profile-completion",
        ProfileWrite(
            display_name=payload.display_name,
            facts=[FactInput(key="age", value=21), FactInput(key="student_status", value=True)],
        ),
    )
    assert {f.key: f.id for f in changed.facts}["student_status"] == rows["student_status"]
    assert db.get(ProfileFact, evidence.id).verification == "verified"
    with pytest.raises(APIError) as caught:
        save_profile(
            db,
            "profile-completion",
            payload.model_copy(update={"expected_revision": first.revision}),
        )
    assert caught.value.code == "profile_conflict"
    db.rollback()


def test_dependent_repeat_save_and_stale_revision(db):
    save_profile(
        db, "guardian-completion", ProfileWrite(display_name="Fictional guardian", facts=[])
    )
    home = subjects.create_household(
        db, "guardian-completion", subjects.HouseholdWrite(name="Fictional home")
    )
    child = subjects.add_dependent(
        db,
        "guardian-completion",
        home.id,
        subjects.DependentWrite(
            display_name="Fictional child",
            facts=[FactInput(key="age", value=12)],
            relationship="parent",
            guardian_responsibility_confirmed=True,
        ),
    )
    data = ProfileWrite(
        display_name=child.name,
        facts=[FactInput(key="age", value=12)],
        expected_revision=child.revision,
    )
    repeated = subjects.update_person(db, "guardian-completion", child.id, data)
    assert repeated.facts[0].id == child.facts[0].id and repeated.revision == child.revision
    subjects.update_person(
        db,
        "guardian-completion",
        child.id,
        data.model_copy(update={"display_name": "New fictional name"}),
    )
    with pytest.raises(APIError) as caught:
        subjects.update_person(db, "guardian-completion", child.id, data)
    assert caught.value.code == "profile_conflict"
    db.rollback()


def test_contradictory_study_answers_rejected_but_prior_education_preserved():
    with pytest.raises(ValidationError):
        ProfileWrite(
            display_name="Fictional learner",
            facts=[
                FactInput(key="student_status", value=False),
                FactInput(key="enrollment_mode", value="full_time"),
            ],
        )
    with pytest.raises(ValidationError):
        ProfileWrite(
            display_name="Fictional learner",
            facts=[
                FactInput(key="education_level", value="undergraduate"),
                FactInput(key="school_recognized_or_government", value=True),
            ],
        )
    ProfileWrite(
        display_name="Fictional graduate",
        facts=[
            FactInput(key="student_status", value=False),
            FactInput(key="education_level", value="undergraduate"),
        ],
    )


def test_simultaneous_edits_have_one_winner(db):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy.orm import Session

    initial = save_profile(
        db,
        "concurrent-completion",
        ProfileWrite(display_name="Fictional concurrent", facts=[FactInput(key="age", value=20)]),
    )
    barrier = Barrier(2)

    def change(age):
        with Session(db.get_bind()) as other:
            barrier.wait(timeout=5)
            try:
                result = save_profile(
                    other,
                    "concurrent-completion",
                    ProfileWrite(
                        display_name=initial.display_name,
                        facts=[FactInput(key="age", value=age)],
                        expected_revision=initial.revision,
                    ),
                )
                return result.facts[0].value
            except APIError as error:
                other.rollback()
                return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(change, [21, 22]))
    assert results.count("profile_conflict") == 1
    assert any(result in [21, 22] for result in results)
