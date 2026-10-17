import hashlib
import uuid
from datetime import date
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from opportunity_platform.corpus.schemas import ManifestRecord

Category = Literal["education", "welfare", "business", "procurement", "healthcare", "employment"]
Availability = Literal["verified_current", "historical", "unknown", "potentially_expired"]
ApplicationStatus = Literal["open", "closed", "not_established"]


def official_url(value: str) -> str:
    url = urlsplit(value)
    host = (url.hostname or "").lower()
    if (
        url.scheme not in {"http", "https"}
        or url.username
        or url.password
        or url.port not in {None, 80, 443}
        or not (host.endswith(".gov.in") or host.endswith(".nic.in"))
    ):
        raise ValueError("A public official government URL is required")
    return value


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResearchPage(ClosedModel):
    page: int = Field(ge=1, le=10000)
    text: str = Field(min_length=1, max_length=100000)
    basis: Literal["original_extracted_text", "offline_ocr"]
    text_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    image_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def integrity(self):
        if hashlib.sha256(self.text.encode()).hexdigest() != self.text_sha256:
            raise ValueError("Research page text checksum mismatch")
        if self.basis == "offline_ocr" and not self.image_sha256:
            raise ValueError("OCR evidence requires its original-page render fingerprint")
        return self


class ResearchSource(ClosedModel):
    snapshot_id: uuid.UUID
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_url: str = Field(max_length=2000)
    pages: list[ResearchPage] = Field(min_length=1, max_length=20)
    _official = field_validator("source_url")(official_url)

    @model_validator(mode="after")
    def unique_pages(self):
        if len({p.page for p in self.pages}) != len(self.pages):
            raise ValueError("Duplicate page in source")
        return self


class ResearchCitation(ClosedModel):
    field: Literal[
        "title",
        "summary",
        "authority",
        "jurisdiction",
        "benefit",
        "availability",
        "application",
        "deadline",
    ]
    snapshot_id: uuid.UUID
    page: int = Field(ge=1)
    passage: str = Field(min_length=5, max_length=4000)


class ResearchInput(ClosedModel):
    key: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,159}$")
    title: str = Field(min_length=5, max_length=300)
    authority: str | None = Field(default=None, max_length=250)
    category: Category
    jurisdiction: str = Field(min_length=2, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    kind: Literal["scheme", "scheme_component", "institutional_admission", "tender", "award"]
    summary: str = Field(min_length=30, max_length=1600)
    benefit: str | None = Field(default=None, max_length=600)
    availability: Availability = "unknown"
    availability_note: str = Field(min_length=15, max_length=1000)
    application_status: ApplicationStatus = "not_established"
    apply_url: str | None = Field(default=None, max_length=2000)
    closes_on: date | None = None
    as_of: date
    limitations: list[str] = Field(min_length=1, max_length=12)
    sources: list[ResearchSource] = Field(min_length=1, max_length=12)
    citations: list[ResearchCitation] = Field(min_length=2, max_length=50)
    verification_state: Literal["source_backed_research"] = "source_backed_research"
    eligibility_verified: Literal[False] = False

    @field_validator("apply_url")
    @classmethod
    def safe_application(cls, value):
        return official_url(value) if value else None

    @model_validator(mode="after")
    def evidence(self):
        from opportunity_platform.ingestion.corpus_policy.validation import date_supported
        from opportunity_platform.ingestion.schemas import normalize

        sources = {s.snapshot_id: s for s in self.sources}
        if len(sources) != len(self.sources):
            raise ValueError("Duplicate source identity")
        for c in self.citations:
            source = sources.get(c.snapshot_id)
            if source is None or not any(
                p.page == c.page and normalize(c.passage) in normalize(p.text) for p in source.pages
            ):
                raise ValueError("Citation is absent from its exact captured/derived page")
        fields = {c.field for c in self.citations}
        required = {"title", "summary", "jurisdiction"}
        if self.authority:
            required.add("authority")
        if self.benefit:
            required.add("benefit")
        if self.availability != "unknown":
            required.add("availability")
        if self.apply_url or self.application_status != "not_established":
            required.add("application")
        if self.closes_on:
            required.add("deadline")
            if not any(
                c.field == "deadline" and date_supported(self.closes_on, c.passage)
                for c in self.citations
            ):
                raise ValueError("Deadline is not stated in cited evidence")
        if required - fields:
            raise ValueError("Material listing fields lack source citations")
        if self.application_status == "open" and (
            self.availability != "verified_current"
            or not self.closes_on
            or self.closes_on < self.as_of
            or not self.apply_url
        ):
            raise ValueError("Open applications need a current cited window and official route")
        if self.apply_url and not any(
            c.field == "application" and self.apply_url in c.passage for c in self.citations
        ):
            raise ValueError("Application URL absent from cited passage")
        return self


class ResearchDocumentLink(ClosedModel):
    snapshot_id: uuid.UUID
    source_url: str
    content_hash: str
    pages: list[int]
    excerpt: str
    basis: str


class ResearchCard(ClosedModel):
    evidence_strength: str = "unassessed"
    archive: bool = False
    documents: list[ResearchDocumentLink] = []
    id: uuid.UUID
    key: str
    title: str
    authority: str | None
    category: Category
    jurisdiction: str
    district: str | None
    kind: str
    summary: str
    benefit: str | None
    availability: Availability
    availability_note: str
    application_status: ApplicationStatus
    apply_url: str | None
    closes_on: date | None
    as_of: date
    source_url: str
    source_count: int
    verification_state: Literal["source_backed_research"] = "source_backed_research"
    eligibility_verified: Literal[False] = False


class ResearchDetail(ResearchCard):
    limitations: list[str]
    sources: list[ResearchSource]
    citations: list[ResearchCitation]


class ResearchResults(ClosedModel):
    neural_status: str = "not_requested"
    items: list[ResearchCard]
    total: int
    next_cursor: uuid.UUID | None


class ResearchFacets(ClosedModel):
    catalogue_total: int = 0
    archive_total: int = 0
    evidence_strengths: dict[str, int] = {}
    kinds: dict[str, int] = {}
    total: int
    categories: list[str]
    jurisdictions: list[str]
    availability: dict[str, int]
    application_status: dict[str, int]
    source_documents: int


class OriginalResearchPage(ClosedModel):
    page: int = Field(ge=1, le=10000)
    text: str = Field(max_length=100000)
    source_url: str = Field(max_length=2000)
    _official = field_validator("source_url")(official_url)


class CapturedResearchSource(ClosedModel):
    """An existing immutable public acquisition, previously absent from the product DB."""

    acquisition: ManifestRecord
    original_pages: list[OriginalResearchPage] = Field(min_length=1, max_length=500)
    title: str = Field(min_length=5, max_length=300)
    authority: str | None = Field(default=None, max_length=250)

    @model_validator(mode="after")
    def official_capture(self):
        official_url(self.acquisition.canonical_source_url)
        official_url(self.acquisition.final_url)
        if any(p.source_url != self.acquisition.canonical_source_url for p in self.original_pages):
            raise ValueError("Captured page URL differs from acquisition identity")
        if len({p.page for p in self.original_pages}) != len(self.original_pages):
            raise ValueError("Duplicate captured page")
        if sum(len(p.text) for p in self.original_pages) > 2_000_000:
            raise ValueError("Captured source exceeds public text bound")
        return self
