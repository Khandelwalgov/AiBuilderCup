"""Real public-source comparisons with fictional subjects in isolated PostgreSQL schemas."""

import copy
import json
from pathlib import Path

import pytest
from sqlalchemy import select
from test_research_guidance import real_guidance as original_guidance

from opportunity_platform.core.auth import current_uid
from opportunity_platform.db.models import ActionItem, ProfileFact, ResearchListing, SourceSnapshot
from opportunity_platform.eligibility.rules import FactInput
from opportunity_platform.main import app
from opportunity_platform.profiles.service import ProfileWrite, save_profile
from opportunity_platform.research.conditions import compare, definitions
from opportunity_platform.subjects.service import (
    BusinessWrite,
    DependentWrite,
    HouseholdWrite,
    add_dependent,
    create_household,
    revoke_guardian_access,
    save_business,
)


@pytest.fixture
def real_guidance(client, db):
    return original_guidance.__wrapped__(client, db)


ROOT = Path(__file__).resolve().parents[3]
OWNER = "fictional-research-owner"


def auth():
    app.dependency_overrides[current_uid] = lambda: OWNER


def request(client, **body):
    response = client.post("/v1/research-opportunities/guidance", json={"limit": 24, **body})
    assert response.status_code == 200, response.text
    return response.json()


def outcomes(item):
    return {
        (c["rule"].get("condition") or {}).get("fact"): c["result"]["outcome"]
        for c in item["conditions"]
    }


def test_all_condition_mappings_are_bound_to_existing_captured_documents():
    bundle = json.loads((ROOT / "data/research/catalogue-v1.json").read_text())
    rows = {r["key"]: r for r in bundle["listings"]}
    evidence = json.loads((ROOT / "data/research/condition-evidence-v2.json").read_text())
    captured = {s["snapshot_id"]: s for s in evidence["sources"]}
    from opportunity_platform.ingestion.schemas import normalize

    for c in definitions():
        sources = rows[c["listing_key"]]["sources"]
        source = next(s for s in sources if s["content_hash"] == c["source_hash"])
        assert source["snapshot_id"] == c["snapshot_id"] and source["source_url"] == c["source_url"]
        pages = captured[c["snapshot_id"]]["pages"]
        page = next(p for p in pages if p["page"] == c["page"])
        assert normalize(c["passage"]) in normalize(page["text"])
    assert len({c["parent"] for c in definitions()}) == 11


def test_personal_discovery_education_scenario_and_plan_are_source_backed(real_guidance):
    client, db = real_guidance
    auth()
    save_profile(
        db,
        OWNER,
        ProfileWrite(
            display_name="Fictional graduate",
            facts=[
                FactInput(key="age", value=22),
                FactInput(key="domicile_state", value="Rajasthan"),
                FactInput(key="residence_state", value="Karnataka"),
                FactInput(key="highest_completed_education", value="undergraduate"),
                FactInput(key="student_status", value=False),
            ],
        ),
    )
    db.commit()
    before = [(f.id, copy.deepcopy(f.value)) for f in db.scalars(select(ProfileFact))]
    data = request(client)
    st = next(i for i in data["items"] if i["parent_key"] == "post-matric-st")
    assert outcomes(st)["student_status"] == "unsatisfied"
    assert outcomes(st)["highest_completed_education"] == "satisfied"
    assert outcomes(st)["has_bank_account"] == "unknown"
    assert data["reviewed"]["catalogue_count"] == 0 and data["eligible_count"] == 0
    assert data["candidate_count"] > 8
    assert data["supported_pair_count"] == 9
    assert any(i["listing"]["jurisdiction"] == "Rajasthan" for i in data["items"])
    simulation = request(
        client, scenario=True, overrides=[{"key": "student_status", "value": True}]
    )
    simulated = next(i for i in simulation["items"] if i["parent_key"] == "post-matric-st")
    assert outcomes(simulated)["student_status"] == "satisfied"
    assert outcomes(simulated)[None] == "unknown"
    assert sum(c["changed"] for c in simulated["conditions"]) == 4
    assert simulation["actions"] and not list(db.scalars(select(ActionItem)))
    assert before == [(f.id, copy.deepcopy(f.value)) for f in db.scalars(select(ProfileFact))]
    plan = client.post("/v1/research-opportunities/plan", json={}).json()
    action = next(a for a in plan["actions"] if a["fact"] == "student_status")
    assert (
        client.patch("/v1/actions/" + action["id"], json={"status": "completed"}).status_code == 200
    )
    assert before == [(f.id, copy.deepcopy(f.value)) for f in db.scalars(select(ProfileFact))]
    again = client.post("/v1/research-opportunities/plan", json={}).json()
    assert next(a for a in again["actions"] if a["id"] == action["id"])["status"] == "completed"
    app.dependency_overrides[current_uid] = lambda: "unrelated-fictional-account"
    assert (
        client.patch("/v1/actions/" + action["id"], json={"status": "pending"}).status_code == 404
    )


def test_family_members_have_separate_conditions_and_revocation(real_guidance):
    client, db = real_guidance
    auth()
    household = create_household(db, OWNER, HouseholdWrite(name="Fictional family"))
    children = []
    for name, course in [("Fictional daughter one", "IX"), ("Fictional daughter two", "XII")]:
        child = add_dependent(
            db,
            OWNER,
            household.id,
            DependentWrite(
                display_name=name,
                guardian_responsibility_confirmed=True,
                relationship="parent",
                facts=[
                    FactInput(key="student_status", value=True),
                    FactInput(key="current_education_level", value=course),
                    FactInput(key="enrollment_mode", value="full_time"),
                ],
            ),
        )
        children.append(child)
    body = {"subject": {"kind": "household", "id": str(household.id)}, "q": "YASASVI"}
    result = request(client, **body)
    assert result["supported_pair_count"] == 12
    first = next(
        i
        for i in result["items"]
        if i["subject_name"] == "Fictional daughter one"
        and i["parent_key"] == "pm-yasasvi-pre-matric"
    )
    second = next(
        i
        for i in result["items"]
        if i["subject_name"] == "Fictional daughter two"
        and i["parent_key"] == "pm-yasasvi-pre-matric"
    )
    assert outcomes(first)["current_education_level"] == "satisfied"
    assert outcomes(second)["current_education_level"] == "unsatisfied"
    changed = request(
        client,
        **body,
        scenario=True,
        member_overrides={
            "person:" + str(children[1].id): [{"key": "current_education_level", "value": "X"}]
        },
    )
    assert (
        outcomes(
            next(
                i
                for i in changed["items"]
                if i["subject_id"] == str(children[1].id)
                and i["parent_key"] == "pm-yasasvi-pre-matric"
            )
        )["current_education_level"]
        == "satisfied"
    )
    revoke_guardian_access(db, OWNER, children[0].id)
    result = request(client, **body)
    assert not any(i["subject_id"] == str(children[0].id) for i in result["items"])
    assert (
        client.post(
            "/v1/research-opportunities/guidance",
            json={"subject": {"kind": "person", "id": str(children[0].id)}},
        ).status_code
        == 404
    )


def test_business_specific_readiness_components_and_hypothesis(real_guidance):
    client, db = real_guidance
    auth()
    # Existing public TEAM page 12 is added to the test-only snapshot scaffold.
    dossier = json.loads((ROOT / "data/policy-review/2026-10-17/team.json").read_text())
    snapshot = db.get(SourceSnapshot, dossier["baseline"]["snapshot_id"])
    snapshot.pages = [*snapshot.pages, next(p for p in dossier["pages"] if p["page"] == 12)]
    business = save_business(
        db,
        OWNER,
        BusinessWrite(
            name="Fictional enterprise",
            legal_status="company",
            facts=[
                FactInput(key="business_registered", value=True),
                FactInput(key="business_size", value="small"),
                FactInput(key="business_sector", value="services"),
                FactInput(key="business_udyam_registered", value=False),
                FactInput(key="business_registration_state", value="Rajasthan"),
            ],
        ),
    )
    db.commit()
    body = {"subject": {"kind": "business", "id": str(business.id)}}
    result = request(client, **body)
    assert result["supported_pair_count"] == 2
    team = next(i for i in result["items"] if i["parent_key"] == "msme-team")
    assert len(team["components"]) == 4
    assert outcomes(team)["business_udyam_registered"] == "unsatisfied"
    assert outcomes(team)["business_size"] == "satisfied"
    assert outcomes(team)["business_similar_assistance"] == "unknown"
    assert all(
        i["listing"]["category"] == "business" and not i["listing"]["archive"]
        for i in result["items"]
    )
    hypothetical = request(
        client,
        **body,
        scenario=True,
        overrides=[{"key": "business_udyam_registered", "value": True}],
    )
    team = next(i for i in hypothetical["items"] if i["parent_key"] == "msme-team")
    assert outcomes(team)["business_udyam_registered"] == "satisfied"
    assert sum(c["changed"] for c in team["conditions"]) == 1
    plan = client.post("/v1/research-opportunities/plan", json=body).json()
    action = next(a for a in plan["actions"] if a["fact"] == "business_udyam_registered")
    assert len(action["opportunities"]) == 5
    assert len([a for a in plan["actions"] if a["fact"] == "business_udyam_registered"]) == 1
    # Evidence drift disables comparisons rather than trusting the prepared mapping.
    snapshot.content_hash = "f" * 64
    db.flush()
    row = db.scalar(
        select(ResearchListing).where(ResearchListing.identity_key == "msme-team-catalogue")
    )
    assert all(
        c.result.outcome == "unknown" and not c.evidence_available for c in compare(db, row, [], [])
    )


def test_public_hindi_lexical_fallback_never_needs_private_facts(real_guidance, monkeypatch):
    from opportunity_platform.research import search
    from opportunity_platform.retrieval.neural import UnavailableNeuralRetriever

    monkeypatch.setattr(search, "neural_retriever", lambda: UnavailableNeuralRetriever())
    client, _ = real_guidance
    response = client.get("/v1/research-opportunities", params={"q": "scholarship", "limit": 100})
    assert response.status_code == 200 and response.json()["total"] > 0
    assert all(not i["eligibility_verified"] for i in response.json()["items"])


def test_local_multilingual_research_retrieval_with_existing_pinned_model(
    real_guidance, monkeypatch
):
    import os

    from opportunity_platform.core.config import settings
    from opportunity_platform.research.search import rank

    directory = os.environ.get("NEURAL_TEST_MODEL_DIRECTORY")
    if not directory:
        pytest.skip("Explicit existing pinned local model directory required")
    monkeypatch.setattr(settings(), "neural_model_directory", directory)
    monkeypatch.setattr(settings(), "neural_retrieval_enabled", True)
    _, db = real_guidance
    rows = list(db.scalars(select(ResearchListing)))
    by_id = {str(r.id): r for r in rows}
    measurements = {}
    for query, category in [
        ("scholarship for study", "education"),
        ("पढ़ाई के लिए आर्थिक सहायता", "education"),
        ("selling products online ONDC", "business"),
        ("व्यवसाय के लिए सहायता", "business"),
    ]:
        scores, status = rank(rows, query)
        assert status.startswith("local_cpu:")
        first = sorted(scores, key=lambda k: (-scores[k], k))[:5]
        assert any(by_id[key].category == category for key in first)
        measurements[query] = [by_id[key].identity_key for key in first]
    print(
        "Actual local-model top-five research retrieval:",
        json.dumps(measurements, ensure_ascii=False),
    )


def test_fictional_family_members_do_not_create_profiles_or_permissions(real_guidance):
    client, db = real_guidance
    auth()
    from opportunity_platform.db.models import ConsentGrant, Person

    before = (len(list(db.scalars(select(Person)))), len(list(db.scalars(select(ConsentGrant)))))
    result = request(
        client,
        scenario=True,
        people=[
            {
                "key": "future-child",
                "name": "Fictional future learner",
                "relationship": "child",
                "facts": [
                    {"key": "student_status", "value": True},
                    {"key": "current_education_level", "value": "IX"},
                ],
            }
        ],
    )
    child = next(
        i for i in result["items"] if i["fictional"] and i["parent_key"] == "pm-yasasvi-pre-matric"
    )
    assert outcomes(child)["current_education_level"] == "satisfied"
    assert result["hypothetical"] and all(a["status"] == "hypothetical" for a in result["actions"])
    assert before == (
        len(list(db.scalars(select(Person)))),
        len(list(db.scalars(select(ConsentGrant)))),
    )
    assert not list(db.scalars(select(ActionItem)))
