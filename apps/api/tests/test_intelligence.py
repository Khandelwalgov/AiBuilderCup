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
    unchanged = simulate(db, "phase4-test", ScenarioRequest(base=request))
    assert all(c["change"] == "unchanged" for c in unchanged.changes)
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
    actual_ids = {item.opportunity.id for item in result.actual.items}
    assert any(item.opportunity.id not in actual_ids for item in result.hypothetical.items)
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


def test_small_catalogue_empty_query_evaluates_all_family_pairs(db, monkeypatch):
    from opportunity_platform.core.config import settings

    monkeypatch.setattr(settings(), "enable_development_catalogue", True)
    fictional_catalogue(db, 90)
    request = SearchRequest(development=True, shortlist=50)
    subjects = [
        SearchSubject(str(i), "person", f"Fictional member {i}", None, []) for i in range(5)
    ]
    result = search(db, "unused", request, subjects)
    assert result.assessed_pair_count == result.eligible_pair_count == 250
    assert not result.truncated
    assert result.subject_coverage == {str(i): 50 for i in range(5)}


def test_private_routes_require_firebase(client):
    assert client.post("/v1/search", json={"mode": "me"}).status_code == 401
    assert client.post("/v1/scenarios/evaluate", json={"base": {"mode": "me"}}).status_code == 401


def test_family_authorized_members_and_household_income_scope(db, monkeypatch):
    from opportunity_platform.core.config import settings
    from opportunity_platform.eligibility.rules import FactInput
    from opportunity_platform.profiles.service import ProfileWrite, save_profile
    from opportunity_platform.subjects import service as subjects

    monkeypatch.setattr(settings(), "enable_development_catalogue", True)
    fictional_catalogue(db, 27)
    save_profile(
        db,
        "family-test",
        ProfileWrite(display_name="Fictional parent", facts=[FactInput(key="age", value=40)]),
    )
    home = subjects.create_household(
        db, "family-test", subjects.HouseholdWrite(name="Fictional family")
    )
    child = subjects.add_dependent(
        db,
        "family-test",
        home.id,
        subjects.DependentWrite(
            display_name="Fictional child",
            facts=[FactInput(key="age", value=10)],
            guardian_responsibility_confirmed=True,
            relationship="parent",
        ),
    )
    stranger = account(db, "private-adult")
    adult = Person(user_id=stranger.id, display_name="PRIVATE ADULT NEVER EXPOSED")
    db.add(adult)
    db.flush()
    from datetime import date

    db.add(HouseholdMembership(household_id=home.id, person_id=adult.id, starts_on=date.today()))
    db.commit()
    result = search(
        db, "family-test", SearchRequest(mode="family", subject_id=home.id, development=True)
    )
    assert len(result.subjects) == 3
    assert "PRIVATE ADULT" not in result.model_dump_json()
    assert {
        a.subject_key for i in result.items for a in i.assessments if a.subject_kind == "person"
    } >= {f"person:{child.id}"}
    school = next(i for i in result.items if i.opportunity.category == "school")
    assert {a.evaluation.status for a in school.assessments} == {
        "potential_match",
        "not_eligible_on_known_facts",
    }
    hh = next(a for i in result.items for a in i.assessments if a.subject_kind == "household")
    assert hh.evaluation.status == "possibly_eligible_missing_information"
    subjects.revoke_guardian_access(db, "family-test", child.id)
    after = search(
        db, "family-test", SearchRequest(mode="family", subject_id=home.id, development=True)
    )
    assert f"person:{child.id}" not in after.subject_coverage
    assert len(after.subjects) == 2
    with pytest.raises(APIError):
        simulate(
            db,
            "family-test",
            ScenarioRequest(
                base=SearchRequest(mode="family", subject_id=home.id, development=True),
                overrides=[
                    {"subject_key": f"person:{child.id}", "facts": [{"key": "age", "value": 10}]}
                ],
            ),
        )


def test_new_unreviewed_draft_never_replaces_published_index_version(db, monkeypatch):
    from opportunity_platform.core.config import settings

    monkeypatch.setattr(settings(), "enable_development_catalogue", True)
    fictional_catalogue(db, 9)
    request = SearchRequest(development=True)
    rows, _, _, _ = load_catalogue(db, request)
    o, v, _ = rows[0]
    db.add(
        OpportunityVersion(
            opportunity_id=o.id,
            version=2,
            publication_state="draft",
            status="needs_review",
            title="UNREVIEWED DRAFT NEVER RETRIEVED",
            summary="draft",
            issuer="Fictional",
            country="IN",
        )
    )
    db.commit()
    after, _, _, _ = load_catalogue(db, request)
    assert len(after) == len(rows)
    assert next(version for op, version, _ in after if op.id == o.id).id == v.id


def test_exact_income_boundary_and_large_changes_do_not_filter_candidates(db, monkeypatch):
    from opportunity_platform.core.config import settings

    monkeypatch.setattr(settings(), "enable_development_catalogue", True)
    fictional_catalogue(db, 9)
    user = account(db, "income-boundary")
    p = Person(user_id=user.id, display_name="Fictional income boundary")
    db.add(p)
    db.flush()
    db.add(
        ProfileFact(
            person_id=p.id,
            key="annual_parental_income",
            value=202000,
            origin="user_supplied",
            verification="unverified",
            context={"income_period": "2026-27", "income_definition": "parental"},
        )
    )
    db.commit()
    request = SearchRequest(development=True)
    actual = search(db, "income-boundary", request)
    target = next(i for i in actual.items if i.opportunity.category == "state_support")
    assert target.assessments[0].evaluation.status == "potential_match"
    for income in [202001, 10**12]:
        response = simulate(
            db,
            "income-boundary",
            ScenarioRequest(
                base=request,
                overrides=[
                    {
                        "subject_key": f"person:{p.id}",
                        "facts": [
                            {
                                "key": "annual_parental_income",
                                "value": income,
                                "income_period": "2026-27",
                                "income_definition": "parental",
                            }
                        ],
                    }
                ],
            ),
        )
        item = next(
            i for i in response.hypothetical.items if i.opportunity.id == target.opportunity.id
        )
        assert item.assessments[0].evaluation.status == "not_eligible_on_known_facts"
    wrong_scope = simulate(
        db,
        "income-boundary",
        ScenarioRequest(
            base=request,
            overrides=[
                {
                    "subject_key": f"person:{p.id}",
                    "facts": [
                        {
                            "key": "annual_parental_income",
                            "value": 0,
                            "income_period": "2026-27",
                            "income_definition": "household",
                        }
                    ],
                }
            ],
        ),
    )
    item = next(
        i for i in wrong_scope.hypothetical.items if i.opportunity.id == target.opportunity.id
    )
    assert item.assessments[0].evaluation.status == "possibly_eligible_missing_information"
