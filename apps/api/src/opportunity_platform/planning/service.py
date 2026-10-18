"""Version-aware reusable actions. Facts are never inferred from kinship or an action status."""

import hashlib
import json
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select, text

from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import (
    ActionDependency,
    ActionItem,
    AuditEvent,
    MatchEvaluation,
    Opportunity,
    Requirement,
    User,
)
from opportunity_platform.eligibility import service as eligibility
from opportunity_platform.eligibility.rules import FactInput
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
    retrieval_truncated: bool = False


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
    from opportunity_platform.documents.service import readiness
    from opportunity_platform.retrieval.service import (
        SearchRequest,
        SearchSubject,
        load_catalogue,
        select_candidates,
    )

    documentary = {str(r.requirement_id): r for r in readiness(session, uid, subject)}
    facts = subject_facts(session, subject.kind, obj.id)
    request = SearchRequest(development=development)
    rows, requirements, evidence, fts = load_catalogue(session, request)
    candidate_facts = facts
    if hypothetical is not None:
        overridden = {f.key for f in hypothetical}
        from opportunity_platform.eligibility.engine import FactRecord

        candidate_facts = [f for f in facts if f.key not in overridden] + [
            FactRecord(
                id="scenario",
                key=f.key,
                value=f.value,
                context={
                    "income_period": f.income_period,
                    "income_definition": f.income_definition,
                },
            )
            for f in hypothetical
        ]
    pairs, _, pair_count = select_candidates(
        rows,
        requirements,
        [SearchSubject(str(obj.id), subject.kind, "Selected subject", obj.id, candidate_facts)],
        request,
        fts,
    )
    rows = [row for _, row in pairs]
    truncated = len(rows) < pair_count
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
            if (identity or "").startswith("research:"):
                continue
            if identity not in grouped and not truncated:
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
        retrieval_truncated=truncated,
    )


class ActionProgressWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["pending", "in_progress", "completed"]


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
    if (record.identity or "").startswith("research:"):
        from opportunity_platform.research.guidance import GuidanceRequest

        active = research_actions(
            session,
            uid,
            GuidanceRequest(subject=SubjectRef(kind=kind, id=getattr(record, kind + "_id"))),
            persist=False,
        )
        if not any(a.identity == record.identity for a in active):
            raise APIError(
                409, "action_outdated", "Refresh the research plan; this dependency changed."
            )
        record.status = data.status
        session.add(
            AuditEvent(
                actor_id=user.id,
                action="research_action_progress_updated",
                object_id=record.id,
                details={"status": data.status, "changes_evidence_verification": False},
            )
        )
        session.commit()
        return ActionProgressView(status=record.status)
    current = session.scalar(
        select(ActionDependency.id)
        .join(Requirement, Requirement.id == ActionDependency.requirement_id)
        .join(Opportunity, Opportunity.published_version_id == Requirement.version_id)
        .where(ActionDependency.action_id == record.id, Opportunity.is_synthetic.is_(False))
        .limit(1)
    )
    if (
        current is None
        or record.status not in {"pending", "in_progress"}
        or data.status == "completed"
    ):
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


def research_actions(session, uid, request, *, persist=False):
    """Use existing subject-scoped actions for provisional, evidenced dependencies.

    A progress write never changes facts or documentary verification. Hypotheses
    produce ephemeral identities only. Shared semantics stay within one subject.
    """
    from opportunity_platform.research.guidance import guidance

    persist = persist and not (
        request.scenario
        or request.overrides
        or request.member_overrides
        or request.people
        or request.excluded_subject_keys
    )
    user, obj, _ = resolve(session, uid, request.subject, write=persist, read_only=not persist)
    grouped = {}
    offset = 0
    while True:
        result = guidance(session, uid, request.model_copy(update={"limit": 24, "offset": offset}))
        for item in result.items:
            for condition in item.conditions:
                if not condition.action or not condition.evidence_available:
                    continue
                payload = {
                    "subject": item.subject_id,
                    "semantic": condition.semantic,
                    "rule": condition.rule.model_dump(mode="json"),
                }
                identity = (
                    "research:"
                    + hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
                )
                entry = grouped.setdefault(
                    identity,
                    {
                        "title": condition.action,
                        "kind": "provisional_research",
                        "fact": condition.rule.condition.fact
                        if condition.rule.op == "condition"
                        else None,
                        "opportunities": [],
                        "subject_id": item.subject_id,
                        "subject_kind": item.subject_kind,
                        "fictional": item.fictional,
                    },
                )
                for listing in [item.listing, *item.components]:
                    entry["opportunities"].append(
                        {
                            "id": str(listing.id),
                            "title": listing.title,
                            "requirement": condition.title,
                            "snapshot_id": condition.snapshot_id,
                            "page": condition.page,
                            "passage": condition.passage,
                        }
                    )
        offset += 24
        if offset >= result.candidate_count:
            break
    actions = []
    if persist:
        session.execute(select(User).where(User.id == user.id).with_for_update())
    for identity, entry in sorted(grouped.items()):
        kind, identifier = entry["subject_kind"], uuid.UUID(entry["subject_id"])
        # Family actions belong to the individual member whose facts produced them.
        if not entry["fictional"]:
            resolve(
                session,
                uid,
                SubjectRef(kind=kind, id=identifier),
                write=persist,
                read_only=not persist,
            )
        if persist:
            # Serialize a shared subject's dependency across different administrators.
            session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"),
                {"key": int(hashlib.sha256(identity.encode()).hexdigest()[:15], 16)},
            )
        record = (
            None
            if entry["fictional"]
            else session.scalar(
                select(ActionItem).where(
                    ActionItem.identity == identity, getattr(ActionItem, kind + "_id") == identifier
                )
            )
        )
        if persist:
            if record is None:
                record = ActionItem(
                    **{kind + "_id": identifier}, identity=identity, title=entry["title"]
                )
                session.add(record)
                session.flush()
            record.details = entry
        actions.append(
            ActionView(
                id=record.id if record else uuid.uuid5(identifier, identity),
                identity=identity,
                title=entry["title"],
                kind=entry["kind"],
                fact=entry["fact"],
                status="hypothetical"
                if request.scenario or request.overrides or request.member_overrides
                else record.status
                if record
                else "pending",
                opportunities=entry["opportunities"],
                explanation=(
                    "Provisional research action. Completion does not verify evidence "
                    "or establish eligibility, current funding or admission."
                ),
            )
        )
    if persist:
        session.commit()
    return sorted(actions, key=lambda a: (-len(a.opportunities), a.title))
