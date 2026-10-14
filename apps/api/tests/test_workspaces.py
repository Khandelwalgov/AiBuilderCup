from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select
from test_pipeline import approve, candidate, pipeline, version  # noqa: F401

from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import (
    BusinessMembership,
    ConsentGrant,
    MatchEvaluation,
    Opportunity,
    OpportunityVersion,
    ProfileFact,
    User,
)
from opportunity_platform.eligibility import service as eligibility
from opportunity_platform.eligibility.rules import FactInput
from opportunity_platform.ingestion import service as ingestion
from opportunity_platform.planning import service as planning
from opportunity_platform.profiles.service import ProfileWrite, save_profile
from opportunity_platform.subjects import service as subjects


def setup_person(db, uid="fictional-owner"):
    return save_profile(
        db,
        uid,
        ProfileWrite(display_name="Fictional owner", facts=[FactInput(key="age", value=30)]),
    )


def test_household_guardian_revocation_and_no_adult_leak(db):
    setup_person(db)
    setup_person(db, "fictional-other")
    h = subjects.create_household(
        db, "fictional-owner", subjects.HouseholdWrite(name="Fictional household")
    )
    d = subjects.add_dependent(
        db,
        "fictional-owner",
        h.id,
        subjects.DependentWrite(
            display_name="Fictional dependent",
            facts=[FactInput(key="age", value=12)],
            guardian_responsibility_confirmed=True,
            relationship="parent",
        ),
    )
    assert subjects.view(db, "fictional-owner", subjects.SubjectRef(id=d.id)).facts[0].value == 12
    for ref in [subjects.SubjectRef(kind="household", id=h.id), subjects.SubjectRef(id=d.id)]:
        with pytest.raises(APIError):
            subjects.view(db, "fictional-other", ref)
    with pytest.raises(APIError):
        subjects.update_person(
            db, "fictional-other", d.id, ProfileWrite(display_name="Forbidden", facts=[])
        )
    grant = db.scalar(select(ConsentGrant).where(ConsentGrant.person_id == d.id))
    grant.revoked_at = datetime.now(timezone.utc)
    db.commit()
    with pytest.raises(APIError):
        subjects.view(db, "fictional-owner", subjects.SubjectRef(id=d.id))
    assert (
        subjects.view(
            db, "fictional-owner", subjects.SubjectRef(kind="household", id=h.id)
        ).members[1]["access"]
        == "restricted"
    )
    # Household facts remain separate and empty; no automatic income aggregation.
    assert (
        subjects.view(db, "fictional-owner", subjects.SubjectRef(kind="household", id=h.id)).facts
        == []
    )


def test_business_role_permissions_and_unregistered(db):
    setup_person(db)
    setup_person(db, "fictional-viewer")
    data = subjects.BusinessWrite(
        name="Fictional unregistered enterprise",
        legal_status="unregistered",
        facts=[FactInput(key="business_registered", value=False)],
    )
    b = subjects.save_business(db, "fictional-owner", data)
    with pytest.raises(APIError):
        subjects.view(db, "fictional-viewer", subjects.SubjectRef(kind="business", id=b.id))
    viewer = db.scalar(select(User).where(User.firebase_uid == "fictional-viewer"))
    db.add(BusinessMembership(user_id=viewer.id, business_id=b.id, role="viewer"))
    db.commit()
    assert (
        subjects.view(db, "fictional-viewer", subjects.SubjectRef(kind="business", id=b.id)).role
        == "viewer"
    )
    with pytest.raises(APIError):
        subjects.save_business(db, "fictional-viewer", data, b.id)
    db.scalar(
        select(BusinessMembership).where(BusinessMembership.user_id == viewer.id)
    ).role = "editor"
    db.commit()
    assert subjects.save_business(db, "fictional-viewer", data, b.id).name == data.name


def publish_two(db, pipeline):  # noqa: F811
    actor, _ = pipeline
    ingestion.ingest(db, "depwd-pre-matric", actor)
    v = version(db)
    approve(db, actor, v)
    first = db.get(Opportunity, v.opportunity_id)
    second = Opportunity(
        source_id=first.source_id,
        source_key="fictional-distinct-test-only",
        category="education",
        is_synthetic=False,
    )
    db.add(second)
    db.flush()
    other = OpportunityVersion(
        opportunity_id=second.id,
        version=1,
        snapshot_id=v.snapshot_id,
        extraction=candidate().model_dump(mode="json"),
        title="Fictional second test opportunity",
        summary=v.summary,
        source_url=v.source_url,
        content_hash=v.content_hash,
    )
    db.add(other)
    db.commit()
    approve(db, actor, other)
    return first, second


def test_shared_action_simulation_and_subject_context(db, pipeline):  # noqa: F811
    first, second = publish_two(db, pipeline)
    setup_person(db)
    ref = subjects.SubjectRef()
    real = planning.build(db, "fictional-owner", ref)
    shared = [a for a in real.actions if a.kind == "document"]
    assert len(shared) == 1
    assert len({o["id"] for o in shared[0].opportunities}) == 2
    count = db.scalar(select(func.count()).select_from(MatchEvaluation))
    facts_before = db.scalar(select(func.count()).select_from(ProfileFact))
    simulated = planning.build(db, "fictional-owner", ref, [FactInput(key="age", value=12)])
    assert all(e.status == "not_eligible_on_known_facts" for e in simulated.evaluations)
    assert db.scalar(select(func.count()).select_from(MatchEvaluation)) == count
    assert db.scalar(select(func.count()).select_from(ProfileFact)) == facts_before
    assert all(
        e.status == "potential_match" or e.status == "possibly_eligible_missing_information"
        for e in real.evaluations
    )
    assert simulated.actions[0].kind == "document"  # No fake verification.
    h = subjects.create_household(
        db, "fictional-owner", subjects.HouseholdWrite(name="Fictional family")
    )
    household = eligibility.check(
        db, "fictional-owner", first.id, subjects.SubjectRef(kind="household", id=h.id)
    )
    assert all(r.result.outcome == "unknown" for r in household.requirements)
