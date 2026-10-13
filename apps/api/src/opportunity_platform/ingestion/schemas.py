from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from opportunity_platform.eligibility.rules import Condition, Rule


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_url: str
    passage: str = Field(min_length=5, max_length=6000)
    page: int = Field(ge=1)
    language: str = Field(min_length=2, max_length=50)
    basis: Literal["explicit", "interpretation"]


class FieldCitation(BaseModel):
    field: str
    citation: Citation


class CandidateRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(min_length=5, max_length=2000)
    rule: Rule
    evidence: Citation
    subject_context: Literal["person", "business", "household"] = "person"


class CandidateData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=5, max_length=300)
    summary: str = Field(min_length=10, max_length=3000)
    issuer: str | None = None
    category: str = Field(min_length=2, max_length=80)
    country: str | None = None
    state: str | None = None
    district: str | None = None
    benefits: str | None = None
    restrictions: list[str] = Field(default_factory=list, max_length=50)
    required_documents: list[str] = Field(default_factory=list, max_length=50)
    opens_on: date | None = None
    closes_on: date | None = None
    apply_url: str | None = None
    field_evidence: list[FieldCitation] = Field(default_factory=list, max_length=100)
    requirements: list[CandidateRequirement] = Field(default_factory=list, max_length=50)
    review_flags: list[str] = Field(default_factory=list, max_length=50)
    missing_fields: list[str] = Field(default_factory=list, max_length=50)


class ExtractedRequirement(BaseModel):
    description: str
    combine: Literal["all", "any"]
    conditions: list[Condition] = Field(min_length=1, max_length=30)
    evidence: Citation
    subject_context: Literal["person", "business", "household"]


class Extraction(CandidateData):
    # Gemini extracts shallow groups. Complex source logic must be flagged for human review.
    requirements: list[ExtractedRequirement] = Field(max_length=50)

    def candidate(self) -> CandidateData:
        data = self.model_dump(mode="json", exclude={"requirements"})
        data["requirements"] = [
            CandidateRequirement(
                description=req.description,
                rule=Rule(
                    op=req.combine,
                    children=[Rule(op="condition", condition=c) for c in req.conditions],
                ),
                evidence=req.evidence,
                subject_context=req.subject_context,
            ).model_dump(mode="json")
            for req in self.requirements
        ]
        return CandidateData.model_validate(data)


def normalize(text: str) -> str:
    return " ".join(text.split())


def validate_evidence(candidate: CandidateData, pages: list[dict]):
    from urllib.parse import urlparse

    # Exact whitespace-normalized evidence matching; the model cannot forge a passage.
    evidence = [f.citation for f in candidate.field_evidence] + [
        r.evidence for r in candidate.requirements
    ]
    for citation in evidence:
        page = next(
            (
                p
                for p in pages
                if p["page"] == citation.page and p.get("source_url") == citation.source_url
            ),
            None,
        )
        if page is None or normalize(citation.passage) not in normalize(page["text"]):
            raise ValueError("Citation does not match the recorded source page")
    fields = {item.field for item in candidate.field_evidence}
    for name in [
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
        value = getattr(candidate, name)
        if value and name not in fields:
            raise ValueError(f"Source evidence missing for {name}")
    if candidate.apply_url:
        parsed = urlparse(candidate.apply_url)
        if parsed.scheme != "https" or parsed.username or parsed.password:
            raise ValueError("Application URL must be HTTPS")
        if not any(candidate.apply_url in page["text"] for page in pages):
            raise ValueError("Application URL was not found verbatim in the source")
