"""Meaning/period cases shared with actual browser evaluation of the generated specification."""

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

from opportunity_platform.core.auth import current_uid
from opportunity_platform.db.models import ProfileFact
from opportunity_platform.eligibility.engine import FactRecord, evaluate
from opportunity_platform.eligibility.rules import Condition, FactInput, Rule
from opportunity_platform.main import app
from opportunity_platform.profiles.semantics import SPEC, issues
from opportunity_platform.profiles.service import ProfileWrite, save_profile

CASES = json.loads(
    (Path(__file__).resolve().parents[3] / "data/fixtures/domain-semantic-cases.json").read_text()
)
TODAY = date(2026, 10, 16)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_shared_meaning_specification(case):
    result = issues(
        [FactInput(**f) for f in case["facts"]], [FactInput(**f) for f in case["before"]], TODAY
    )
    assert [i["code"] + ":" + i["severity"] for i in result] == case["expected"]
    for issue in result:
        assert issue["fields"] and len(issue["message"]) == 2 and issue["same_active_period"]


def test_generated_spec_is_identical():
    path = (
        Path(__file__).resolve().parents[3]
        / "apps/web/src/features/profiles/semantics.generated.json"
    )
    assert json.loads(path.read_text()) == SPEC


def record(key, value, **kw):
    return FactRecord(id=key, key=key, value=value, **kw)


def leaf(key, value, **kw):
    return Rule(op="condition", condition=Condition(op="eq", fact=key, value=value, **kw))


def test_current_completed_legacy_and_historical_are_separate():
    facts = [
        record("highest_completed_education", "undergraduate"),
        record("student_status", True),
        record("current_education_level", "postgraduate"),
    ]
    assert (
        evaluate(leaf("highest_completed_education", "undergraduate"), facts, TODAY).outcome
        == "satisfied"
    )
    assert (
        evaluate(leaf("current_education_level", "postgraduate"), facts, TODAY).outcome
        == "satisfied"
    )
    assert (
        evaluate(leaf("highest_completed_education", "postgraduate"), facts, TODAY).outcome
        == "unsatisfied"
    )
    assert evaluate(leaf("education_level", "undergraduate"), facts, TODAY).outcome == "unknown"
    facts[1] = record("student_status", False)
    assert (
        evaluate(leaf("current_education_level", "postgraduate"), facts, TODAY).outcome
        == "unsatisfied"
    )
    facts[1] = record("student_status", True, valid_until=date(2025, 12, 31))
    assert (
        evaluate(leaf("current_education_level", "postgraduate"), facts, TODAY).outcome == "unknown"
    )
    facts[1] = record("student_status", True)
    facts[2] = record("current_education_level", "postgraduate", valid_until=date(2025, 12, 31))
    assert (
        evaluate(leaf("current_education_level", "postgraduate"), facts, TODAY).outcome == "unknown"
    )


def test_multiple_income_definitions_and_zero_are_scoped_before_conflicts():
    rule = Rule(
        op="condition",
        condition=Condition(
            op="lte",
            fact="annual_parental_income",
            value=1000,
            income_period="2026",
            income_definition="parents",
        ),
    )
    facts = [
        record(
            "annual_parental_income",
            0,
            context={"income_period": "2026", "income_definition": "parents"},
        ),
        record(
            "annual_parental_income",
            90000,
            context={"income_period": "2025", "income_definition": "household"},
        ),
    ]
    assert evaluate(rule, facts, TODAY).outcome == "satisfied"
    assert evaluate(rule, facts[1:], TODAY).outcome == "unknown"
    assert evaluate(rule, [record("annual_parental_income", 0)], TODAY).outcome == "unknown"
    facts.append(
        record(
            "annual_parental_income",
            500,
            context={"income_period": "2026", "income_definition": "parents"},
        )
    )
    assert evaluate(rule, facts, TODAY).outcome == "unknown"


def test_api_precise_errors_retained_legacy_and_archived_history(client, db):
    app.dependency_overrides[current_uid] = lambda: "fictional-semantic"
    first = save_profile(
        db, "fictional-semantic", ProfileWrite(display_name="Fictional graduate", facts=[])
    )
    db.add(
        ProfileFact(
            person_id=first.id,
            key="enrollment_mode",
            value="full_time",
            origin="user_supplied",
            verification="unverified",
            context={},
        )
    )
    db.add(
        ProfileFact(
            person_id=first.id,
            key="student_status",
            value=False,
            origin="user_supplied",
            verification="unverified",
            context={},
        )
    )
    db.commit()
    payload = {
        "display_name": "Fictional graduate",
        "facts": [
            {"key": "student_status", "value": False},
            {"key": "enrollment_mode", "value": "full_time"},
            {"key": "highest_completed_education", "value": "undergraduate"},
        ],
    }
    # Existing broken/ambiguous legacy details remain visible warnings, not a hidden save trap.
    assert client.put("/v1/profile/me", json=payload).status_code == 200
    payload["facts"][1]["valid_until"] = "2025-12-31"
    assert client.put("/v1/profile/me", json=payload).status_code == 200
    row = db.scalar(
        select(ProfileFact).where(
            ProfileFact.person_id == first.id, ProfileFact.key == "enrollment_mode"
        )
    )
    assert row.value == "full_time" and row.context["history"][0]["value"] == "full_time"
    payload["facts"][1].pop("valid_until")
    failure = client.put("/v1/profile/me", json=payload)
    assert failure.status_code == 422 and failure.json()["error"]["code"] == "semantic_conflict"
    assert failure.json()["error"]["issues"][0]["fields"] == ["student_status", "enrollment_mode"]
    db.rollback()
    invalid = client.put(
        "/v1/profile/me", json={"display_name": "Fictional", "facts": [{"key": "age", "value": -1}]}
    )
    assert invalid.json()["error"]["code"] == "invalid_value"
    assert invalid.json()["error"]["issues"][0]["fields"] == ["age"]
    wrong = client.put(
        "/v1/profile/me",
        json={"display_name": "Fictional", "facts": [{"key": "business_turnover", "value": 0}]},
    )
    assert wrong.json()["error"]["code"] == "subject_fact_mismatch"
    db.rollback()


def test_age_as_of_and_current_school_scope_require_temporal_evidence():
    current = record("age", 20, context={"recorded_at": "2026-10-16T00:00:00+00:00"})
    assert (
        evaluate(leaf("age", 20, as_of=date(2025, 10, 16)), [current], TODAY).outcome == "unknown"
    )
    assert evaluate(leaf("age", 20, as_of=TODAY), [current], TODAY).outcome == "satisfied"
    assert (
        evaluate(leaf("age", 20, as_of=date(2027, 10, 16)), [current], TODAY).outcome == "unknown"
    )
    school = leaf("school_recognized_or_government", True)
    facts = [record("student_status", True), record("school_recognized_or_government", True)]
    assert evaluate(school, facts, TODAY).outcome == "unknown"
    facts.append(record("current_education_level", "IX"))
    assert evaluate(school, facts, TODAY).outcome == "satisfied"
    facts[-1] = record("current_education_level", "undergraduate")
    assert evaluate(school, facts, TODAY).outcome == "unknown"


def test_enrollment_dependency_changes_fingerprint_and_persisted_result(db):
    from opportunity_platform.core.config import settings
    from opportunity_platform.db.models import (
        MatchEvaluation,
        Opportunity,
        OpportunityVersion,
        Requirement,
        Source,
        User,
    )
    from opportunity_platform.eligibility.refresh import keys
    from opportunity_platform.eligibility.service import check

    source = Source(
        name="FICTIONAL meaning policy",
        authority="Fictional",
        url="https://example.invalid/meaning",
        is_synthetic=True,
        status="verified",
    )
    db.add(source)
    db.flush()
    owner = User(firebase_uid="fictional-meaning-reviewer", is_admin=True)
    db.add(owner)
    db.flush()
    op = Opportunity(
        source_id=source.id, source_key="meaning", category="education", is_synthetic=True
    )
    db.add(op)
    db.flush()
    v = OpportunityVersion(
        opportunity_id=op.id,
        version=1,
        publication_state="published",
        status="verified",
        title="FICTIONAL meaning",
        summary="Fictional",
        issuer="Fictional",
        source_url=source.url,
        reviewer_id=owner.id,
        last_verified_at=datetime.now(timezone.utc),
    )
    db.add(v)
    db.flush()
    op.published_version_id = v.id
    rule = leaf("current_education_level", "postgraduate")
    db.add(
        Requirement(
            version_id=v.id,
            description="FICTIONAL current postgraduate course",
            subject_context="person",
            rule=rule.model_dump(mode="json"),
        )
    )
    db.commit()
    previous = settings().enable_development_catalogue
    settings().enable_development_catalogue = True
    try:
        data = ProfileWrite(
            display_name="Fictional",
            facts=[
                FactInput(key="student_status", value=True),
                FactInput(key="current_education_level", value="postgraduate"),
            ],
        )
        save_profile(db, "fictional-current-course", data)
        first = check(db, "fictional-current-course", op.id, development=True)
        assert first.requirements[0].result.outcome == "satisfied"
        archived = [
            FactInput(key="student_status", value=False),
            FactInput(
                key="current_education_level", value="postgraduate", valid_until=date(2025, 12, 31)
            ),
        ]
        save_profile(
            db, "fictional-current-course", ProfileWrite(display_name="Fictional", facts=archived)
        )
        second = check(db, "fictional-current-course", op.id, development=True)
        assert first.id != second.id and second.requirements[0].result.outcome == "unsatisfied"
        assert db.get(MatchEvaluation, first.id).results[0]["result"]["outcome"] == "satisfied"
        assert "student_status" in keys(rule)
        req = db.scalar(select(Requirement).where(Requirement.version_id == v.id))
        req.application_context = "renewal"
        db.commit()
        fresh = check(
            db, "fictional-current-course", op.id, application_type="fresh", development=True
        )
        assert fresh.requirements[0].result.outcome == "not_applicable"
        assert fresh.status == "possibly_eligible_missing_information"
    finally:
        settings().enable_development_catalogue = previous


def test_nationality_representation_does_not_reject_indian_country_code():
    for answer in ["IN", "Indian", "India", "भारतीय"]:
        assert (
            evaluate(leaf("nationality", "Indian"), [record("nationality", answer)], TODAY).outcome
            == "satisfied"
        )
    assert (
        evaluate(leaf("nationality", "IN"), [record("nationality", "other")], TODAY).outcome
        == "unknown"
    )
    assert (
        evaluate(leaf("nationality", "IN"), [record("nationality", "Nepali")], TODAY).outcome
        == "unsatisfied"
    )


@pytest.mark.parametrize(
    "key,value",
    [
        ("current_education_level", "none"),
        ("current_education_level", "unmapped_course"),
        ("highest_completed_education", "unmapped_award"),
        ("business_operating_status", "invented_status"),
    ],
)
def test_new_fact_choices_are_closed(key, value):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        FactInput(key=key, value=value)


def test_location_language_aliases_do_not_mix_residence_domicile_or_registration():
    facts = [
        record("domicile_state", "राजस्थान"),
        record("residence_state", "Delhi"),
        record("business_registration_state", "महाराष्ट्र"),
    ]
    assert evaluate(leaf("domicile_state", "Rajasthan"), facts, TODAY).outcome == "satisfied"
    assert evaluate(leaf("residence_state", "Rajasthan"), facts, TODAY).outcome == "unsatisfied"
    assert (
        evaluate(leaf("business_registration_state", "Maharashtra"), facts, TODAY).outcome
        == "satisfied"
    )
    assert (
        evaluate(
            leaf("residence_state", "Unmapped"), [record("residence_state", "अज्ञात स्थान")], TODAY
        ).outcome
        == "unknown"
    )


def test_zero_income_with_verified_evidence_requires_the_same_period_and_definition():
    amount = Rule(
        op="condition",
        condition=Condition(
            op="lte",
            fact="annual_parental_income",
            value=1000,
            income_period="2026",
            income_definition="parents",
        ),
    )
    certificate = Rule(
        op="condition",
        condition=Condition(
            op="document",
            fact="has_income_certificate",
            income_period="2026",
            income_definition="parents",
        ),
    )
    rule = Rule(op="all", children=[amount, certificate])
    scope = {"income_period": "2026", "income_definition": "parents"}
    facts = [
        record("annual_parental_income", 0, context=scope),
        record(
            "has_income_certificate",
            True,
            origin="verified_document",
            verification="verified",
            context=scope,
        ),
    ]
    assert evaluate(rule, facts, TODAY).outcome == "satisfied"
    facts[-1].context = {"income_period": "2025", "income_definition": "parents"}
    assert evaluate(rule, facts, TODAY).outcome == "unknown"
    facts[-1].context = {"income_period": "2026", "income_definition": "household"}
    assert evaluate(rule, facts, TODAY).outcome == "unknown"
    facts[-1].context = scope
    facts[-1].origin = "user_supplied"
    assert evaluate(rule, facts, TODAY).outcome == "unknown"
