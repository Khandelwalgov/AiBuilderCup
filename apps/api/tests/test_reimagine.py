"""Actual ASGI CORS and authorized subject regressions; all persistence isolated."""

from test_pipeline import pipeline  # noqa:F401
from test_workspaces import publish_two, setup_person

from opportunity_platform.core.auth import current_uid
from opportunity_platform.main import app
from opportunity_platform.subjects import service as subjects


def test_separate_origin_patch_preflight_accepts_allowed_origin_only(client):
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "PATCH",
        "Access-Control-Request-Headers": "authorization,content-type",
    }
    response = client.options("/v1/actions/11111111-1111-4111-8111-111111111111", headers=headers)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "PATCH" in response.headers["access-control-allow-methods"]
    response = client.options(
        "/v1/actions/11111111-1111-4111-8111-111111111111",
        headers={**headers, "Origin": "https://untrusted.invalid"},
    )
    assert response.status_code == 400 and "access-control-allow-origin" not in response.headers


def test_explicit_subject_evaluation_never_uses_owner_facts_for_dependent(client, db, pipeline):  # noqa:F811
    from opportunity_platform.eligibility.rules import FactInput

    first, _ = publish_two(db, pipeline)
    setup_person(db)
    household = subjects.create_household(
        db, "fictional-owner", subjects.HouseholdWrite(name="Fictional family")
    )
    child = subjects.add_dependent(
        db,
        "fictional-owner",
        household.id,
        subjects.DependentWrite(
            display_name="Fictional child",
            facts=[FactInput(key="age", value=12)],
            relationship="parent",
            guardian_responsibility_confirmed=True,
        ),
    )
    app.dependency_overrides[current_uid] = lambda: "fictional-owner"
    try:

        def assess(subject):
            return client.post(
                f"/v1/opportunities/{first.id}/evaluate",
                json={"subject": subject, "application_type": "fresh"},
            )

        owner = assess({"kind": "person"})
        dependent = assess({"kind": "person", "id": str(child.id)})
        assert owner.status_code == 200 and dependent.status_code == 200
        assert owner.json()["status"] != "not_eligible_on_known_facts"
        assert dependent.json()["status"] == "not_eligible_on_known_facts"
        app.dependency_overrides[current_uid] = lambda: "fictional-stranger"
        assert assess({"kind": "person", "id": str(child.id)}).status_code == 404
    finally:
        app.dependency_overrides.pop(current_uid, None)


def test_ingestion_confirmation_rejects_before_any_provider_execution(
    client,
    db,
    pipeline,  # noqa: F811
    monkeypatch,
):  # noqa: F811
    from opportunity_platform import workflows
    from opportunity_platform.core.config import settings

    calls = []

    def forbidden_execution(*args, **kwargs):
        calls.append(True)
        raise AssertionError("This test must never execute ingestion or any network operation")

    # Replace the entire ingestion boundary, not merely the transport.
    monkeypatch.setattr(workflows.ingestion, "ingest", forbidden_execution)
    actor, _ = pipeline
    app.dependency_overrides[current_uid] = lambda: actor.firebase_uid
    config = settings()
    try:
        monkeypatch.setattr(config, "ai_ingestion_live_enabled", False)
        permission = client.get("/v1/admin/ingestion-settings").json()
        assert permission["live_enabled"] is False
        body = {
            "expected_provider": config.ai_extraction_provider,
            "expected_model": config.gemini_model,
            "confirm_potential_paid_use": True,
        }
        response = client.post("/v1/admin/sources/depwd-pre-matric/ingest", json=body)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "ingestion_not_authorized"
        monkeypatch.setattr(config, "ai_ingestion_live_enabled", True)
        response = client.post(
            "/v1/admin/sources/depwd-pre-matric/ingest",
            json={**body, "expected_model": "stale-test-model"},
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "provider_configuration_changed"
        assert calls == []
    finally:
        app.dependency_overrides.pop(current_uid, None)
