"""Real PostgreSQL integration on disposable fictional data, no model calls."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import (
    ActionItem,
    Document,
    Household,
    HouseholdMembership,
    MatchEvaluation,
    Opportunity,
    OpportunityVersion,
    Person,
    ProfileFact,
    Requirement,
    RequirementEvidence,
    Source,
    User,
)
from opportunity_platform.eligibility.engine import FactRecord
from opportunity_platform.profiles.service import account
from opportunity_platform.retrieval.service import (
    SearchRequest,
    SearchSubject,
    load_catalogue,
    search,
    select_candidates,
)
from opportunity_platform.scenarios.service import ScenarioRequest, simulate


def fictional_catalogue(session, count=405):
    reviewer = User(firebase_uid="phase4-fictional-reviewer", is_admin=True)
    source = Source(
        name="FICTIONAL benchmark only",
        authority="Fictional",
        url="https://example.invalid/phase4",
        is_synthetic=True,
        status="verified",
    )
    session.add_all([reviewer, source])
    session.flush()
    categories = [
        "school",
        "higher_education",
        "state_support",
        "household",
        "startup",
        "MSME",
        "procurement",
        "unknown",
        "documentary",
    ]
    for i in range(count):
        category = categories[i % 9]
        kind = (
            "household"
            if category == "household"
            else "business"
            if category in {"startup", "MSME", "procurement"}
            else "person"
        )
        o = Opportunity(
            id=uuid.uuid5(uuid.NAMESPACE_URL, f"phase4-policy-{i}"),
            source_id=source.id,
            source_key=str(i),
            category=category,
            is_synthetic=True,
        )
        session.add(o)
        session.flush()
        v = OpportunityVersion(
            opportunity_id=o.id,
            version=1,
            publication_state="published",
            status="verified",
            title=f"FICTIONAL {category} policy {i}",
            summary=f"Fictional {category} exercise; no real benefit.",
            issuer="Fictional",
            category=category,
            country="IN",
            state="Rajasthan" if i % 3 == 0 else None,
            source_url=source.url,
            last_verified_at=datetime.now(timezone.utc),
            reviewer_id=reviewer.id,
        )
        session.add(v)
        session.flush()
        o.published_version_id = v.id
        if kind == "household":
            condition = {
                "op": "lte",
                "fact": "annual_household_income",
                "value": 100000 + i * 1000,
                "income_period": "2026-27",
                "income_definition": "explicit-demo-household",
            }
        elif kind == "business":
            condition = {
                "op": "lte",
                "fact": "business_turnover",
                "value": 1000000 + i * 10000,
                "income_period": "2026-27",
                "income_definition": "gross-turnover",
            }
        elif category == "unknown":
            condition = {"op": "unknown"}
        elif category == "documentary":
            condition = {
                "op": "document",
                "fact": "has_income_certificate",
                "income_period": "2026-27",
                "income_definition": "parental",
            }
        elif category == "school":
            condition = {"op": "lte", "fact": "age", "value": 17 + (i % 2)}
        elif category == "higher_education":
            condition = {"op": "gte", "fact": "age", "value": 18 + (i % 5)}
        else:
            condition = {
                "op": "lte",
                "fact": "annual_parental_income",
                "value": 200000 + i * 1000,
                "income_period": "2026-27",
                "income_definition": "parental",
            }
        r = Requirement(
            version_id=v.id,
            description=f"FICTIONAL {category} condition {i}",
            subject_context=kind,
            kind="eligibility",
            application_context="all",
            rule={"op": "condition", "condition": condition, "children": []},
        )
        session.add(r)
        session.flush()
        session.add(
            RequirementEvidence(
                requirement_id=r.id,
                source_url=source.url,
                page="1",
                passage=f"FICTIONAL condition {condition}",
            )
        )
    session.commit()


def counts(db):
    return {
        m.__tablename__: db.scalar(select(func.count()).select_from(m))
        for m in [
            ProfileFact,
            Person,
            Household,
            HouseholdMembership,
            MatchEvaluation,
            ActionItem,
            Document,
        ]
    }


def test_hybrid_exact_and_scenario_nonpersistence(db, monkeypatch):
    from opportunity_platform.core.config import settings

    monkeypatch.setattr(settings(), "enable_development_catalogue", True)
    fictional_catalogue(db, 90)
    user = account(db, "phase4-test")
    p = Person(user_id=user.id, display_name="Fictional adult")
    db.add(p)
    db.flush()
    db.add(
        ProfileFact(
            person_id=p.id,
            key="age",
            value=18,
            origin="user_supplied",
            verification="unverified",
            context={},
        )
    )
    db.commit()
    request = SearchRequest(mode="me", development=True)
    first = search(db, "phase4-test", request)
    assert first.assessed_pair_count == 50
    assert any(
        a.evaluation.status == "not_eligible_on_known_facts"
        for i in first.items
        for a in i.assessments
    )
    assert any(
        a.evaluation.status == "possibly_eligible_missing_information"
        for i in first.items
        for a in i.assessments
    )
    assert [i.opportunity.id for i in first.items] == [
        i.opportunity.id for i in search(db, "phase4-test", request).items
    ]
    before = counts(db)
    body = ScenarioRequest(
        base=request,
        overrides=[
            {
                "subject_key": f"person:{p.id}",
                "facts": [
                    {"key": "age", "value": 17},
                    {
                        "key": "annual_personal_income",
                        "value": 10**12,
                        "income_period": "2026-27",
                        "income_definition": "personal",
                    },
                ],
            }
        ],
        people=[
            {
                "key": "child",
                "name": "Fictional child",
                "relationship": "child",
                "facts": [{"key": "age", "value": 10}],
            }
        ],
        household_facts=[
            {
                "key": "annual_household_income",
                "value": 0,
                "income_period": "2026-27",
                "income_definition": "explicit-demo-household",
            }
        ],
    )
    result = simulate(db, "phase4-test", body)
    assert result.persistence == "none"
    assert any(c["change"] == "changed" for c in result.changes)
    assert any(
        c["change"] == "newly_retrieved" and c["subject_key"] == "scenario:household"
        for c in result.changes
    )
    assert any(c["subject_key"] == "scenario:person:child" for c in result.changes)
    assert result.plan.hypothetical
    assert result.plan.actions
    db.commit()  # Even a caller committing cannot save scenario objects.
    assert counts(db) == before
    with pytest.raises(APIError):
        search(db, "other-account", SearchRequest(mode="member", subject_id=p.id, development=True))
    with pytest.raises(APIError):
        simulate(
            db,
            "phase4-test",
            ScenarioRequest(
                base=request,
                overrides=[
                    {
                        "subject_key": f"person:{p.id}",
                        "facts": [{"key": "has_income_certificate", "value": True}],
                    }
                ],
            ),
        )


def test_large_fair_shortlist_and_national(db, monkeypatch):
    from opportunity_platform.core.config import settings

    monkeypatch.setattr(settings(), "enable_development_catalogue", True)
    fictional_catalogue(db)
    request = SearchRequest(development=True, q="school", state="Rajasthan")
    rows, reqs, _, fts = load_catalogue(db, request)
    assert any(v.state is None for _, v, _ in rows)
    assert fts
    subjects = [
        SearchSubject(
            "parent", "person", "Fictional parent", None, [FactRecord(id="f", key="age", value=90)]
        ),
        SearchSubject("child", "person", "Fictional child", None, []),
        SearchSubject("biz", "business", "Fictional business", None, []),
    ]
    pairs, _, total = select_candidates(rows, reqs, subjects, request, fts)
    assert len(pairs) == 150 and total > 150
    assert {s.key: sum(t.key == s.key for t, _ in pairs) for s in subjects} == {
        "parent": 50,
        "child": 50,
        "biz": 50,
    }
    assert len({(s.key, o.id) for s, (o, _, _) in pairs}) == 150
    result = search(db, "unused", request, subjects)
    assert result.truncated
    assert result.category_coverage.keys() >= {
        "school",
        "higher_education",
        "unknown",
        "procurement",
    }


def test_private_routes_require_firebase(client):
    assert client.post("/v1/search", json={"mode": "me"}).status_code == 401
    assert client.post("/v1/scenarios/evaluate", json={"base": {"mode": "me"}}).status_code == 401
