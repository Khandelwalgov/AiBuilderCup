import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from opportunity_platform.subjects.service import SubjectRef

DocumentType = Literal[
    "income_certificate",
    "parental_income_certificate",
    "personal_income_certificate",
    "disability_certificate",
    "udid",
    "registration_certificate",
    "age_proof",
    "education_certificate",
    "other",
]


class DocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: SubjectRef
    display_name: str = Field(min_length=1, max_length=100)
    document_type: DocumentType
    issuer: str | None = Field(default=None, max_length=120)
    issued_on: date | None = None
    expires_on: date | None = None
    approved_uses: list[Literal["readiness"]] = Field(min_length=1, max_length=1)
    requirement_ids: list[uuid.UUID] = Field(default_factory=list, max_length=30)
    replaces_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def dates(self):
        if self.issued_on and self.expires_on and self.expires_on < self.issued_on:
            raise ValueError("Expiry must not precede issue date")
        if len(self.requirement_ids) != len(set(self.requirement_ids)):
            raise ValueError("Requirements must be unique")
        return self


class LinkWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requirement_ids: list[uuid.UUID] = Field(min_length=1, max_length=30)
    expected_revision: str = Field(min_length=64, max_length=64)


class DeleteWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: str = Field(min_length=64, max_length=64)


class DocumentView(BaseModel):
    id: uuid.UUID
    subject: SubjectRef
    display_name: str
    document_type: str
    media_type: str
    byte_size: int
    sha256: str | None
    issuer: str | None
    issued_on: date | None
    expires_on: date | None
    status: str
    verification: Literal["not_verified"] = "not_verified"
    created_at: datetime
    uploaded_at: datetime | None
    approved_uses: list[str]
    linked_requirements: list[dict]
    replaces_id: uuid.UUID | None
    revision: str
    purge_pending: bool


class RequirementDocumentView(BaseModel):
    requirement_id: uuid.UUID
    version_id: uuid.UUID
    opportunity_id: uuid.UUID
    opportunity_title: str
    requirement: str
    document_type: str
    compatibility: dict
    citations: list[dict]
    documentary_status: str
    documents: list[DocumentView]


class AccessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purpose: Literal["preview", "download"]


class AccessView(BaseModel):
    token: str
    expires_in_seconds: int = 60


class DocumentCapabilities(BaseModel):
    uploads_enabled: bool
    max_file_bytes: int
    max_count: int
    allowed_media_types: list[str] = ["application/pdf", "image/jpeg", "image/png"]
    production_uploads_ready: bool = False
