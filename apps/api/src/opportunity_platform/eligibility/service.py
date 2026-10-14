import uuid
from datetime import date, datetime, timezone

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import (
    MatchEvaluation,
    Opportunity,
    OpportunityVersion,
    Requirement,
    RequirementEvidence,
)
from opportunity_platform.eligibility.engine import FactRecord, Result, evaluate
from opportunity_platform.eligibility.rules import FactInput, Rule
from opportunity_platform.opportunities.schemas import CitationView
from opportunity_platform.opportunities.service import catalogue
from opportunity_platform.subjects.service import SubjectRef, resolve, subject_facts


class RequirementResult(BaseModel):
    requirement_id: uuid.UUID
    requirement: str
    rule: Rule
    kind: str = "eligibility"
    application_context: str = "all"
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
    opportunity_title: str = ""
    previous_status: str | None = None
    previous_version: int | None = None


def check(
    session: Session,
    uid: str,
    opportunity_id: uuid.UUID,
    subject: SubjectRef | None = None,
    hypothetical: list[FactInput] | None = None,
    commit: bool = True,
    application_type: str | None = None,
) -> EvaluationView:
    if application_type not in {None, "fresh", "renewal"}:
        raise APIError(422, "invalid_application_context", "Choose fresh, renewal or unknown.")
    subject = subject or SubjectRef()
    _user, profile, _role = resolve(session, uid, subject)
    facts = subject_facts(session, subject.kind, profile.id)
    if hypothetical is not None:
        keys = {f.key for f in hypothetical}
        facts = [f for f in facts if f.key not in keys] + [
            FactRecord(
                id="hypothetical",
                key=f.key,
                value=f.value,
                context={
                    "income_period": f.income_period,
                    "income_definition": f.income_definition,
                },
                valid_from=f.valid_from,
                valid_until=f.valid_until,
            )
            for f in hypothetical
        ]
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
            if requirement.subject_context == subject.kind
            else Result(
                outcome="unknown",
                reason="This condition needs a separately authorized household "
                "or business context.",
                blockers=["subject:" + requirement.subject_context],
            )
        )
        if requirement.kind in {"procedure", "selection", "interpretation"}:
            result = Result(
                outcome="unknown",
                reason=(
                    "This is an administrative, selection or interpretation "
                    "condition requiring clarification."
                ),
                blockers=["clarification:" + str(requirement.id)],
            )
        if requirement.application_context != "all":
            if application_type and application_type != requirement.application_context:
                result = Result(
                    outcome="not_applicable",
                    reason="This condition applies only to "
                    + requirement.application_context
                    + " applications.",
                )
            elif not application_type:
                result = Result(
                    outcome="unknown",
                    reason="Clarify whether this opportunity application is fresh or renewal.",
                    missing=["application_type"],
                    blockers=["context:" + str(requirement.id)],
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
                kind=requirement.kind,
                application_context=requirement.application_context,
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
    previous = session.scalar(
        select(MatchEvaluation)
        .join(OpportunityVersion, OpportunityVersion.id == MatchEvaluation.version_id)
        .where(
            OpportunityVersion.opportunity_id == opportunity.id,
            getattr(MatchEvaluation, subject.kind + "_id") == profile.id,
        )
        .order_by(MatchEvaluation.created_at.desc(), MatchEvaluation.id)
        .limit(1)
    )
    previous_version = (
        session.get(OpportunityVersion, previous.version_id).version if previous else None
    )
    now = datetime.now(timezone.utc)
    record = MatchEvaluation(
        **{subject.kind + "_id": profile.id},
        version_id=version.id,
        status=status,
        fact_snapshot={
            "facts": [f.model_dump(mode="json") for f in facts],
            "evaluation_date": now.date().isoformat(),
            "engine_version": "2",
            "application_type": application_type,
        },
        results=[r.model_dump(mode="json") for r in results],
    )
    if hypothetical is None:
        session.add(record)
        if commit:
            session.commit()
        else:
            session.flush()
    else:
        record.id = uuid.uuid4()
    return EvaluationView(
        id=record.id,
        opportunity_id=opportunity.id,
        version_id=version.id,
        version=version.version,
        opportunity_title=version.title,
        previous_status=previous.status if previous else None,
        previous_version=previous_version,
        evaluated_at=now,
        status=status,
        requirements=results,
        disclaimer=(
            "Preliminary assessment using the reviewed source and supplied facts. "
            "Missing evidence remains unknown. The issuing authority decides "
            "eligibility, selection, availability and approval."
        ),
    )
