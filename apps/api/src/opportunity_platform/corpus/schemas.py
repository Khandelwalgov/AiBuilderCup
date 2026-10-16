"""Versioned acquisition configuration and public manifest contracts."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(pattern=r"^[a-z0-9-]+$")
    authority: str
    jurisdiction: str  # India or a named state; classification is registry metadata.
    category: str
    seeds: list[str] = Field(min_length=1)
    allowed_hosts: list[str] = Field(min_length=1)
    # Mandatory path restriction for shared government CDNs.
    path_prefixes: dict[str, list[str]] = Field(default_factory=dict)
    adapter: Literal["html", "pdf", "feed", "playwright"] = "html"
    document_pattern: str = r"(?i)\.pdf(?:$|\?)"
    page_pattern: str = r"(?!)"
    exclude_pattern: str = (
        r"(?i)recruitment|vacanc|annual.report|budget|telephone|directory|staff|roster"
    )
    max_depth: int = Field(default=1, ge=0, le=3)
    max_pages: int = Field(default=8, ge=1, le=30)
    max_documents: int = Field(default=25, ge=1, le=100)
    terms_url: str | None = None
    access: Literal["public", "needs_review", "manual_access_required"] = "needs_review"
    access_note: str

    @model_validator(mode="after")
    def restricted_cdn(self):
        for host in self.allowed_hosts:
            if host == "cdnbbsr.s3waas.gov.in" and not self.path_prefixes.get(host):
                raise ValueError("Shared CDN must have explicit issuing-authority path prefixes")
        return self


class Candidate(BaseModel):
    url: str
    discovery_url: str
    title: str
    publication_date: date | None = None
    effective_date: date | None = None
    closes_on: date | None = None
    related_urls: list[str] = Field(default_factory=list)
    association_basis: str | None = None
    relation: Literal["document", "amendment", "possible_replacement"] = "document"


class ManifestRecord(BaseModel):
    """One immutable snapshot, with all source/index associations in discoveries."""

    schema_version: Literal[1] = 1
    snapshot_id: str
    document_id: str
    previous_snapshot_id: str | None
    canonical_source_url: str
    originating_domain: str
    final_url: str
    downloaded_at: datetime
    sha256: str
    size_bytes: int
    format: Literal["pdf", "html"]
    blob_path: str
    http_metadata: dict
    retrieval_status: Literal["captured"] = "captured"
    publication_state: Literal["unreviewed"] = "unreviewed"
    validation: dict
    discoveries: list[dict]
