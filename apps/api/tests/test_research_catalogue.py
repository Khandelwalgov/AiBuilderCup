"""Research catalogue contracts; local isolated PostgreSQL only, never publication."""

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from opportunity_platform.db.models import (
    CandidateReview,
    Opportunity,
    OpportunityVersion,
    ResearchListing,
    Source,
    SourceSnapshot,
    User,
)
from opportunity_platform.research.importer import identifier, import_listings, load
from opportunity_platform.research.schemas import ResearchInput

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = ROOT / "data/research/catalogue-v1.json"


def test_real_research_bundle_has_exact_passages_and_no_eligibility_certification():
    data, listings, fingerprint = load(BUNDLE)
    assert fingerprint == hashlib.sha256(BUNDLE.read_bytes()).hexdigest()
    assert data["inventory"]["unique_documents_examined"] == 124
    assert len(listings) == data["inventory"]["research_listings_identified"]
    assert all(v.eligibility_verified is False for v in listings)
    assert not any(v.application_status == "open" for v in listings)
    assert len({v.key for v in listings}) == len(listings)
    assert len(data["exclusions"]) == 124


@pytest.mark.parametrize("change", ["quote", "url", "text_hash", "eligibility", "open"])
def test_research_fails_closed_on_invented_evidence_or_claims(change):
    _, listings, _ = load(BUNDLE)
    value = listings[0].model_dump(mode="json")
    if change == "quote":
        value["citations"][0]["passage"] = "An invented unsupported government promise."
    elif change == "url":
        value["sources"][0]["source_url"] = "https://untrusted.invalid/private"
    elif change == "text_hash":
        value["sources"][0]["pages"][0]["text"] += " forged"
    elif change == "eligibility":
        value["eligibility_verified"] = True
    else:
        value["application_status"] = "open"
    with pytest.raises(ValidationError):
        ResearchInput.model_validate(value)


@pytest.fixture
def research_baseline(db):
    data, listings, _ = load(BUNDLE)
    actor = User(firebase_uid="fictional-local-research-operator", is_admin=True)
    db.add(actor)
    db.flush()
    captured = {str(v.acquisition.sha256) for v in data["captured_sources"]}
    # Preserve actual public capture IDs, URLs and original text where available.
    # Source metadata here is a local-only scaffold; there is no Firebase bypass in production.
    sources = {}
    for listing in listings:
        for source in listing.sources:
            if source.content_hash in captured or source.snapshot_id in sources:
                continue
            sources[source.snapshot_id] = source
    for snapshot_id, source in sources.items():
        publisher = Source(
            name="Fictional local scaffold for real captured public text",
            url=source.source_url,
            is_synthetic=False,
        )
        db.add(publisher)
        db.flush()
        db.add(
            SourceSnapshot(
                id=snapshot_id,
                source_id=publisher.id,
                content_hash=source.content_hash,
                source_url=source.source_url,
                pages=[
                    {"page": p.page, "text": p.text, "source_url": source.source_url}
                    for p in source.pages
                ],
                media_type="application/pdf",
                byte_count=1,
                response_metadata={"origin": "corpus-policy-v1"},
            )
        )
    # Same source can be used on different pages across listings.
    for listing in listings:
        for source in listing.sources:
            if source.content_hash in captured:
                continue
            snapshot = db.get(SourceSnapshot, source.snapshot_id)
            pages = {p["page"]: p for p in snapshot.pages}
            for page in source.pages:
                pages[page.page] = {
                    "page": page.page,
                    "text": page.text,
                    "source_url": source.source_url,
                }
            snapshot.pages = list(pages.values())
    db.commit()
    return data, listings, actor


def test_full_research_import_visibility_idempotency_and_policy_separation(
    client, db, research_baseline
):
    data, listings, actor = research_baseline
    before = {
        model.__tablename__: db.scalar(select(func.count()).select_from(model))
        for model in [Opportunity, OpportunityVersion, CandidateReview]
    }
    first = import_listings(db, listings, actor, captured_sources=data["captured_sources"])
    db.commit()
    assert first["research_listings_inserted"] == len(listings)
    assert client.get("/v1/research-opportunities").json()["total"] == 0
    assert (
        client.get("/v1/research-opportunities/" + str(identifier(listings[0].key))).status_code
        == 404
    )
    second = import_listings(
        db, listings, actor, make_public=True, captured_sources=data["captured_sources"]
    )
    db.commit()
    assert second["existing_listings_activated"] == len(listings)
    assert (
        import_listings(
            db, listings, actor, make_public=True, captured_sources=data["captured_sources"]
        )["research_listings_inserted"]
        == 0
    )
    db.commit()
    response = client.get("/v1/research-opportunities?limit=100")
    assert response.status_code == 200 and response.json()["total"] == len(listings)
    assert all(not item["eligibility_verified"] for item in response.json()["items"])
    facets = client.get("/v1/research-opportunities/facets").json()
    assert facets["total"] == len(listings) and "education" in facets["categories"]
    assert client.get("/v1/research-opportunities?category=procurement").json()["total"] == 18
    assert client.get("/v1/research-opportunities?q=GIFT").json()["total"] >= 1
    assert client.get("/v1/research-opportunities?q=योजना").json()["total"] >= 1
    assert client.get("/v1/research-opportunities?q=%25").json()["total"] < len(listings)
    assert client.get("/v1/research-opportunities?application_status=open").json()["total"] == 0
    page = client.get("/v1/research-opportunities?limit=7").json()
    next_page = client.get(
        "/v1/research-opportunities", params={"limit": 7, "cursor": page["next_cursor"]}
    ).json()
    assert not {i["id"] for i in page["items"]} & {i["id"] for i in next_page["items"]}
    detail = client.get("/v1/research-opportunities/" + str(identifier(listings[0].key))).json()
    assert (
        detail["citations"]
        and detail["sources"]
        and detail["verification_state"] == "source_backed_research"
    )
    assert client.get("/v1/opportunities/" + detail["id"]).status_code == 404
    assert client.get("/v1/opportunities").json()["total"] == 0
    assert db.scalar(select(func.count()).select_from(ResearchListing)) == len(listings)
    for model in [Opportunity, OpportunityVersion, CandidateReview]:
        assert db.scalar(select(func.count()).select_from(model)) == before[model.__tablename__]
    assert client.post("/v1/search", json={"mode": "me"}).status_code == 401


def test_import_rejects_changed_source_and_non_admin_before_insert(db, research_baseline):
    data, listings, actor = research_baseline
    actor.is_admin = False
    db.commit()
    with pytest.raises(Exception):
        import_listings(
            db, listings, actor, make_public=True, captured_sources=data["captured_sources"]
        )
    db.rollback()
    actor.is_admin = True
    source = next(
        source
        for v in listings
        for source in v.sources
        if db.get(SourceSnapshot, source.snapshot_id)
    )
    db.get(SourceSnapshot, source.snapshot_id).content_hash = "0" * 64
    db.commit()
    with pytest.raises(ValueError, match="hash"):
        import_listings(
            db, listings, actor, make_public=True, captured_sources=data["captured_sources"]
        )
    db.rollback()
    assert db.scalar(select(func.count()).select_from(ResearchListing)) == 0
