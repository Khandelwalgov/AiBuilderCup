import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from opportunity_platform.ingestion.schemas import FieldCitation

Status = Literal[
    "discovered", "parsed", "needs_review", "verified", "superseded", "closed", "source_unreachable"
]


class SourceView(BaseModel):
    name: str
    authority: str | None
    url: str | None
    last_checked_at: datetime | None
    last_successful_check_at: datetime | None
    status: str


class CitationView(BaseModel):
    source_url: str
    passage: str
    page: str | None


class RequirementView(BaseModel):
    id: uuid.UUID
    description: str
    rule: dict
    subject_context: str
    citations: list[CitationView]


class OpportunityView(BaseModel):
    id: uuid.UUID
    version: int
    publication_state: str
    requirements: list[RequirementView]
    field_evidence: list[FieldCitation]
    review_flags: list[str]
    missing_fields: list[str]
    title: str
    summary: str
    category: str
    issuer: str | None
    is_synthetic: bool
    status: Status
    country: str
    state: str | None
    district: str | None
    applicability: list[dict]
    benefits: str | None
    restrictions: list[str]
    required_documents: list[str]
    opens_on: date | None
    closes_on: date | None
    apply_url: str | None
    source_url: str | None
    first_seen_at: datetime
    last_verified_at: datetime | None
    source: SourceView


class OpportunityPage(BaseModel):
    items: list[OpportunityView]
    total: int
    next_cursor: str | None


class Facets(BaseModel):
    categories: list[str]
    states: list[str]
    districts: list[str]
    total: int
    synthetic: int
    verified: int
    official_sources: int
