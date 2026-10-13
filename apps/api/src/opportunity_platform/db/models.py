"""Persistence models. Relationships do not imply permission; services enforce ownership."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Entity(Base):
    __abstract__ = True
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Entity):
    __tablename__ = "users"
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True)
    is_admin: Mapped[bool] = mapped_column(default=False, server_default="false")
    language: Mapped[str] = mapped_column(default="en")
    notification_preferences: Mapped[dict] = mapped_column(JSON, default=dict)


class Person(Entity):
    __tablename__ = "people"
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), unique=True)
    display_name: Mapped[str]


class Household(Entity):
    __tablename__ = "households"
    name: Mapped[str]


class HouseholdMembership(Entity):
    __tablename__ = "household_memberships"
    household_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("households.id"), index=True)
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("people.id"), index=True)
    starts_on: Mapped[date]
    ends_on: Mapped[date | None]
    __table_args__ = (CheckConstraint("ends_on IS NULL OR ends_on >= starts_on"),)


class Relationship(Entity):
    __tablename__ = "relationships"
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("people.id"))
    related_person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("people.id"))
    kind: Mapped[str]
    starts_on: Mapped[date]
    ends_on: Mapped[date | None]
    __table_args__ = (CheckConstraint("person_id != related_person_id"),)


class ConsentGrant(Entity):
    __tablename__ = "consent_grants"
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("people.id"), index=True)
    grantee_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    scope: Mapped[str]
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Business(Entity):
    __tablename__ = "businesses"
    name: Mapped[str]
    legal_status: Mapped[str | None]


class BusinessMembership(Entity):
    __tablename__ = "business_memberships"
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str]
    __table_args__ = (
        UniqueConstraint("business_id", "user_id"),
        CheckConstraint("role IN ('owner','admin','editor','viewer')"),
    )


class SubjectEntity(Entity):
    __abstract__ = True
    person_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("people.id"), index=True)
    household_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("households.id"), index=True)
    business_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("businesses.id"), index=True)


SUBJECT_CHECK = (
    "(CASE WHEN person_id IS NULL THEN 0 ELSE 1 END + CASE WHEN household_id IS "
    "NULL THEN 0 ELSE 1 END + CASE WHEN business_id IS NULL THEN 0 ELSE 1 END) = "
    "1"
)


class ProfileFact(SubjectEntity):
    __tablename__ = "profile_facts"
    key: Mapped[str]
    value: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    origin: Mapped[str]
    verification: Mapped[str] = mapped_column(default="unknown")
    valid_from: Mapped[date | None]
    valid_until: Mapped[date | None]
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (
        CheckConstraint(SUBJECT_CHECK),
        CheckConstraint("origin IN ('user_supplied','verified_document','ai_inference','unknown')"),
    )


class Document(SubjectEntity):
    __tablename__ = "documents"
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    blob_key: Mapped[str]
    media_type: Mapped[str]
    approved_uses: Mapped[list] = mapped_column(JSON, default=list)
    __table_args__ = (CheckConstraint(SUBJECT_CHECK),)


class EvidenceLink(Entity):
    __tablename__ = "evidence_links"
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"))
    fact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profile_facts.id"))
    reference: Mapped[str | None]
    __table_args__ = (UniqueConstraint("document_id", "fact_id"),)


class Source(Entity):
    __tablename__ = "sources"
    name: Mapped[str]
    authority: Mapped[str | None]
    url: Mapped[str | None]
    is_synthetic: Mapped[bool] = mapped_column(default=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_successful_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(default="discovered")


class Opportunity(Entity):
    __tablename__ = "opportunities"
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"), index=True)
    published_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("opportunity_versions.id", use_alter=True, name="fk_published_version")
    )
    source_key: Mapped[str]
    category: Mapped[str] = mapped_column(index=True)
    is_synthetic: Mapped[bool] = mapped_column(default=False)
    __table_args__ = (UniqueConstraint("source_id", "source_key"),)


class OpportunityVersion(Entity):
    __tablename__ = "opportunity_versions"
    opportunity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("opportunities.id"), index=True)
    version: Mapped[int]
    publication_state: Mapped[str] = mapped_column(default="draft", server_default="draft")
    category: Mapped[str | None]
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_snapshots.id", name="fk_version_snapshot")
    )
    extraction: Mapped[dict | None] = mapped_column(JSON)
    title: Mapped[str]
    summary: Mapped[str]
    issuer: Mapped[str | None]
    status: Mapped[str] = mapped_column(default="needs_review")
    country: Mapped[str] = mapped_column(default="IN", index=True)
    state: Mapped[str | None] = mapped_column(index=True)
    district: Mapped[str | None] = mapped_column(index=True)
    applicability: Mapped[list] = mapped_column(JSON, default=list)
    benefits: Mapped[str | None]
    restrictions: Mapped[list] = mapped_column(JSON, default=list)
    required_documents: Mapped[list] = mapped_column(JSON, default=list)
    effective_on: Mapped[date | None]
    opens_on: Mapped[date | None]
    closes_on: Mapped[date | None] = mapped_column(index=True)
    expires_on: Mapped[date | None]
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("opportunity_versions.id"))
    apply_url: Mapped[str | None]
    source_url: Mapped[str | None]
    content_hash: Mapped[str | None]
    snapshot_key: Mapped[str | None]
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    __table_args__ = (
        UniqueConstraint("opportunity_id", "version"),
        CheckConstraint("version > 0"),
        CheckConstraint(
            "publication_state IN ('draft','published','rejected')", name="ck_publication_state"
        ),
        CheckConstraint(
            "publication_state != 'published' OR status = 'verified'", name="ck_published_verified"
        ),
        CheckConstraint(
            (
                "status IN ('discovered','parsed','needs_review','verified',"
                "'superseded','closed','source_unreachable')"
            )
        ),
        CheckConstraint(
            (
                "status != 'verified' OR (source_url IS NOT NULL AND last_verified_at IS NOT "
                "NULL AND reviewer_id IS NOT NULL)"
            )
        ),
        Index("ix_version_geo", "country", "state", "district"),
    )


class Requirement(Entity):
    __tablename__ = "requirements"
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("opportunity_versions.id"), index=True)
    description: Mapped[str]
    rule: Mapped[dict] = mapped_column(JSON)
    subject_context: Mapped[str]


class RequirementEvidence(Entity):
    __tablename__ = "requirement_evidence"
    requirement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("requirements.id"))
    source_url: Mapped[str]
    passage: Mapped[str]
    page: Mapped[str | None]


class MatchEvaluation(SubjectEntity):
    __tablename__ = "match_evaluations"
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("opportunity_versions.id"))
    status: Mapped[str]
    fact_snapshot: Mapped[dict] = mapped_column(JSON)
    results: Mapped[list] = mapped_column(JSON)
    __table_args__ = (
        CheckConstraint(SUBJECT_CHECK),
        CheckConstraint(
            (
                "status IN ('potential_match','possibly_eligible_missing_information',"
                "'known_blocker','not_eligible_on_known_facts','ready_for_application_preflight')"
            )
        ),
    )


class ActionItem(SubjectEntity):
    __tablename__ = "action_items"
    title: Mapped[str]
    status: Mapped[str] = mapped_column(default="pending")
    __table_args__ = (CheckConstraint(SUBJECT_CHECK),)


class ActionDependency(Entity):
    __tablename__ = "action_dependencies"
    action_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("action_items.id"))
    requirement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("requirements.id"))
    __table_args__ = (UniqueConstraint("action_id", "requirement_id"),)


class SourceSnapshot(Entity):
    __tablename__ = "source_snapshots"
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"), index=True)
    content_hash: Mapped[str]
    media_type: Mapped[str]
    source_url: Mapped[str]
    # Public authoritative text only; never personal documents. Binary blobs go to GCS later.
    pages: Mapped[list] = mapped_column(JSON)
    byte_count: Mapped[int]
    response_metadata: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("source_id", "content_hash"),)


class IngestionRun(Entity):
    __tablename__ = "ingestion_runs"
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"), index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source_snapshots.id"))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str]
    diagnostic_code: Mapped[str | None]
    model: Mapped[str | None]
    extractor_version: Mapped[str | None]
    changed: Mapped[bool | None]
    http_status: Mapped[int | None]


class CandidateReview(Entity):
    __tablename__ = "candidate_reviews"
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("opportunity_versions.id"), index=True)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str]
    note: Mapped[str]
    before: Mapped[dict | None] = mapped_column(JSON)
    after: Mapped[dict | None] = mapped_column(JSON)


class AuditEvent(Entity):
    __tablename__ = "audit_events"
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str]
    object_id: Mapped[uuid.UUID]
    details: Mapped[dict] = mapped_column(JSON, default=dict)
