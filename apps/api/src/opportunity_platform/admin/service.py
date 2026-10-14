import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import (
    AuditEvent,
    CandidateReview,
    Opportunity,
    OpportunityVersion,
    Requirement,
    RequirementEvidence,
    SourceSnapshot,
    User,
)
from opportunity_platform.ingestion.schemas import CandidateData, validate_evidence


class SnapshotPage(BaseModel):
    page: int
    text: str
    source_url: str


class ReviewSummary(BaseModel):
    id: uuid.UUID
    title: str
    version: int
    publication_state: str
    source_url: str | None
    created_at: datetime


class ReviewView(ReviewSummary):
    candidate: CandidateData
    extraction_provider: str | None
    extraction_model: str | None
    extractor_version: str | None
    extraction_usage: dict | None
    published: CandidateData | None
    pages: list[SnapshotPage]
    content_hash: str
    candidate_hash: str
    changes: list[str]
    history: list[dict]


class ReviewWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["correct", "approve", "reject", "request_review"]
    note: str = Field(min_length=1, max_length=2000)
    expected_hash: str = Field(min_length=64, max_length=64)
    candidate: CandidateData | None = None
    acknowledge_flags: bool = False
    source_completeness_confirmed: bool = False


def digest(candidate: dict) -> str:
    return hashlib.sha256(json.dumps(candidate, sort_keys=True).encode()).hexdigest()


def summary(version: OpportunityVersion) -> ReviewSummary:
    return ReviewSummary.model_validate(version, from_attributes=True)


def read(session: Session, identifier: uuid.UUID) -> ReviewView:
    version = session.get(OpportunityVersion, identifier)
    if version is None or version.extraction is None:
        raise APIError(404, "candidate_not_found", "This candidate could not be found.")
    opportunity = session.get(Opportunity, version.opportunity_id)
    published = (
        session.get(OpportunityVersion, opportunity.published_version_id)
        if opportunity.published_version_id
        else None
    )
    previous = published.extraction if published and published.id != version.id else None
    snapshot = session.get(SourceSnapshot, version.snapshot_id)
    fields = set(version.extraction) | set(previous or {})
    changes = sorted(
        key for key in fields if version.extraction.get(key) != (previous or {}).get(key)
    )
    return ReviewView(
        **summary(version).model_dump(),
        candidate=CandidateData.model_validate(version.extraction),
        extraction_provider=version.extraction_provider,
        extraction_model=version.extraction_model,
        extractor_version=version.extractor_version,
        extraction_usage=version.extraction_usage,
        published=CandidateData.model_validate(previous) if previous else None,
        pages=snapshot.pages,
        content_hash=snapshot.content_hash,
        candidate_hash=digest(version.extraction),
        changes=changes,
        history=[
            {
                "decision": r.decision,
                "note": r.note,
                "reviewer_id": str(r.reviewer_id),
                "created_at": r.created_at.isoformat(),
            }
            for r in session.scalars(
                select(CandidateReview)
                .where(CandidateReview.version_id == version.id)
                .order_by(CandidateReview.created_at)
            )
        ],
    )


def review(session: Session, identifier: uuid.UUID, actor: User, data: ReviewWrite) -> ReviewView:
    if not actor.is_admin:
        raise APIError(403, "admin_required", "Administrator access is required.")
    # Lock stable identity first to serialize approval of different candidate versions.
    existing = session.get(OpportunityVersion, identifier)
    if existing is None or existing.extraction is None:
        raise APIError(404, "candidate_not_found", "This candidate could not be found.")
    opportunity = session.scalar(
        select(Opportunity).where(Opportunity.id == existing.opportunity_id).with_for_update()
    )
    version = session.scalar(
        select(OpportunityVersion)
        .where(OpportunityVersion.id == identifier)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if version.publication_state != "draft":
        raise APIError(
            409,
            "candidate_not_editable",
            "Only draft candidates can be reviewed. Published versions are immutable.",
        )
    if data.expected_hash != digest(version.extraction):
        raise APIError(409, "candidate_changed", "The candidate changed. Reload before reviewing.")
    before = version.extraction
    candidate = data.candidate or CandidateData.model_validate(before)
    snapshot = session.get(SourceSnapshot, version.snapshot_id)
    try:
        validate_evidence(candidate, snapshot.pages)
    except ValueError as error:
        raise APIError(422, "invalid_source_evidence", str(error)) from None
    if data.decision == "approve":
        if opportunity.is_synthetic:
            raise APIError(
                422,
                "synthetic_not_publishable",
                "Synthetic fixtures cannot be published as verified opportunities.",
            )
        if not data.source_completeness_confirmed or (
            candidate.review_flags and not data.acknowledge_flags
        ):
            raise APIError(
                422,
                "review_confirmation_required",
                "Confirm source completeness and acknowledge the review flags before publishing.",
            )
        if not candidate.requirements or not candidate.issuer or not candidate.country:
            raise APIError(
                422,
                "candidate_incomplete",
                "Review the issuing authority, geography and requirements before publishing.",
            )
        if set(candidate.required_documents) != {d.document for d in candidate.document_evidence}:
            raise APIError(
                422,
                "document_evidence_required",
                "Each required document needs its own reviewed source citation before publication.",
            )
        published = (
            session.get(OpportunityVersion, opportunity.published_version_id)
            if opportunity.published_version_id
            else None
        )
        if published and published.version >= version.version:
            raise APIError(
                409,
                "stale_candidate",
                "A newer version is already published. Review a fresh candidate.",
            )
    metadata = candidate.model_dump(mode="json")
    version.extraction = metadata
    for key in [
        "title",
        "summary",
        "issuer",
        "category",
        "country",
        "state",
        "district",
        "benefits",
        "restrictions",
        "required_documents",
        "opens_on",
        "closes_on",
        "apply_url",
    ]:
        value = getattr(candidate, key)
        setattr(version, key, value if key != "country" or value else "unknown")
    if data.decision == "approve":
        # Requirements and publication pointer commit together; no partial public state.
        version.status = "verified"
        version.publication_state = "published"
        version.reviewer_id = actor.id
        version.last_verified_at = datetime.now(timezone.utc)
        version.supersedes_id = opportunity.published_version_id
        for requirement in candidate.requirements:
            record = Requirement(
                version_id=version.id,
                description=requirement.description,
                rule={**requirement.rule.model_dump(mode="json")},
                subject_context=requirement.subject_context,
                kind=requirement.kind,
                application_context=requirement.application_context,
            )
            session.add(record)
            session.flush()
            session.add(
                RequirementEvidence(
                    requirement_id=record.id,
                    source_url=requirement.evidence.source_url,
                    passage=requirement.evidence.passage,
                    page=str(requirement.evidence.page),
                )
            )
        for item in candidate.document_evidence:
            document = item.document
            citation = item.evidence
            record = Requirement(
                version_id=version.id,
                description="Required document: " + document,
                rule={"op": "condition", "condition": {"op": "unknown"}, "children": []},
                subject_context="person",
            )
            session.add(record)
            session.flush()
            session.add(
                RequirementEvidence(
                    requirement_id=record.id,
                    source_url=citation.source_url,
                    passage=citation.passage,
                    page=str(citation.page),
                )
            )
        opportunity.published_version_id = version.id
    elif data.decision == "reject":
        version.publication_state = "rejected"
    session.add(
        CandidateReview(
            version_id=version.id,
            reviewer_id=actor.id,
            decision=data.decision,
            note=data.note,
            before=before,
            after=metadata,
        )
    )
    session.add(
        AuditEvent(
            actor_id=actor.id,
            action="candidate_" + data.decision,
            object_id=version.id,
            details={
                "snapshot_id": str(snapshot.id),
                "content_hash": snapshot.content_hash,
                "candidate_hash": digest(metadata),
            },
        )
    )
    session.commit()
    return read(session, version.id)
