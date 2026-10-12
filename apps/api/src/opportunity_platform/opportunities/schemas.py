import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

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


class OpportunityView(BaseModel):
    id: uuid.UUID
    version: int
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
