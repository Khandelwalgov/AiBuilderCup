"""Version-aware reusable actions. Facts are never inferred from kinship or an action status."""

import hashlib
import json
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select

from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import (
    ActionDependency,
    ActionItem,
    AuditEvent,
    MatchEvaluation,
    Opportunity,
    OpportunityVersion,
    Requirement,
    RequirementEvidence,
    User,
)
from opportunity_platform.eligibility import service as eligibility
from opportunity_platform.eligibility.rules import FactInput
from opportunity_platform.opportunities.service import catalogue
from opportunity_platform.subjects.service import SubjectRef, resolve, subject_facts


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: SubjectRef = Field(default_factory=SubjectRef)
    development: bool = False


class SimulationRequest(PlanRequest):
    facts: list[FactInput] = Field(max_length=30)


class ActionView(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    identity: str
    kind: str
    fact: str | None = None
    opportunities: list[dict]
    explanation: str
    documentary_status: str | None = None
    documents: list[dict] = []


class PlanView(BaseModel):
    subject: SubjectRef
    hypothetical: bool
    evaluations: list[eligibility.EvaluationView]
    actions: list[ActionView]
    known_blockers: list[dict]


def leaves(rule):
    return (
        [rule.condition]
        if rule.op == "condition"
        else [c for r in rule.children for c in leaves(r)]
    )


def identities(requirement):
    # One reusable information/evidence dependency, independent of tree shape and thresholds.
    # Income definition/period/date and subject context remain distinct.
    if requirement.document_dependency and requirement.result.kind == "evidence_gap":
        return [
            (
                dict(requirement.document_dependency),
                requirement.requirement.removeprefix("Required document: "),
            )
        ]
    conditions = leaves(requirement.rule)
    result = []
    for c in conditions:
        if c.op == "document" and c.fact in requirement.result.missing and requirement.citations:
            from opportunity_platform.planning.documents import dependency

            names = {
                "has_udid_certificate": "Unique Disability Identity card (UDID)",
                "has_disability_certificate": "Disability certificate",
            }
            if c.fact in names:
                normalized = dependency(names[c.fact], requirement.citations[0])
                if normalized:
                    result.append((normalized, names[c.fact]))
                    continue
        if c.fact and c.fact in requirement.result.missing:
            payload = {
                "fact": c.fact,
                "kind": "document" if c.op == "document" else "information",
                "income_period": c.income_period,
                "income_definition": c.income_definition,
                "as_of": str(c.as_of),
            }
            result.append((payload, c.fact.replace("_", " ")))
    if not result:
        # Uninterpreted clauses never merge on an empty unknown rule hash.
        result = [
            (
                {"requirement": str(requirement.requirement_id), "kind": "clarification"},
                requirement.requirement,
            )
        ]
    return result


def application_context(session, kind, identifier, version_id):
    previous = session.scalar(
        select(MatchEvaluation)
        .where(
            MatchEvaluation.version_id == version_id,
            getattr(MatchEvaluation, kind + "_id") == identifier,
        )
        .order_by(MatchEvaluation.created_at.desc(), MatchEvaluation.id)
        .limit(1)
    )
    return previous.fact_snapshot.get("application_type") if previous else None


def build(session, uid, subject, hypothetical=None, development=False):
    user, obj, _ = resolve(session, uid, subject)
    subject = SubjectRef(kind=subject.kind, id=obj.id)
    # Serialize plan mutation to avoid duplicate actions across simultaneous requests.
    session.execute(select(User).where(User.id == user.id).with_for_update())
    rows = list(
        session.execute(
            catalogue(development)
            .where(
                OpportunityVersion.publication_state == "published",
                Opportunity.published_version_id == OpportunityVersion.id,
            )
            .order_by(Opportunity.id)
            .limit(100)
        )
    )
    from opportunity_platform.documents.service import readiness

    documentary = {str(r.requirement_id): r for r in readiness(session, uid, subject)}
    facts = subject_facts(session, subject.kind, obj.id)
    requirements = {}
    for requirement in session.scalars(
        select(Requirement)
        .where(Requirement.version_id.in_([row[1].id for row in rows]))
        .order_by(Requirement.id)
    ):
        requirements.setdefault(requirement.version_id, []).append(requirement)
    rows = [
        row
        for row in rows
        if not requirements.get(row[1].id)
        or any(r.subject_context == subject.kind for r in requirements[row[1].id])
    ]
    evidence = {}
    reqids = [r.id for group in requirements.values() for r in group]
    if reqids:
        for item in session.scalars(
            select(RequirementEvidence).where(RequirementEvidence.requirement_id.in_(reqids))
        ):
            evidence.setdefault(item.requirement_id, []).append(item)
    evaluations = [
        eligibility.check(
            session,
            uid,
            row[0].id,
            subject,
            hypothetical,
            commit=False,
            application_type=application_context(session, subject.kind, obj.id, row[1].id),
            _prepared={
                "row": row,
                "facts": facts,
                "requirements": requirements.get(row[1].id, []),
                "evidence": evidence,
                "documentary": documentary,
            },
        )
        for row in rows
    ]
    grouped = {}
    blockers = []
    for ev in evaluations:
        for r in ev.requirements:
            link = {
                "id": str(ev.opportunity_id),
                "version_id": str(ev.version_id),
                "requirement_id": str(r.requirement_id),
                "requirement": r.requirement,
                "citations": [c.model_dump() for c in r.citations],
            }
            if r.result.outcome == "unsatisfied":
                blockers.append(link)
                continue
            if r.result.outcome != "unknown":
                continue
            for payload, label in identities(r):
                payload["subject_context"] = subject.kind
                identity = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
                entry = grouped.setdefault(
                    identity,
                    {
                        "title": (
                            "Verify evidence: "
                            if payload["kind"] == "document"
                            else "Clarify: "
                            if payload["kind"] == "clarification"
                            else "Provide: "
                        )
                        + label,
                        "kind": payload["kind"],
                        "fact": payload.get("fact"),
                        "opportunities": [],
                        "documentary_status": None,
                        "documents": [],
                    },
                )
                if payload["kind"] == "document":
                    states = [entry["documentary_status"], r.documentary_status]
                    entry["documentary_status"] = (
                        "uploaded_unverified"
                        if "uploaded_unverified" in states
                        else r.documentary_status or entry["documentary_status"] or "not_provided"
                    )
                    for document in r.documents:
                        if not any(d["id"] == document["id"] for d in entry["documents"]):
                            entry["documents"].append(document)
                if link not in entry["opportunities"]:
                    entry["opportunities"].append(link)
    evaluations.sort(
        key=lambda ev: (
            {
                "potential_match": 0,
                "possibly_eligible_missing_information": 1,
                "not_eligible_on_known_facts": 2,
            }.get(ev.status, 3),
            ev.opportunity_title,
        )
    )
    actions = []
    existing = {
        a.identity: a
        for a in session.scalars(
            select(ActionItem).where(getattr(ActionItem, subject.kind + "_id") == obj.id)
        )
    }
    for identity, entry in grouped.items():
        record = existing.get(identity)
        if hypothetical is None:
            if record is None:
                record = ActionItem(
                    **{subject.kind + "_id": obj.id}, identity=identity, title=entry["title"]
                )
                session.add(record)
                session.flush()
            if record.status not in {"pending", "in_progress"}:
                record.status = "pending"
            record.details = entry
            session.execute(delete(ActionDependency).where(ActionDependency.action_id == record.id))
            for requirement_id in {link["requirement_id"] for link in entry["opportunities"]}:
                session.add(
                    ActionDependency(action_id=record.id, requirement_id=uuid.UUID(requirement_id))
                )
        actions.append(
            ActionView(
                id=record.id if record else uuid.uuid4(),
                identity=identity,
                status="hypothetical" if hypothetical is not None else record.status,
                explanation=(
                    "Prioritized by the number of current published opportunities affected. "
                    "Completing a task does not verify evidence "
                    "or override a substantive condition."
                ),
                **entry,
            )
        )
    if hypothetical is None:
        for identity, record in existing.items():
            if identity not in grouped:
                record.status = "resolved_or_superseded"
                session.execute(
                    delete(ActionDependency).where(ActionDependency.action_id == record.id)
                )
        session.commit()
    return PlanView(
        subject=subject,
        hypothetical=hypothetical is not None,
        evaluations=evaluations,
        actions=sorted(
            actions, key=lambda a: (-len({link["id"] for link in a.opportunities}), a.title)
        ),
        known_blockers=blockers,
    )


class ActionProgressWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["pending", "in_progress"]


class ActionProgressView(BaseModel):
    status: str


def progress(session, uid, identifier, data):
    record = session.scalar(select(ActionItem).where(ActionItem.id == identifier).with_for_update())
    if record is None:
        raise APIError(404, "action_not_found", "This action is not available.")
    kind = next(
        k for k in ["person", "household", "business"] if getattr(record, k + "_id") is not None
    )
    user, _, _ = resolve(
        session, uid, SubjectRef(kind=kind, id=getattr(record, kind + "_id")), True
    )
    current = session.scalar(
        select(ActionDependency.id)
        .join(Requirement, Requirement.id == ActionDependency.requirement_id)
        .join(Opportunity, Opportunity.published_version_id == Requirement.version_id)
        .where(ActionDependency.action_id == record.id, Opportunity.is_synthetic.is_(False))
        .limit(1)
    )
    if current is None or record.status not in {"pending", "in_progress"}:
        raise APIError(
            409, "action_outdated", "Refresh the current plan before updating an action."
        )
    record.status = data.status
    session.add(
        AuditEvent(
            actor_id=user.id,
            action="action_progress_updated",
            object_id=record.id,
            details={"status": data.status, "changes_evidence_verification": False},
        )
    )
    session.commit()
    return ActionProgressView(status=record.status)
