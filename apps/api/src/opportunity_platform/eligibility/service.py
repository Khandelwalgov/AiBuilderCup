import hashlib
import json
import uuid
from datetime import date, datetime, timezone

from pydantic import BaseModel
from sqlalchemy import select, text
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
    document_dependency: dict | None = None
    documentary_status: str | None = None
    documents: list[dict] = []
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
    changes: list[dict] = []


def evaluate_requirements(
    requirements,
    facts,
    subject_kind,
    evidence_by_requirement=None,
    documentary=None,
    application_type=None,
    today=None,
):
    """Pure assessment: no session, writes, permission inference or AI."""
    evidence_by_requirement = evidence_by_requirement or {}
    documentary = documentary or {}
    results = []
    for requirement in requirements:
        rule = Rule.model_validate(requirement.rule)
        result = (
            evaluate(rule, facts, today or date.today())
            if requirement.subject_context == subject_kind
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
            for e in evidence_by_requirement.get(requirement.id, [])
        ]
        if (
            requirement.description.startswith("Required document: ")
            and result.outcome != "not_applicable"
            and requirement.subject_context == subject_kind
        ):
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
                document_dependency=requirement.document_dependency,
                documentary_status=documentary[str(requirement.id)].documentary_status
                if str(requirement.id) in documentary
                else None,
                documents=[
                    d.model_dump(mode="json") for d in documentary[str(requirement.id)].documents
                ]
                if str(requirement.id) in documentary
                else [],
                result=result,
                citations=citations,
                next_steps=next_steps,
            )
        )
    return results


def overall_status(results):
    if any(r.result.outcome == "unsatisfied" for r in results):
        return "not_eligible_on_known_facts"
    elif (
        not results
        or all(r.result.outcome == "not_applicable" for r in results)
        or any(r.result.outcome == "unknown" for r in results)
    ):
        return "possibly_eligible_missing_information"
    else:
        # Satisfied self-reported conditions never imply document-verified readiness.
        return "potential_match"


def check(
    session: Session,
    uid: str,
    opportunity_id: uuid.UUID,
    subject: SubjectRef | None = None,
    hypothetical: list[FactInput] | None = None,
    commit: bool = True,
    application_type: str | None = None,
    _prepared: dict | None = None,
    development: bool = False,
) -> EvaluationView:
    if application_type not in {None, "fresh", "renewal"}:
        raise APIError(422, "invalid_application_context", "Choose fresh, renewal or unknown.")
    subject = subject or SubjectRef()
    _user, profile, _role = resolve(session, uid, subject)
    if hypothetical is None:
        # Same subject across different authorized callers must serialize too.
        namespace = session.scalar(text("select current_schema()"))
        lock = int.from_bytes(
            hashlib.sha256(f"{namespace}:assessment:{subject.kind}:{profile.id}".encode()).digest()[
                :8
            ],
            "big",
            signed=True,
        )
        session.execute(text("select pg_advisory_xact_lock(:key)"), {"key": lock})
        # Permissions are checked on every request before returning any cached assessment.
        resolve(session, uid, subject)
    facts = _prepared["facts"] if _prepared else subject_facts(session, subject.kind, profile.id)
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
    row = (
        _prepared["row"]
        if _prepared
        else session.execute(
            catalogue(development).where(
                Opportunity.id == opportunity_id,
                OpportunityVersion.publication_state == "published",
                Opportunity.published_version_id == OpportunityVersion.id,
            )
        ).first()
    )
    if row is None:
        raise APIError(
            404,
            "published_opportunity_not_found",
            "Only reviewed, published real opportunities can be evaluated.",
        )
    opportunity, version, _source = row
    from opportunity_platform.documents.service import readiness

    documentary = (
        _prepared.get("documentary", {})
        if _prepared
        else {str(r.requirement_id): r for r in readiness(session, uid, subject)}
    )
    results = []
    requirements = (
        _prepared["requirements"]
        if _prepared
        else list(
            session.scalars(
                select(Requirement)
                .where(Requirement.version_id == version.id)
                .order_by(Requirement.id)
            )
        )
    )
    if requirements and not any(r.subject_context == subject.kind for r in requirements):
        raise APIError(
            422,
            "unsupported_subject_context",
            "The reviewed conditions do not support this subject type. "
            "Choose an appropriate authorized context.",
        )
    evidence_by_requirement = _prepared["evidence"] if _prepared else {}
    if requirements and not _prepared:
        for evidence in session.scalars(
            select(RequirementEvidence).where(
                RequirementEvidence.requirement_id.in_([r.id for r in requirements])
            )
        ):
            evidence_by_requirement.setdefault(evidence.requirement_id, []).append(evidence)
    results = evaluate_requirements(
        requirements, facts, subject.kind, evidence_by_requirement, documentary, application_type
    )
    status = overall_status(results)
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
    # Compare with the prior distinct snapshot; unchanged loads retain this meaningful diff.
    baseline = previous
    now = datetime.now(timezone.utc)
    relevant_keys = {c.fact for r in results for c in rule_leaves(r.rule) if c.fact}
    if relevant_keys & {
        "current_education_level",
        "enrollment_mode",
        "school_recognized_or_government",
    }:
        relevant_keys.add("student_status")
    canonical_facts = sorted(
        [
            {
                **{
                    k: v for k, v in f.model_dump(mode="json").items() if k not in {"id", "context"}
                },
                "context": {k: f.context.get(k) for k in ["income_period", "income_definition"]},
            }
            for f in facts
            if f.key in relevant_keys
        ],
        key=lambda f: json.dumps(f, sort_keys=True),
    )
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "subject": [subject.kind, str(profile.id)],
                "version": str(version.id),
                "facts": canonical_facts,
                "date": now.date().isoformat(),
                "application_type": application_type,
                "engine": "4",
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    record = MatchEvaluation(
        **{subject.kind + "_id": profile.id},
        version_id=version.id,
        fingerprint=fingerprint,
        status=status,
        fact_snapshot={
            "facts": [f.model_dump(mode="json") for f in facts],
            "evaluation_date": now.date().isoformat(),
            "engine_version": "4",
            "application_type": application_type,
        },
        results=[
            r.model_dump(mode="json", exclude={"documents", "documentary_status"}) for r in results
        ],
    )
    if (
        hypothetical is None
        and previous
        and previous.version_id == version.id
        and previous.fingerprint == fingerprint
    ):
        record = previous
        baseline = session.scalar(
            select(MatchEvaluation)
            .join(OpportunityVersion, OpportunityVersion.id == MatchEvaluation.version_id)
            .where(
                OpportunityVersion.opportunity_id == opportunity.id,
                getattr(MatchEvaluation, subject.kind + "_id") == profile.id,
                MatchEvaluation.id != record.id,
                MatchEvaluation.created_at <= record.created_at,
            )
            .order_by(MatchEvaluation.created_at.desc(), MatchEvaluation.id)
            .limit(1)
        )
        now = previous.created_at
        if commit:
            session.commit()
    elif hypothetical is None:
        session.add(record)
        if commit:
            session.commit()
        else:
            session.flush()
    else:
        record.id = uuid.uuid4()
    previous_results = {r["requirement"]: r for r in baseline.results} if baseline else {}
    changes = [
        {
            "requirement": r.requirement,
            "before": previous_results[r.requirement]["result"]["outcome"]
            if r.requirement in previous_results
            else "not_previously_assessed",
            "after": r.result.outcome,
        }
        for r in results
        if baseline
        and (
            r.requirement not in previous_results
            or previous_results[r.requirement]["result"]["outcome"] != r.result.outcome
        )
    ]
    return EvaluationView(
        changes=changes,
        id=record.id,
        opportunity_id=opportunity.id,
        version_id=version.id,
        version=version.version,
        opportunity_title=version.title,
        previous_status=baseline.status if baseline else None,
        previous_version=session.get(OpportunityVersion, baseline.version_id).version
        if baseline
        else None,
        evaluated_at=now,
        status=status,
        requirements=results,
        disclaimer=(
            "Preliminary assessment using the reviewed source and supplied facts. "
            "Missing evidence remains unknown. The issuing authority decides "
            "eligibility, selection, availability and approval."
        ),
    )


def rule_leaves(rule):
    return (
        [rule.condition]
        if rule.op == "condition"
        else [c for r in rule.children for c in rule_leaves(r)]
    )
