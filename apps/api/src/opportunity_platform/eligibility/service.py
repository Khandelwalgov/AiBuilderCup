import uuid
from datetime import date, datetime, timezone

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import (
    MatchEvaluation,
    Opportunity,
    Requirement,
    RequirementEvidence,
)
from opportunity_platform.eligibility.engine import Result, evaluate
from opportunity_platform.eligibility.rules import Rule
from opportunity_platform.opportunities.schemas import CitationView
from opportunity_platform.opportunities.service import catalogue
from opportunity_platform.profiles.service import account, facts_for, person


class RequirementResult(BaseModel):
    requirement_id: uuid.UUID
    requirement: str
    rule: Rule
    result: Result
    citations: list[CitationView]
    next_steps: list[str]


class EvaluationView(BaseModel):
    id: uuid.UUID
    opportunity_id: uuid.UUID
    version_id: uuid.UUID
    version: int
    evaluated_at: datetime
    status: str
    requirements: list[RequirementResult]
    disclaimer: str


def check(session: Session, uid: str, opportunity_id: uuid.UUID) -> EvaluationView:
    user = account(session, uid)
    profile = person(session, user)
    facts = facts_for(session, profile)
    row = session.execute(catalogue().where(Opportunity.id == opportunity_id)).first()
    if row is None:
        raise APIError(
            404,
            "published_opportunity_not_found",
            "Only reviewed, published real opportunities can be evaluated.",
        )
    opportunity, version, _source = row
    results = []
    for requirement in session.scalars(
        select(Requirement).where(Requirement.version_id == version.id).order_by(Requirement.id)
    ):
        rule = Rule.model_validate(requirement.rule)
        result = (
            evaluate(rule, facts, date.today())
            if requirement.subject_context == "person"
            else Result(
                outcome="unknown",
                reason="This condition needs a separately authorized household "
                "or business context.",
                blockers=["subject:" + requirement.subject_context],
            )
        )
        citations = [
            CitationView(source_url=e.source_url, passage=e.passage, page=e.page)
            for e in session.scalars(
                select(RequirementEvidence).where(
                    RequirementEvidence.requirement_id == requirement.id
                )
            )
        ]
        if requirement.description.startswith("Required document: "):
            import hashlib

            key = "document:" + hashlib.sha256(requirement.description.encode()).hexdigest()[:20]
            result = Result(
                outcome="unknown",
                reason="Required documentary evidence has not been verified by this prototype.",
                missing=[requirement.description],
                blockers=[key],
                kind="evidence_gap",
            )
        next_steps = [f"Provide or clarify: {key}." for key in result.missing]
        if result.kind == "evidence_gap":
            next_steps.append(
                (
                    "Obtain the required evidence and have it verified. Self-reporting a "
                    "document is not verification."
                )
            )
        if result.outcome == "unsatisfied":
            next_steps.append(
                (
                    "Check the cited condition and correct inaccurate profile information; do "
                    "not misrepresent facts."
                )
            )
        results.append(
            RequirementResult(
                requirement_id=requirement.id,
                requirement=requirement.description,
                rule=rule,
                result=result,
                citations=citations,
                next_steps=next_steps,
            )
        )
    if any(r.result.outcome == "unsatisfied" for r in results):
        status = "not_eligible_on_known_facts"
    elif not results or any(r.result.outcome == "unknown" for r in results):
        status = "possibly_eligible_missing_information"
    else:
        # Satisfied self-reported conditions never imply document-verified readiness.
        status = "potential_match"
    now = datetime.now(timezone.utc)
    record = MatchEvaluation(
        person_id=profile.id,
        version_id=version.id,
        status=status,
        fact_snapshot={
            "facts": [f.model_dump(mode="json") for f in facts],
            "evaluation_date": now.date().isoformat(),
            "engine_version": "1",
        },
        results=[r.model_dump(mode="json") for r in results],
    )
    session.add(record)
    session.commit()
    return EvaluationView(
        id=record.id,
        opportunity_id=opportunity.id,
        version_id=version.id,
        version=version.version,
        evaluated_at=now,
        status=status,
        requirements=results,
        disclaimer=(
            "Preliminary assessment using the reviewed source and supplied facts. "
            "Missing evidence remains unknown. The issuing authority decides "
            "eligibility, selection, availability and approval."
        ),
    )
