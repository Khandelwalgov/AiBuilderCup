"""Authorized private storage/readiness links, never document authenticity or legal approval."""

import base64
import hashlib
import hmac
import io
import json
import secrets
import time
import uuid
import warnings
from datetime import date, datetime, timezone
from functools import lru_cache

from PIL import Image
from pypdf import PdfReader
from sqlalchemy import func, select

from opportunity_platform.core.config import settings
from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import (
    AuditEvent,
    Document,
    DocumentRequirementLink,
    Opportunity,
    OpportunityVersion,
    Requirement,
    RequirementEvidence,
    User,
)
from opportunity_platform.documents.schemas import (
    DocumentCreate,
    DocumentView,
    RequirementDocumentView,
)
from opportunity_platform.documents.storage import storage
from opportunity_platform.eligibility.rules import Rule
from opportunity_platform.subjects.service import SubjectRef, resolve

ACTIVE = {"pending_upload", "uploaded_unverified"}
MISSING = "This document is not available with your permissions."


def subject_ref(doc):
    kind = next(
        k for k in ["person", "household", "business"] if getattr(doc, k + "_id") is not None
    )
    return SubjectRef(kind=kind, id=getattr(doc, kind + "_id"))


def authorize(session, uid, identifier, write=False, lock=False):
    query = select(Document).where(Document.id == identifier)
    if lock:
        query = query.with_for_update()
    doc = session.scalar(query.execution_options(populate_existing=True))
    if doc is None:
        raise APIError(404, "document_not_found", MISSING)
    try:
        user, _, _ = resolve(session, uid, subject_ref(doc), write)
    except APIError:
        raise APIError(404, "document_not_found", MISSING) from None
    return user, doc


def status(doc):
    if doc.status == "uploaded_unverified" and doc.expires_on and doc.expires_on < date.today():
        return "expired"
    return doc.status


def linked(session, doc):
    return [
        {
            "requirement_id": str(link.requirement_id),
            "version_id": str(link.version_id),
            "opportunity_id": str(version.opportunity_id),
            "opportunity_title": version.title,
            "requirement": req.description,
            "current": op.published_version_id == version.id,
        }
        for link, req, version, op in session.execute(
            select(DocumentRequirementLink, Requirement, OpportunityVersion, Opportunity)
            .join(Requirement, Requirement.id == DocumentRequirementLink.requirement_id)
            .join(OpportunityVersion, OpportunityVersion.id == DocumentRequirementLink.version_id)
            .join(Opportunity, Opportunity.id == OpportunityVersion.opportunity_id)
            .where(DocumentRequirementLink.document_id == doc.id)
        )
    ]


def revision(doc, links):
    return hashlib.sha256(
        json.dumps(
            [
                str(doc.id),
                doc.status,
                doc.sha256,
                sorted(str(item["requirement_id"]) for item in links),
            ]
        ).encode()
    ).hexdigest()


def view(session, doc):
    links = linked(session, doc)
    return DocumentView(
        id=doc.id,
        subject=subject_ref(doc),
        display_name=doc.display_name,
        document_type=doc.document_type,
        media_type=doc.media_type,
        byte_size=doc.byte_size,
        sha256=doc.sha256,
        issuer=doc.issuer,
        issued_on=doc.issued_on,
        expires_on=doc.expires_on,
        status=status(doc),
        created_at=doc.created_at,
        uploaded_at=doc.uploaded_at,
        approved_uses=doc.approved_uses,
        linked_requirements=links,
        replaces_id=doc.replaces_id,
        revision=revision(doc, links),
        purge_pending=doc.purge_pending,
    )


def check_revision(session, doc, expected):
    if expected != revision(doc, linked(session, doc)):
        raise APIError(
            409, "document_conflict", "This document changed. Reload before trying again."
        )


def audit(session, user, action, doc):
    session.add(AuditEvent(actor_id=user.id, action=action, object_id=doc.id, details={}))


def listing(session, uid, subject):
    user, obj, _ = resolve(session, uid, subject)
    docs = list(
        session.scalars(
            select(Document)
            .where(getattr(Document, subject.kind + "_id") == obj.id)
            .order_by(Document.created_at.desc())
        )
    )
    session.add(
        AuditEvent(actor_id=user.id, action="document_list_viewed", object_id=obj.id, details={})
    )
    session.commit()
    return [view(session, doc) for doc in docs]


def leaves(rule):
    return (
        [rule.condition]
        if rule.op == "condition"
        else [c for child in rule.children for c in leaves(child)]
    )


def compatibility(req):
    if req.document_dependency:
        payload = dict(req.document_dependency)
        payload["document_type"] = {
            "parental-income-certificate": "parental_income_certificate",
            "disability-certificate": "disability_certificate",
            "udid": "udid",
            "age-proof": "age_proof",
            "academic-qualification": "education_certificate",
        }.get(payload.get("document"), "other")
        return payload
    conditions = [c for c in leaves(Rule.model_validate(req.rule)) if c.op == "document"]
    if not conditions:
        return None
    # One form must not guess which of several distinct document conditions it supports.
    if len(conditions) != 1:
        return {"document_type": "other", "uninterpreted_requirement": str(req.id)}
    c = conditions[0]
    name = {
        "has_income_certificate": "income_certificate",
        "has_disability_certificate": "disability_certificate",
        "has_udid_certificate": "udid",
        "has_registration_certificate": "registration_certificate",
    }[c.fact]
    return {
        "document_type": name,
        "income_definition": c.income_definition,
        "income_period": c.income_period,
        "as_of": str(c.as_of),
        "policy_scope": str(req.id)
        if name == "income_certificate" and not (c.income_period and c.income_definition)
        else None,
    }


def requirement(session, identifier, kind):
    row = session.execute(
        select(Requirement, OpportunityVersion, Opportunity)
        .join(OpportunityVersion, OpportunityVersion.id == Requirement.version_id)
        .join(Opportunity, Opportunity.id == OpportunityVersion.opportunity_id)
        .where(
            Requirement.id == identifier,
            Opportunity.published_version_id == OpportunityVersion.id,
            OpportunityVersion.publication_state == "published",
            OpportunityVersion.status == "verified",
        )
    ).first()
    if (
        row is None
        or row[0].subject_context != kind
        or (row[2].is_synthetic and not settings().enable_development_catalogue)
    ):
        raise APIError(
            404, "requirement_not_found", "This published document requirement is not available."
        )
    if compatibility(row[0]) is None:
        raise APIError(
            422,
            "not_document_requirement",
            "This condition needs information rather than a document.",
        )
    return row


def attach(session, doc, ids):
    rows = [requirement(session, r, subject_ref(doc).kind)[0] for r in ids]
    existing = list(
        session.scalars(
            select(DocumentRequirementLink).where(DocumentRequirementLink.document_id == doc.id)
        )
    )
    basis = [e.compatibility for e in existing] + [compatibility(r) for r in rows]
    if any(p.get("document_type") != doc.document_type for p in basis):
        raise APIError(
            422, "document_type_mismatch", "Choose the document type required by this condition."
        )
    if basis and any(p != basis[0] for p in basis):
        raise APIError(
            422,
            "incompatible_document_requirements",
            "These requirements have different evidence scopes. Keep their documents separate.",
        )
    for req in rows:
        if not any(e.requirement_id == req.id for e in existing):
            session.add(
                DocumentRequirementLink(
                    document_id=doc.id,
                    requirement_id=req.id,
                    version_id=req.version_id,
                    compatibility=compatibility(req),
                )
            )
    session.flush()


def require_uploads():
    if not settings().document_uploads_enabled or settings().environment == "production":
        raise APIError(
            503,
            "uploads_disabled",
            "Uploads are disabled until private storage and security prerequisites are ready.",
        )


def create(session, uid, data: DocumentCreate):
    require_uploads()
    user, obj, _ = resolve(session, uid, data.subject, True)
    session.execute(select(User).where(User.id == user.id).with_for_update())
    count, total = session.execute(
        select(func.count(), func.coalesce(func.sum(Document.byte_size), 0)).where(
            Document.owner_user_id == user.id, Document.status.in_(ACTIVE)
        )
    ).one()
    if count >= settings().document_max_count or total >= settings().document_max_total_bytes:
        raise APIError(
            429,
            "document_quota",
            "Storage limit reached. Remove an unused document first.",
        )
    old = None
    if data.replaces_id:
        _, old = authorize(session, uid, data.replaces_id, True, True)
        if (
            subject_ref(old) != SubjectRef(kind=data.subject.kind, id=obj.id)
            or old.status != "uploaded_unverified"
        ):
            raise APIError(
                409,
                "replacement_unavailable",
                "This document cannot be replaced in the selected context.",
            )
        if old.document_type != data.document_type:
            raise APIError(
                422, "document_type_mismatch", "A replacement must have the same document purpose."
            )
    doc = Document(
        **{data.subject.kind + "_id": obj.id},
        owner_user_id=user.id,
        blob_key=uuid.uuid4().hex,
        media_type="application/octet-stream",
        display_name=data.display_name.strip(),
        document_type=data.document_type,
        issuer=data.issuer,
        issued_on=data.issued_on,
        expires_on=data.expires_on,
        approved_uses=data.approved_uses,
        status="pending_upload",
        storage_backend=settings().document_storage_backend,
        replaces_id=old.id if old else None,
    )
    if not doc.display_name:
        raise APIError(422, "document_name_required", "Give this document a recognizable name.")
    session.add(doc)
    session.flush()
    ids = list(data.requirement_ids)
    if old:
        ids = list(
            set(
                ids
                + [
                    e.requirement_id
                    for e in session.scalars(
                        select(DocumentRequirementLink).where(
                            DocumentRequirementLink.document_id == old.id
                        )
                    )
                    if session.get(
                        Opportunity, session.get(OpportunityVersion, e.version_id).opportunity_id
                    ).published_version_id
                    == e.version_id
                ]
            )
        )
    attach(session, doc, ids)
    audit(session, user, "document_upload_started", doc)
    session.commit()
    return view(session, doc)


def validate_file(content, media):
    if not content or len(content) > settings().document_max_file_bytes:
        raise APIError(413, "document_size", "Choose a nonempty file within the upload size limit.")
    good = False
    if media == "application/pdf" and content.startswith(b"%PDF-") and b"%%EOF" in content[-2048:]:
        try:
            reader = PdfReader(io.BytesIO(content), strict=True)
            dangerous = [
                b"/JavaScript",
                b"/JS",
                b"/Launch",
                b"/EmbeddedFile",
                b"/OpenAction",
                b"/AA",
                b"/RichMedia",
            ]
            good = (
                not reader.is_encrypted
                and len(reader.pages) <= 100
                and not any(x in content for x in dangerous)
            )
        except Exception:
            good = False
    elif media in {"image/png", "image/jpeg"}:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(content)) as image:
                    expected = "PNG" if media == "image/png" else "JPEG"
                    if image.format != expected or image.width * image.height > 20_000_000:
                        raise ValueError("Unsupported image")
                    image.verify()
                with Image.open(io.BytesIO(content)) as image:
                    image.load()
                    good = image.width > 0 and image.height > 0
        except Exception:
            good = False
    if not good:
        raise APIError(
            422,
            "unsupported_document",
            "Choose a valid PDF, JPEG or PNG without active content or password protection.",
        )


def purge(session, doc):
    try:
        storage(doc.storage_backend).delete(doc.blob_key)
    except Exception:
        raise APIError(
            503,
            "document_purge_pending",
            "Access has been removed. Private file removal is pending; retry removal safely.",
        ) from None
    doc.purge_pending = False
    session.commit()


def upload(session, uid, identifier, content, media):
    require_uploads()
    user, doc = authorize(session, uid, identifier, True, True)
    if doc.status == "uploaded_unverified":
        if doc.sha256 == hashlib.sha256(content).hexdigest():
            return view(session, doc)
        raise APIError(409, "document_conflict", "Use Replace to update an uploaded file.")
    if doc.owner_user_id != user.id:
        raise APIError(404, "document_not_found", MISSING)
    if doc.status != "pending_upload":
        raise APIError(409, "document_not_uploadable", "Start a new upload for this document.")
    validate_file(content, media)
    session.execute(select(User).where(User.id == user.id).with_for_update())
    total = session.scalar(
        select(func.coalesce(func.sum(Document.byte_size), 0)).where(
            Document.owner_user_id == user.id, Document.status.in_(ACTIVE)
        )
    )
    if total + len(content) > settings().document_max_total_bytes:
        raise APIError(
            429, "document_quota", "Your private document storage limit has been reached."
        )
    old = None
    if doc.replaces_id:
        _, old = authorize(session, uid, doc.replaces_id, True, True)
        if old.status != "uploaded_unverified":
            raise APIError(
                409, "document_conflict", "This document was already replaced or removed."
            )
    backend = storage(doc.storage_backend)
    wrote = False
    try:
        backend.put(doc.blob_key, content, media)
        wrote = True
        doc.byte_size = len(content)
        doc.sha256 = hashlib.sha256(content).hexdigest()
        doc.media_type = media
        doc.uploaded_at = datetime.now(timezone.utc)
        doc.status = "uploaded_unverified"
        if old:
            old.status = "replaced"
            old.purge_pending = True
        audit(session, user, "document_uploaded", doc)
        session.commit()
    except Exception as error:
        session.rollback()
        if wrote:
            try:
                backend.delete(doc.blob_key)
            except Exception:
                pass
        if isinstance(error, APIError):
            raise
        raise APIError(
            503, "upload_failed", "The file was not saved. Your upload can be retried."
        ) from None
    if old:
        purge(session, old)
    return view(session, doc)


def remove(session, uid, identifier, expected):
    user, doc = authorize(session, uid, identifier, True, True)
    if doc.status == "deleted":
        if doc.purge_pending:
            purge(session, doc)
        return view(session, doc)
    check_revision(session, doc, expected)
    doc.status = "deleted"
    doc.purge_pending = True
    doc.display_name = "Removed document"
    doc.issuer = None
    doc.issued_on = doc.expires_on = None
    doc.approved_uses = []
    audit(session, user, "document_removed", doc)
    session.commit()
    purge(session, doc)
    return view(session, doc)


def link(session, uid, identifier, data):
    user, doc = authorize(session, uid, identifier, True, True)
    check_revision(session, doc, data.expected_revision)
    if doc.status != "uploaded_unverified":
        raise APIError(409, "document_not_linkable", "Upload the document before linking it.")
    if status(doc) == "expired":
        raise APIError(422, "document_expired", "Replace the expired document before reusing it.")
    attach(session, doc, data.requirement_ids)
    audit(session, user, "document_requirements_linked", doc)
    session.commit()
    return view(session, doc)


@lru_cache
def signing_key():
    return settings().document_signing_key.encode() or secrets.token_bytes(32)


def access(session, uid, identifier, purpose):
    user, doc = authorize(session, uid, identifier)
    if doc.status != "uploaded_unverified":
        raise APIError(404, "document_not_found", MISSING)
    payload = base64.urlsafe_b64encode(
        json.dumps(
            {
                "uid": uid,
                "id": str(identifier),
                "exp": int(time.time()) + 60,
                "purpose": purpose,
                "sha": doc.sha256,
            }
        ).encode()
    ).decode()
    signature = hmac.new(signing_key(), payload.encode(), hashlib.sha256).hexdigest()
    audit(session, user, "document_access_granted", doc)
    session.commit()
    return payload + "." + signature


def retrieve(session, uid, identifier, token, purpose):
    try:
        payload, signature = token.split(".")
        if not hmac.compare_digest(
            signature, hmac.new(signing_key(), payload.encode(), hashlib.sha256).hexdigest()
        ):
            raise ValueError()
        claims = json.loads(base64.urlsafe_b64decode(payload))
        if (
            claims["uid"] != uid
            or claims["id"] != str(identifier)
            or claims["exp"] <= time.time()
            or claims["purpose"] != purpose
        ):
            raise ValueError()
    except Exception:
        raise APIError(404, "document_not_found", MISSING) from None
    user, doc = authorize(session, uid, identifier)
    if doc.status != "uploaded_unverified" or claims["sha"] != doc.sha256:
        raise APIError(404, "document_not_found", MISSING)
    try:
        content = storage(doc.storage_backend).get(doc.blob_key)
    except Exception:
        raise APIError(
            503, "storage_unavailable", "Private file retrieval is temporarily unavailable."
        ) from None
    if len(content) != doc.byte_size or hashlib.sha256(content).hexdigest() != doc.sha256:
        raise APIError(
            503,
            "document_integrity_failed",
            "The stored file could not be validated. Retry or replace it.",
        )
    audit(session, user, "document_" + purpose, doc)
    session.commit()
    return doc, content


def readiness(session, uid, subject):
    _, obj, _ = resolve(session, uid, subject)
    docs = list(
        session.scalars(select(Document).where(getattr(Document, subject.kind + "_id") == obj.id))
    )
    rows = session.execute(
        select(Requirement, OpportunityVersion, Opportunity)
        .join(OpportunityVersion, OpportunityVersion.id == Requirement.version_id)
        .join(Opportunity, Opportunity.published_version_id == OpportunityVersion.id)
        .where(
            Requirement.subject_context == subject.kind,
            OpportunityVersion.publication_state == "published",
            OpportunityVersion.status == "verified",
        )
    ).all()
    result = []
    for req, version, op in rows:
        if op.is_synthetic and not settings().enable_development_catalogue:
            continue
        basis = compatibility(req)
        if basis is None:
            continue
        linked_docs = [
            view(session, d)
            for d in docs
            if d.status in ACTIVE
            and any(item["requirement_id"] == str(req.id) for item in linked(session, d))
        ]
        current_status = (
            "uploaded_unverified"
            if any(d.status == "uploaded_unverified" for d in linked_docs)
            else "expired"
            if any(d.status == "expired" for d in linked_docs)
            else "pending_upload"
            if linked_docs
            else "not_provided"
        )
        citations = [
            {"source_url": e.source_url, "page": e.page, "passage": e.passage}
            for e in session.scalars(
                select(RequirementEvidence).where(RequirementEvidence.requirement_id == req.id)
            )
        ]
        result.append(
            RequirementDocumentView(
                requirement_id=req.id,
                version_id=version.id,
                opportunity_id=op.id,
                opportunity_title=version.title,
                requirement=req.description,
                document_type=basis["document_type"],
                compatibility=basis,
                citations=citations,
                documentary_status=current_status,
                documents=linked_docs,
            )
        )
    return result
