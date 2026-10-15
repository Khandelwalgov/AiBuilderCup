"""Real HTTP/PostgreSQL/local-blob lifecycle. Fictional files only; no provider calls."""

import io
import uuid
from datetime import date, timedelta

import pytest
from PIL import Image
from pypdf import PdfWriter
from sqlalchemy import select
from test_pipeline import pipeline  # noqa: F401
from test_workspaces import publish_two, setup_person

from opportunity_platform.core.auth import current_uid
from opportunity_platform.core.config import settings
from opportunity_platform.db.models import (
    BusinessMembership,
    Document,
    Opportunity,
    Requirement,
    Source,
)
from opportunity_platform.main import app
from opportunity_platform.profiles.service import ProfileWrite, save_profile
from opportunity_platform.subjects import service as subjects


@pytest.fixture
def vault(client, db, tmp_path, monkeypatch, pipeline):  # noqa: F811
    monkeypatch.setattr(settings(), "document_uploads_enabled", True)
    monkeypatch.setattr(settings(), "document_local_root", str(tmp_path / "private"))
    monkeypatch.setattr(settings(), "enable_development_catalogue", True)
    first, second = publish_two(db, pipeline)
    setup_person(db)
    uid = "fictional-owner"
    app.dependency_overrides[current_uid] = lambda: uid
    reqs = []
    for op, definition in [(first, "parental"), (second, "parental"), (second, "personal")]:
        # Test-only published synthetic policy. Never enters the application schema.
        op.is_synthetic = True
        db.get(Source, op.source_id).is_synthetic = True
        req = Requirement(
            version_id=op.published_version_id,
            description="FICTIONAL income certificate needed",
            subject_context="person",
            kind="document",
            application_context="all",
            rule={
                "op": "condition",
                "condition": {
                    "op": "document",
                    "fact": "has_income_certificate",
                    "income_definition": definition,
                    "income_period": "fictional-2026",
                },
                "children": [],
            },
        )
        db.add(req)
        db.flush()
        reqs.append(req.id)
    db.commit()
    yield client, db, tmp_path, reqs
    app.dependency_overrides.pop(current_uid, None)


def pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.add_metadata({"/Title": "FICTIONAL test document — not an official certificate"})
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


def create(client, reqs=None, subject=None, **extra):
    response = client.post(
        "/v1/documents",
        json={
            "subject": subject or {"kind": "person"},
            "display_name": "Fictional parental income certificate",
            "document_type": "income_certificate",
            "approved_uses": ["readiness"],
            "requirement_ids": [str(r) for r in reqs or []],
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def upload(client, doc, content=None, media="application/pdf"):
    return client.put(
        f"/v1/documents/{doc['id']}/content",
        content=content or pdf(),
        headers={"Content-Type": media},
    )


def token(client, doc, purpose="download"):
    result = client.post(f"/v1/documents/{doc['id']}/access", json={"purpose": purpose})
    assert result.status_code == 200, result.text
    return result.json()["token"]


def retrieve(client, doc, access, purpose="download"):
    return client.get(
        f"/v1/documents/{doc['id']}/content",
        params={"purpose": purpose},
        headers={"X-Document-Access": access},
    )


def test_real_file_lifecycle_compatible_reuse_unknown_eligibility(vault):
    client, db, tmp, reqs = vault
    before = client.get("/v1/documents/requirements").json()
    assert (
        next(r for r in before if r["requirement_id"] == str(reqs[0]))["documentary_status"]
        == "not_provided"
    )
    intent = create(client, reqs[:2])
    saved = upload(client, intent).json()
    assert saved["status"] == "uploaded_unverified" and saved["verification"] == "not_verified"
    assert len(saved["linked_requirements"]) == 2
    assert len(list((tmp / "private").iterdir())) == 1
    assert "blob_key" not in saved and str(tmp) not in str(saved)
    assert upload(client, intent).json()["sha256"] == saved["sha256"]
    access = token(client, saved)
    downloaded = retrieve(client, saved, access)
    assert downloaded.status_code == 200 and downloaded.content == pdf()
    assert downloaded.headers["cache-control"] == "private, no-store"
    assert downloaded.headers["x-content-type-options"] == "nosniff"
    assert retrieve(client, saved, access, "preview").status_code == 404
    preview = retrieve(client, saved, token(client, saved, "preview"), "preview")
    assert preview.status_code == 200 and "inline" in preview.headers["content-disposition"]
    requirement = next(
        r
        for r in client.get("/v1/documents/requirements").json()
        if r["requirement_id"] == str(reqs[0])
    )
    assert requirement["documentary_status"] == "uploaded_unverified"
    plan = client.post("/v1/plan", json={"subject": {"kind": "person"}, "development": True}).json()
    action = next(
        a
        for a in plan["actions"]
        if any(o["requirement_id"] == str(reqs[0]) for o in a["opportunities"])
    )
    assert action["documentary_status"] == "uploaded_unverified"
    assert all(
        r["result"]["outcome"] == "unknown"
        for e in plan["evaluations"]
        for r in e["requirements"]
        if r["requirement_id"] in [str(x) for x in reqs]
    )
    mismatch = client.post(
        f"/v1/documents/{saved['id']}/links",
        json={"requirement_ids": [str(reqs[2])], "expected_revision": saved["revision"]},
    )
    assert (
        mismatch.status_code == 422
        and mismatch.json()["error"]["code"] == "incompatible_document_requirements"
    )
    replacement = create(client, replaces_id=saved["id"])
    new = upload(client, replacement).json()
    assert len(new["linked_requirements"]) == 2
    assert client.get(f"/v1/documents/{saved['id']}").json()["status"] == "replaced"
    assert retrieve(client, saved, access).status_code == 404
    assert len(list((tmp / "private").iterdir())) == 1
    deleted = client.request(
        "DELETE", f"/v1/documents/{new['id']}", json={"expected_revision": new["revision"]}
    )
    assert deleted.status_code == 200 and deleted.json()["status"] == "deleted"
    assert not list((tmp / "private").iterdir())
    assert all(
        r["documentary_status"] == "not_provided"
        for r in client.get("/v1/documents/requirements").json()
    )


def test_cross_user_dependent_adult_business_and_revocation(vault):
    client, db, _, _ = vault
    home = subjects.create_household(
        db, "fictional-owner", subjects.HouseholdWrite(name="Fictional home")
    )
    child = subjects.add_dependent(
        db,
        "fictional-owner",
        home.id,
        subjects.DependentWrite(
            display_name="Fictional child",
            facts=[],
            guardian_responsibility_confirmed=True,
            relationship="parent",
        ),
    )
    intent = create(client, subject={"kind": "person", "id": str(child.id)})
    saved = upload(client, intent).json()
    access = token(client, saved)
    save_profile(
        db, "fictional-stranger", ProfileWrite(display_name="Fictional other adult", facts=[])
    )
    adult = subjects.resolve(db, "fictional-stranger", subjects.SubjectRef())[1]
    app.dependency_overrides[current_uid] = lambda: "fictional-stranger"
    assert client.get(f"/v1/documents/{saved['id']}").status_code == 404
    assert retrieve(client, saved, access).status_code == 404
    assert (
        client.post(
            "/v1/documents",
            json={
                "subject": {"kind": "person", "id": str(child.id)},
                "display_name": "Fictional",
                "document_type": "other",
                "approved_uses": ["readiness"],
            },
        ).status_code
        == 404
    )
    app.dependency_overrides[current_uid] = lambda: "fictional-owner"
    assert (
        client.get(
            "/v1/documents", params={"kind": "person", "subject_id": str(adult.id)}
        ).status_code
        == 404
    )
    business = subjects.save_business(
        db,
        "fictional-owner",
        subjects.BusinessWrite(name="Fictional business", legal_status="unregistered", facts=[]),
    )
    business_doc = upload(
        client, create(client, subject={"kind": "business", "id": str(business.id)})
    ).json()
    stranger = subjects.account(db, "fictional-stranger")
    db.add(BusinessMembership(business_id=business.id, user_id=stranger.id, role="viewer"))
    db.commit()
    app.dependency_overrides[current_uid] = lambda: "fictional-stranger"
    assert client.get(f"/v1/documents/{business_doc['id']}").status_code == 200
    assert (
        client.request(
            "DELETE",
            f"/v1/documents/{business_doc['id']}",
            json={"expected_revision": business_doc["revision"]},
        ).status_code
        == 404
    )
    db.delete(
        db.scalar(select(BusinessMembership).where(BusinessMembership.user_id == stranger.id))
    )
    db.commit()
    assert client.get(f"/v1/documents/{business_doc['id']}").status_code == 404
    app.dependency_overrides[current_uid] = lambda: "fictional-owner"
    subjects.revoke_guardian_access(db, "fictional-owner", child.id)
    assert retrieve(client, saved, access).status_code == 404
    assert client.get(f"/v1/documents/{saved['id']}").status_code == 404


def test_signature_size_quota_expiry_integrity_and_failed_upload(vault, monkeypatch):
    client, db, tmp, reqs = vault
    intent = create(client, reqs[:1])
    bad = upload(client, intent, b"not a PDF")
    assert bad.status_code == 422 and not (tmp / "private").exists()
    monkeypatch.setattr(settings(), "document_max_file_bytes", 1024)
    assert upload(client, intent, b"%PDF-" + b"x" * 1024).status_code == 413
    monkeypatch.setattr(settings(), "document_max_file_bytes", 5_242_880)
    image = Image.new("RGB", (20, 20), "white")
    stream = io.BytesIO()
    image.save(stream, format="JPEG")
    assert upload(client, intent, stream.getvalue(), "image/png").status_code == 422
    saved = upload(client, intent, stream.getvalue(), "image/jpeg").json()
    assert saved["media_type"] == "image/jpeg"
    monkeypatch.setattr(settings(), "document_max_count", 1)
    assert (
        client.post(
            "/v1/documents",
            json={
                "subject": {"kind": "person"},
                "display_name": "Fictional",
                "document_type": "other",
                "approved_uses": ["readiness"],
            },
        ).status_code
        == 429
    )
    doc = db.get(Document, uuid.UUID(saved["id"]))
    doc.expires_on = date.today() - timedelta(days=1)
    db.commit()
    assert client.get(f"/v1/documents/{saved['id']}").json()["status"] == "expired"
    assert (
        client.post(
            f"/v1/documents/{saved['id']}/links",
            json={"requirement_ids": [str(reqs[1])], "expected_revision": saved["revision"]},
        ).status_code
        == 422
    )
    (tmp / "private" / doc.blob_key).write_bytes(b"tampered fictional file")
    assert retrieve(client, saved, token(client, saved)).status_code == 503


def test_no_auth_and_production_upload_gate(client, db, monkeypatch):
    assert client.get("/v1/documents").status_code == 401
    assert client.post("/v1/documents", json={}).status_code == 401
    setup_person(db)
    app.dependency_overrides[current_uid] = lambda: "fictional-owner"
    monkeypatch.setattr(settings(), "environment", "production")
    monkeypatch.setattr(settings(), "document_uploads_enabled", True)
    assert client.get("/v1/documents/capabilities").json()["uploads_enabled"] is False
    assert (
        client.post(
            "/v1/documents",
            json={
                "subject": {"kind": "person"},
                "display_name": "Fictional",
                "document_type": "other",
                "approved_uses": ["readiness"],
            },
        ).status_code
        == 503
    )


def test_scoped_access_expiry_mutation_and_no_user_verification(vault, monkeypatch):
    from opportunity_platform.documents import service as documents

    client, _, _, reqs = vault
    forged = client.post(
        "/v1/documents",
        json={
            "subject": {"kind": "person"},
            "display_name": "Fictional",
            "document_type": "other",
            "approved_uses": ["readiness"],
            "verification": "verified",
        },
    )
    assert forged.status_code == 422
    doc = upload(client, create(client, reqs[:1])).json()
    grant = token(client, doc)
    assert retrieve(client, doc, grant + "tampered").status_code == 404
    now = documents.time.time()
    monkeypatch.setattr(documents.time, "time", lambda: now + 61)
    assert retrieve(client, doc, grant).status_code == 404


def test_quota_replacement_and_physical_delete_retry(vault, monkeypatch):
    from opportunity_platform.documents.storage import LocalStorage

    client, _, tmp, reqs = vault
    monkeypatch.setattr(settings(), "document_max_count", 1)
    monkeypatch.setattr(settings(), "document_max_total_bytes", len(pdf()))
    first = upload(client, create(client, reqs[:1])).json()
    replacement = create(client, replaces_id=first["id"])
    new = upload(client, replacement).json()
    assert new["status"] == "uploaded_unverified" and len(list((tmp / "private").iterdir())) == 1
    grant = token(client, new)
    actual = LocalStorage.delete

    def fail_delete(self, key):
        raise OSError("fictional temporary storage failure")

    monkeypatch.setattr(LocalStorage, "delete", fail_delete)
    removed = client.request(
        "DELETE", f"/v1/documents/{new['id']}", json={"expected_revision": new["revision"]}
    )
    assert removed.status_code == 503
    assert retrieve(client, new, grant).status_code == 404
    pending = client.get(f"/v1/documents/{new['id']}").json()
    assert pending["status"] == "deleted" and pending["purge_pending"] is True
    monkeypatch.setattr(LocalStorage, "delete", actual)
    assert (
        client.request(
            "DELETE", f"/v1/documents/{new['id']}", json={"expected_revision": new["revision"]}
        ).json()["purge_pending"]
        is False
    )
    assert not list((tmp / "private").iterdir())


def test_write_failure_retries_without_partial_blob_and_active_pdf_rejected(vault, monkeypatch):
    from opportunity_platform.documents.storage import LocalStorage

    client, _, tmp, _ = vault
    intent = create(client)
    writer = PdfWriter()
    writer.add_blank_page(width=50, height=50)
    writer.add_js('app.alert("Fictional test")')
    data = io.BytesIO()
    writer.write(data)
    assert upload(client, intent, data.getvalue()).status_code == 422
    original = LocalStorage.put

    def fail_put(self, *args):
        raise OSError("fictional interrupted write")

    monkeypatch.setattr(LocalStorage, "put", fail_put)
    assert upload(client, intent).status_code == 503
    assert not list((tmp / "private").iterdir())
    assert client.get(f"/v1/documents/{intent['id']}").json()["status"] == "pending_upload"
    monkeypatch.setattr(LocalStorage, "put", original)
    assert upload(client, intent).status_code == 200
    import stat

    assert stat.S_IMODE((tmp / "private").stat().st_mode) == 0o700
    assert stat.S_IMODE(next((tmp / "private").iterdir()).stat().st_mode) == 0o600


def test_publication_change_does_not_silently_reuse_old_period(vault):
    from datetime import datetime, timezone

    from opportunity_platform.db.models import OpportunityVersion

    client, db, _, reqs = vault
    doc = upload(client, create(client, reqs[:1])).json()
    original = db.get(Requirement, reqs[0])
    old = db.get(OpportunityVersion, original.version_id)
    op = db.get(Opportunity, old.opportunity_id)
    new = OpportunityVersion(
        opportunity_id=op.id,
        version=old.version + 1,
        publication_state="published",
        status="verified",
        title="FICTIONAL changed period",
        summary="Fictional amended policy, isolated test only.",
        source_url=old.source_url,
        reviewer_id=old.reviewer_id,
        last_verified_at=datetime.now(timezone.utc),
        country="IN",
    )
    db.add(new)
    db.flush()
    op.published_version_id = new.id
    rule = {
        **original.rule,
        "condition": {**original.rule["condition"], "income_period": "fictional-2027"},
    }
    req = Requirement(
        version_id=new.id,
        description="FICTIONAL new-period certificate",
        subject_context="person",
        kind="document",
        application_context="all",
        rule=rule,
    )
    db.add(req)
    db.commit()
    metadata = client.get(f"/v1/documents/{doc['id']}").json()
    assert metadata["linked_requirements"][0]["current"] is False
    current = next(
        n
        for n in client.get("/v1/documents/requirements").json()
        if n["requirement_id"] == str(req.id)
    )
    assert current["documentary_status"] == "not_provided"
    assert (
        client.post(
            f"/v1/documents/{doc['id']}/links",
            json={"requirement_ids": [str(req.id)], "expected_revision": metadata["revision"]},
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/v1/documents/{doc['id']}/links",
            json={"requirement_ids": [str(reqs[0])], "expected_revision": metadata["revision"]},
        ).status_code
        == 404
    )


def test_cross_origin_scoped_header_and_private_metadata_cache(client):
    response = client.options(
        "/v1/documents",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization, X-Document-Access",
        },
    )
    assert response.status_code == 200
    assert "x-document-access" in response.headers["access-control-allow-headers"].lower()
    assert client.get("/v1/documents").headers["cache-control"] == "private, no-store"
