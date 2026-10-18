"""Research discovery cannot be misconstrued as an eligibility result."""

import uuid
from datetime import date
from types import SimpleNamespace

import pytest

from opportunity_platform.eligibility.engine import FactRecord
from opportunity_platform.eligibility.rules import FactInput
from opportunity_platform.research.guidance import (
    GuidanceRequest,
    guidance,
    location_signals,
    with_overrides,
)
from opportunity_platform.research.schemas import ResearchCard


def fact(key, value):
    return FactRecord(id=str(uuid.uuid4()), key=key, value=value)


def test_domicile_can_prioritize_research_but_not_eligibility():
    score, signal, why = location_signals(
        "Rajasthan", [fact("domicile_state", "Rajasthan")], "person"
    )
    assert score == 4 and signal == "saved_domicile"
    assert "location" in why.lower()
    assert location_signals("India", [], "person")[0] == 2
    assert location_signals("Gujarat", [fact("domicile_state", "Rajasthan")], "person")[0] == 0
    assert location_signals("Rajasthan", [], "person")[0] == 1
    assert location_signals("Rajasthan", [fact("residence_state", "Rajasthan")], "person")[0] == 3


def test_simulated_location_replaces_and_does_not_persist_baseline():
    baseline = [fact("domicile_state", "Rajasthan"), fact("age", 22)]
    hypothetical = with_overrides(baseline, [FactInput(key="domicile_state", value="Gujarat")])
    assert baseline[0].value == "Rajasthan"
    assert next(f.value for f in hypothetical if f.key == "domicile_state") == "Gujarat"
    with pytest.raises(ValueError, match="distinct"):
        with_overrides(baseline, [FactInput(key="age", value=25), FactInput(key="age", value=26)])


def research_card(title, jurisdiction, archive=False):
    return ResearchCard(
        id=uuid.uuid4(),
        key=title.lower().replace(" ", "-"),
        title=title,
        authority="Official agency",
        category="education",
        jurisdiction=jurisdiction,
        district=None,
        kind="scheme",
        summary="Official source describes educational financial assistance.",
        benefit="Fee support described by source",
        availability="unknown",
        availability_note="Current year and available budget not verified.",
        application_status="not_established",
        apply_url=None,
        closes_on=None,
        as_of=date(2026, 10, 17),
        source_url="https://example.gov.in/file.pdf",
        source_count=1,
        archive=archive,
        documents=[],
    )


def test_guidance_public_records_only_and_no_false_eligibility(monkeypatch):
    import sys

    from opportunity_platform.research import guidance as module

    rows = [
        SimpleNamespace(id="rajasthan", name="rajasthan", identity_key="test-rajasthan"),
        SimpleNamespace(id="india", name="india", identity_key="test-india"),
        SimpleNamespace(id="archive", name="archive", identity_key="test-archive"),
    ]
    view = {
        "rajasthan": research_card("Scholarship Rajasthan", "Rajasthan"),
        "india": research_card("Scholarship National", "India"),
        "archive": research_card("Old tender", "Rajasthan", True),
    }
    monkeypatch.setattr(
        module,
        "resolve",
        lambda session, uid, ref, **kwargs: (None, SimpleNamespace(id=uuid.uuid4()), None),
    )
    monkeypatch.setattr(
        module,
        "subject_facts",
        lambda session, kind, identifier: [fact("domicile_state", "Rajasthan")],
    )
    monkeypatch.setattr(
        module, "quality", lambda row: {"evidence_strength": "substantive_document"}
    )
    # `guidance` imports `card` when executed, so the route can remain independent from these tests.
    monkeypatch.setitem(
        sys.modules,
        "opportunity_platform.research.router",
        SimpleNamespace(card=lambda row: view[row.name]),
    )
    result = guidance(
        SimpleNamespace(scalars=lambda statement: rows), "valid-user", GuidanceRequest()
    )
    assert result.candidate_count == 2
    assert len(result.items) == 2
    assert all(item.eligibility_verified is False for item in result.items)
    assert result.eligible_count == 0
    assert result.items[0].listing.jurisdiction == "Rajasthan"
    assert any("application route" in step for step in result.items[0].next_steps)


def test_expired_future_and_conflicting_locations_are_unknown():
    records = [
        fact("domicile_state", "Rajasthan").model_copy(update={"valid_until": date(2020, 1, 1)}),
        fact("residence_state", "Gujarat").model_copy(update={"valid_from": date(2099, 1, 1)}),
    ]
    assert location_signals("Rajasthan", records, "person")[1] == "needs_location_check"
    assert (
        location_signals(
            "Rajasthan",
            [fact("domicile_state", "Rajasthan"), fact("domicile_state", "Gujarat")],
            "person",
        )[1]
        == "needs_location_check"
    )
    assert (
        location_signals(
            "Rajasthan", [fact("business_registration_state", "Rajasthan")], "business"
        )[1]
        == "saved_business_registration"
    )


@pytest.fixture
def real_guidance(client, db):
    from test_research_catalogue import research_baseline

    from opportunity_platform.profiles.service import ProfileWrite, save_profile
    from opportunity_platform.research.importer import import_listings

    # Reuse the complete frozen real-public-source bundle; only the account is fictional.
    data, listings, actor = research_baseline.__wrapped__(db)
    import_listings(
        db, listings, actor, make_public=True, captured_sources=data["captured_sources"]
    )
    save_profile(
        db,
        "fictional-research-owner",
        ProfileWrite(
            display_name="Fictional research owner",
            facts=[FactInput(key="domicile_state", value="Rajasthan")],
        ),
    )
    # Complete already-captured public evidence pages, never new acquisition or changed snapshots.
    import json
    from pathlib import Path

    from opportunity_platform.db.models import SourceSnapshot

    evidence = json.loads(
        (
            Path(__file__).resolve().parents[3] / "data/research/condition-evidence-v2.json"
        ).read_text()
    )
    for source in evidence["sources"]:
        snapshot = db.get(SourceSnapshot, source["snapshot_id"])
        assert snapshot and snapshot.content_hash == source["content_hash"]
        assert snapshot.source_url == source["source_url"]
        pages = {p["page"]: p for p in snapshot.pages}
        for page in source["pages"]:
            pages[page["page"]] = page
        snapshot.pages = list(pages.values())
    db.commit()
    return client, db


def test_authenticated_guidance_is_private_nonpersistent_and_not_eligibility(real_guidance):
    import copy

    from sqlalchemy import select

    from opportunity_platform.core.auth import current_uid
    from opportunity_platform.db.models import OpportunityVersion, ProfileFact, ResearchListing
    from opportunity_platform.main import app

    client, db = real_guidance
    assert client.post("/v1/research-opportunities/guidance", json={}).status_code == 401
    app.dependency_overrides[current_uid] = lambda: "fictional-research-owner"
    before = [(str(f.id), f.key, copy.deepcopy(f.value)) for f in db.scalars(select(ProfileFact))]
    baseline = client.post("/v1/research-opportunities/guidance", json={"limit": 24})
    assert baseline.status_code == 200 and baseline.headers["cache-control"] == "private, no-store"
    result = baseline.json()
    assert result["eligible_count"] == 0 and result["candidate_count"] > 0
    assert all(
        not v["eligibility_verified"] and not v["listing"]["archive"] and v["listing"]["documents"]
        for v in result["items"]
    )
    scenario = client.post(
        "/v1/research-opportunities/guidance",
        json={
            "scenario": True,
            "overrides": [{"key": "domicile_state", "value": "Gujarat"}],
            "limit": 24,
        },
    ).json()
    assert scenario["hypothetical"] and scenario["eligible_count"] == 0
    assert all(v["listing"]["jurisdiction"] == "India" for v in scenario["items"])
    assert scenario["candidate_count"] < result["candidate_count"]
    for invalid in [
        [{"key": "age", "value": -1}],
        [{"key": "domicile_state", "value": True}],
        [
            {"key": "domicile_state", "value": "Rajasthan"},
            {"key": "domicile_state", "value": "Gujarat"},
        ],
    ]:
        assert (
            client.post(
                "/v1/research-opportunities/guidance", json={"overrides": invalid}
            ).status_code
            == 422
        )
    after = [(str(f.id), f.key, copy.deepcopy(f.value)) for f in db.scalars(select(ProfileFact))]
    assert sorted(before) == sorted(after)
    assert all(
        v.publication_state == "draft"
        for v in db.scalars(
            select(OpportunityVersion).where(OpportunityVersion.snapshot_id.is_not(None))
        )
    )
    assert len(list(db.scalars(select(ResearchListing)))) == 96


@pytest.mark.parametrize("kind", ["person", "household", "business"])
def test_guidance_cannot_access_another_accounts_subject(real_guidance, kind):
    from opportunity_platform.core.auth import current_uid
    from opportunity_platform.db.models import Business, BusinessMembership, Household, Person, User
    from opportunity_platform.main import app

    client, db = real_guidance
    other = User(firebase_uid="fictional-research-other")
    db.add(other)
    db.flush()
    if kind == "person":
        obj = Person(user_id=other.id, display_name="Fictional private person")
    elif kind == "household":
        obj = Household(owner_user_id=other.id, name="Fictional private household")
    else:
        obj = Business(name="Fictional private business", legal_status="unregistered")
    db.add(obj)
    db.flush()
    if kind == "business":
        db.add(BusinessMembership(business_id=obj.id, user_id=other.id, role="owner"))
    identifier = str(obj.id)
    db.commit()
    app.dependency_overrides[current_uid] = lambda: "fictional-research-owner"
    response = client.post(
        "/v1/research-opportunities/guidance", json={"subject": {"kind": kind, "id": identifier}}
    )
    assert response.status_code == 404 and "Fictional private" not in response.text


def test_new_account_gets_profile_required_without_creating_a_profile(real_guidance):
    from sqlalchemy import func, select

    from opportunity_platform.core.auth import current_uid
    from opportunity_platform.db.models import Person, User
    from opportunity_platform.main import app

    client, db = real_guidance
    db.add(User(firebase_uid="fictional-research-new"))
    db.commit()
    before = db.scalar(select(func.count()).select_from(Person))
    app.dependency_overrides[current_uid] = lambda: "fictional-research-new"
    response = client.post("/v1/research-opportunities/guidance", json={})
    assert response.status_code == 404 and response.json()["error"]["code"] == "profile_not_found"
    assert db.scalar(select(func.count()).select_from(Person)) == before
