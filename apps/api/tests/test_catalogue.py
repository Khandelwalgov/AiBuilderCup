import uuid
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from opportunity_platform.core import auth as auth_module
from opportunity_platform.core.config import settings
from opportunity_platform.db.models import Opportunity, OpportunityVersion, ProfileFact, Source
from opportunity_platform.seed import seed


def test_health_and_truthful_catalogue(client):
    assert client.get("/health").json() == {"status": "ok", "database": "connected"}
    page = client.get("/v1/opportunities?development=true").json()
    assert page["total"] == 6
    assert all(
        item["is_synthetic"]
        and item["source_url"] is None
        and item["last_verified_at"] is None
        and item["closes_on"] is None
        for item in page["items"]
    )
    facets = client.get("/v1/opportunity-facets?development=true").json()
    assert (facets["synthetic"], facets["verified"], facets["official_sources"]) == (6, 0, 0)


def test_filter_search_and_pagination(client):
    assert client.get("/v1/opportunities?development=true&q=students").json()["total"] == 1
    assert (
        client.get("/v1/opportunities?development=true&category=business&state=Rajasthan").json()[
            "total"
        ]
        == 1
    )
    assert client.get("/v1/opportunities?development=true&district=Dausa").json()["total"] == 1
    assert client.get("/v1/opportunities?development=true&state=Kerala").json()["items"] == []
    assert client.get("/v1/opportunities?development=true&q=%25").json()["total"] == 0
    ids = []
    cursor = None
    while True:
        params = {"limit": 2, "development": True}
        if cursor:
            params["cursor"] = cursor
        page = client.get("/v1/opportunities?development=true", params=params).json()
        ids += [item["id"] for item in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert len(ids) == len(set(ids)) == 6


@pytest.mark.parametrize(
    "query", ["limit=0", "limit=101", "cursor=bad", "status=approved", "deadline_before=bad"]
)
def test_validation(client, query):
    response = client.get("/v1/opportunities?development=true&" + query)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert response.headers["X-Request-ID"]


def test_detail_and_missing_record(client):
    item = client.get("/v1/opportunities?development=true").json()["items"][0]
    assert client.get("/v1/opportunities/" + item["id"] + "?development=true").json() == item
    assert client.get("/v1/opportunities/" + str(uuid.uuid4())).status_code == 404


def test_seed_is_idempotent(db):
    seed(db, Path(__file__).resolve().parents[3] / "data/fixtures/opportunities.json")
    assert db.scalar(select(func.count()).select_from(Opportunity)) == 6


def test_latest_version_and_source_failure_preserve_record(client, db):
    opportunity = db.scalar(select(Opportunity))
    old = db.scalar(
        select(OpportunityVersion).where(OpportunityVersion.opportunity_id == opportunity.id)
    )
    db.add(
        OpportunityVersion(
            opportunity_id=opportunity.id,
            version=2,
            title="Updated synthetic example",
            summary="New candidate, not verified",
            status="needs_review",
            country="IN",
        )
    )
    source = db.get(Source, opportunity.source_id)
    source.status = "source_unreachable"
    db.commit()
    item = client.get("/v1/opportunities/" + str(opportunity.id) + "?development=true").json()
    assert item["version"] == 2 and item["source"]["status"] == "source_unreachable"
    assert db.get(OpportunityVersion, old.id) is not None
    assert client.get("/v1/opportunities?development=true").json()["total"] == 6


def test_verified_requires_review_provenance(db):
    opportunity = db.scalar(select(Opportunity))
    db.add(
        OpportunityVersion(
            opportunity_id=opportunity.id,
            version=2,
            title="Bad",
            summary="Bad",
            status="verified",
            country="IN",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_fact_requires_exactly_one_subject(db):
    db.add(ProfileFact(key="income", value=None, origin="unknown"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_private_endpoint_denies_missing_credentials(client):
    assert client.get("/v1/me").status_code == 401
    assert client.get("/v1/me?uid=somebody_else").status_code == 401


def test_auth_not_configured_fails_closed(client, monkeypatch):
    monkeypatch.setattr(settings(), "firebase_project_id", "")
    response = client.get("/v1/me", headers={"Authorization": "Bearer arbitrary"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "auth_not_configured"


def test_protected_identity_from_verified_token_only(client, monkeypatch):
    monkeypatch.setattr(settings(), "firebase_project_id", "test-project")
    from types import SimpleNamespace

    monkeypatch.setattr(
        auth_module.firebase_admin, "get_app", lambda: SimpleNamespace(project_id="test-project")
    )
    calls = []

    def verify(token, app, check_revoked):
        calls.append(check_revoked)
        return {"uid": "verified-user", "is_admin": False}

    monkeypatch.setattr(auth_module.auth, "verify_id_token", verify)
    response = client.get(
        "/v1/me?uid=other-user", headers={"Authorization": "Bearer signed-test-token"}
    )
    assert response.json() == {"uid": "verified-user", "is_admin": False}
    assert calls == [True]

    def invalid(*args, **kwargs):
        raise auth_module.auth.InvalidIdTokenError("invalid")

    monkeypatch.setattr(auth_module.auth, "verify_id_token", invalid)
    assert client.get("/v1/me", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_initialized_firebase_project_mismatch_fails_closed(client, monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(settings(), "firebase_project_id", "selected-project")
    monkeypatch.setattr(
        auth_module.firebase_admin, "get_app", lambda: SimpleNamespace(project_id="other-project")
    )
    response = client.get("/v1/me", headers={"Authorization": "Bearer synthetic-token"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "auth_project_mismatch"
