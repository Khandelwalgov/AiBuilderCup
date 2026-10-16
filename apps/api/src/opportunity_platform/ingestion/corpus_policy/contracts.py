"""Closed contracts for archive-derived candidates and independent review; never approval."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from opportunity_platform.ingestion.schemas import CandidateData, Citation, Extraction

VERSION = "corpus-policy-v1"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Clause(Strict):
    id: str
    source_url: str
    page: int
    section: str | None = None
    passage: str


class Coverage(Strict):
    clause_id: str
    disposition: Literal["represented", "not_applicable", "unrepresentable", "needs_review"]
    requirement_indexes: list[int] = Field(default_factory=list, max_length=50)
    field_names: list[str] = Field(default_factory=list, max_length=30)
    reason: str = Field(min_length=5, max_length=2000)


class PolicyCandidate(Strict):
    candidate: CandidateData
    coverage: list[Coverage] = Field(max_length=2000)


class RawPolicyExtraction(Strict):
    # Same shallow extraction contract as the existing Gemini pipeline.
    candidate: Extraction
    coverage: list[Coverage] = Field(max_length=2000)

    def normalized(self):
        return PolicyCandidate(candidate=self.candidate.candidate(), coverage=self.coverage)


class Issue(Strict):
    code: str = Field(min_length=3, max_length=100)
    severity: Literal["info", "warning", "error", "critical"]
    field: str = Field(max_length=200)
    message: str = Field(min_length=5, max_length=2000)
    evidence: Citation | None = None
    suggested_correction: str = Field(min_length=5, max_length=2000)
    human_required: bool = False


class AIReview(Strict):
    # No approve/verified/publication field exists in the AI contract.
    assessment: Literal["no_issues_detected", "issues_found"]
    candidate_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    examined_clause_ids: list[str] = Field(max_length=2000)
    issues: list[Issue] = Field(max_length=100)


class Stage(Strict):
    attempt: int
    candidate_hash: str
    candidate: dict | None
    issues: list[Issue]
    independent_review: AIReview | None = None


class Outcome(Strict):
    status: Literal["draft_for_human_review", "human_escalation"]
    candidate: PolicyCandidate | None
    stages: list[Stage]
    repair_cycles: int
    model_calls: int
    usage: list[dict]
    human_required: Literal[True] = True
