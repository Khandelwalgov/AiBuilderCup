"""Permission-scoped hybrid retrieval. Exact evaluation never writes in this module."""

import json
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from time import perf_counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from opportunity_platform.core.config import settings
from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import (
    Opportunity,
    OpportunityVersion,
    Requirement,
    RequirementEvidence,
    Source,
)
from opportunity_platform.eligibility.engine import FactRecord
from opportunity_platform.eligibility.rules import FactKey
from opportunity_platform.eligibility.service import (
    EvaluationView,
    evaluate_requirements,
    overall_status,
)
from opportunity_platform.opportunities.schemas import OpportunityView
from opportunity_platform.opportunities.service import catalogue, view
from opportunity_platform.retrieval.neural import (
    PolicyRepresentation,
    SubjectRepresentation,
    neural_retriever,
)
from opportunity_platform.subjects.service import SubjectRef, resolve, subject_facts
from opportunity_platform.subjects.service import view as workspace_view

Mode = Literal["me", "family", "member", "business", "explore"]


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Mode = "me"
    subject_id: uuid.UUID | None = None
    q: str = Field(default="", max_length=200)
    category: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    include_national: bool = True
    interests: list[str] = Field(default_factory=list, max_length=10)
    development: bool = False
    shortlist: int | None = Field(default=None, ge=50, le=500)
    application_type: Literal["fresh", "renewal"] | None = None


@dataclass
class SearchSubject:
    key: str
    kind: str
    name: str
    id: uuid.UUID | None
    facts: list[FactRecord]
    hypothetical: bool = False


class Assessment(BaseModel):
    subject_key: str
    subject_kind: str
    subject_id: uuid.UUID | None
    subject_name: str
    hypothetical: bool
    evaluation: EvaluationView
    reasons: list[str]


class Recommendation(BaseModel):
    opportunity: OpportunityView
    assessments: list[Assessment]
    channels: list[str]


class SearchResponse(BaseModel):
    items: list[Recommendation]
    subjects: list[dict]
    catalogue_count: int
    eligible_pair_count: int
    assessed_pair_count: int
    truncated: bool
    neural_status: str
    timings_ms: dict[str, float]
    subject_coverage: dict[str, int]
    category_coverage: dict[str, int]
    notice: str = "Preliminary cited assessments; shortlist coverage is not guaranteed complete."


def authorized_subjects(session, uid, request):
    if request.mode == "explore":
        return []
    kind = {"me": "person", "member": "person", "family": "household", "business": "business"}[
        request.mode
    ]
    if request.mode != "me" and request.subject_id is None:
        raise APIError(422, "select_subject", "Select an authorized person, household or business.")
    ref = SubjectRef(kind=kind, id=None if request.mode == "me" else request.subject_id)
    _, obj, _ = resolve(session, uid, ref)

    def make(kind, obj):
        return SearchSubject(
            f"{kind}:{obj.id}",
            kind,
            getattr(obj, "display_name", getattr(obj, "name", kind)),
            obj.id,
            subject_facts(session, kind, obj.id),
        )

    result = [make(kind, obj)]
    if request.mode == "family":
        for member in workspace_view(session, uid, ref).members:
            if member.get("access") == "authorized":
                _, person, _ = resolve(session, uid, SubjectRef(id=member["id"]))
                result.append(make("person", person))
    if len(result) > 30:
        raise APIError(
            422, "too_many_subjects", "Choose a specific family member for this large household."
        )
    return result


def published_query(request):
    if request.development:
        if not settings().enable_development_catalogue:
            raise APIError(404, "development_disabled", "The development catalogue is disabled.")
        query = (
            select(Opportunity, OpportunityVersion, Source)
            .join(OpportunityVersion, Opportunity.published_version_id == OpportunityVersion.id)
            .join(Source, Source.id == Opportunity.source_id)
            .where(Opportunity.is_synthetic.is_(True), Source.is_synthetic.is_(True))
        )
    else:
        query = catalogue(False)
    query = query.where(
        Opportunity.published_version_id == OpportunityVersion.id,
        OpportunityVersion.publication_state == "published",
        OpportunityVersion.status == "verified",
    )
    if request.category:
        query = query.where(
            func.coalesce(OpportunityVersion.category, Opportunity.category) == request.category
        )
    for col, value in [
        (OpportunityVersion.state, request.state),
        (OpportunityVersion.district, request.district),
    ]:
        if value:
            national = (
                OpportunityVersion.state.is_(None)
                & OpportunityVersion.district.is_(None)
                & OpportunityVersion.country.in_(["IN", "India"])
            )
            query = query.where(
                (col == value) | national if request.include_national else col == value
            )
    return query


def load_catalogue(session, request):
    rows = session.execute(published_query(request).order_by(Opportunity.id)).all()
    reqs, evidence = defaultdict(list), defaultdict(list)
    if rows:
        for req in session.scalars(
            select(Requirement)
            .where(Requirement.version_id.in_([v.id for _, v, _ in rows]))
            .order_by(Requirement.id)
        ):
            reqs[req.version_id].append(req)
        ids = [r.id for group in reqs.values() for r in group]
        if ids:
            for e in session.scalars(
                select(RequirementEvidence).where(RequirementEvidence.requirement_id.in_(ids))
            ):
                evidence[e.requirement_id].append(e)
    fts = {}
    if request.q.strip():
        tsquery = func.websearch_to_tsquery("english", request.q)
        rank = func.ts_rank_cd(OpportunityVersion.search_vector, tsquery)
        for o, v, _s, score in session.execute(
            published_query(request)
            .add_columns(rank)
            .where(OpportunityVersion.search_vector.op("@@")(tsquery))
        ):
            fts[o.id] = score or 0
    return rows, reqs, evidence, fts


def rule_keys(rule):
    if rule.get("op") == "condition":
        return {rule.get("condition", {}).get("fact")} - {None}
    return set().union(*(rule_keys(c) for c in rule.get("children", [])))


def select_candidates(rows, reqs, subjects, request, fts, neural=None):
    """Round-robin subjects and channels, stratified coverage; no threshold exclusion."""
    neural = neural or neural_retriever()
    neural.candidate_ranks = {}
    limit = request.shortlist or settings().retrieval_shortlist_size
    streams, annotations, total = [], defaultdict(set), 0
    policies = [
        PolicyRepresentation(
            str(o.id),
            str(v.id),
            v.content_hash or "",
            f"{v.title}\n{v.summary}\nBenefits: {v.benefits or 'not established'}",
            [
                {
                    "rule": r.rule,
                    "description": r.description,
                    "subject_context": r.subject_context,
                    "kind": r.kind,
                    "application_context": r.application_context,
                }
                for r in reqs[v.id]
            ],
            {
                "category": v.category or o.category,
                "country": v.country,
                "state": v.state,
                "district": v.district,
            },
        )
        for o, v, _ in rows
    ]
    for subject in subjects:
        applicable = [
            row
            for row in rows
            if not reqs[row[1].id]
            or any(r.subject_context == subject.kind for r in reqs[row[1].id])
        ]
        total += len(applicable)
        known = {f.key for f in subject.facts if f.value is not None}
        # Available keys improve ranking, never exclude missing/large/small values.
        structured = sorted(
            applicable,
            key=lambda row: (
                -len(known & set().union(*(rule_keys(r.rule) for r in reqs[row[1].id]))),
                str(row[0].id),
            ),
        )
        text = sorted(
            [row for row in applicable if row[0].id in fts],
            key=lambda r: (-fts[r[0].id], str(r[0].id)),
        )
        buckets = defaultdict(list)
        for row in applicable:
            o, v, _ = row
            signature = tuple(sorted(set().union(*(rule_keys(r.rule) for r in reqs[v.id]))))
            buckets[(v.category or o.category, v.state or "", signature)].append(row)
        coverage = []
        while any(buckets.values()):
            for key in sorted(buckets):
                if buckets[key]:
                    coverage.append(buckets[key].pop(0))
        representation = SubjectRepresentation(
            subject.kind,
            [f.model_dump(mode="json") for f in subject.facts],
            sorted(set(FactKey.__args__) - known),
            request.q,
        )
        applicable_ids = {str(row[0].id) for row in applicable}
        neural_ids = neural.retrieve(
            [p for p in policies if p.opportunity_id in applicable_ids], representation, limit
        )
        by_id = {str(row[0].id): row for row in applicable}
        vectors = [by_id[key] for key in neural_ids if key in by_id]
        for rank, row in enumerate(vectors, 1):
            neural.candidate_ranks[(subject.key, row[0].id)] = rank
        channels = [
            ("coverage", coverage),
            ("full_text", text),
            ("structured", structured),
            ("neural", vectors),
        ]
        queues = []
        for channel, candidates in channels:
            queues.append(list(candidates))
            for o, v, _ in candidates:
                annotations[(subject.key, o.id)].add(channel)
        merged, seen = [], set()
        while any(queues):
            for queue in queues:
                if queue:
                    row = queue.pop(0)
                    if row[0].id not in seen:
                        merged.append((subject, row))
                        seen.add(row[0].id)
        streams.append(merged)
    # Small catalogues are exhaustive across all authorized subjects. In particular,
    # automatic discovery must not hide an eligible policy behind a vector/PAIR cap.
    # At most 150 published versions × the existing 30-subject authorization limit.
    if len(rows) <= 150:
        limit = total
    pairs = []
    while any(streams) and len(pairs) < limit:
        for stream in streams:
            if stream and len(pairs) < limit:
                pairs.append(stream.pop(0))
    return pairs, annotations, total


def search(session: Session, uid: str, request: SearchRequest, subjects=None):
    start = perf_counter()
    subjects = authorized_subjects(session, uid, request) if subjects is None else subjects
    rows, reqs, evidence, fts = load_catalogue(session, request)
    neural = neural_retriever(session)
    if request.mode == "explore":
        # Full browse remains paginated GET /opportunities; this endpoint is personalized only.
        raise APIError(
            422, "use_full_catalogue", "Use the full published catalogue browser for Explore All."
        )
    pairs, annotations, pair_count = select_candidates(rows, reqs, subjects, request, fts, neural)
    generation_ms = (perf_counter() - start) * 1000
    start = perf_counter()
    assessments, action_counts = [], Counter()
    from opportunity_platform.planning.service import identities

    def action_keys(results):
        return {
            json.dumps(payload, sort_keys=True)
            for r in results
            if r.result.outcome == "unknown"
            for payload, _ in identities(r)
        }

    for subject, row in pairs:
        o, v, _ = row
        results = evaluate_requirements(
            reqs[v.id],
            subject.facts,
            subject.kind,
            evidence,
            application_type=request.application_type,
        )
        evaluation = EvaluationView(
            id=uuid.uuid5(v.id, subject.key),
            opportunity_id=o.id,
            version_id=v.id,
            version=v.version,
            evaluated_at=datetime.now(timezone.utc),
            status=overall_status(results),
            requirements=results,
            disclaimer="Hypothetical preliminary assessment"
            if subject.hypothetical
            else "Preliminary assessment; authorities decide.",
            opportunity_title=v.title,
        )
        for key in action_keys(results):
            action_counts[(subject.key, key)] += 1
        assessments.append((subject, row, evaluation))
    exact_ms = (perf_counter() - start) * 1000
    start = perf_counter()
    grouped = {}
    for subject, row, evaluation in assessments:
        o, v, _ = row
        satisfied = sum(r.result.outcome == "satisfied" for r in evaluation.requirements)

        reasons = [f"{subject.name}: {evaluation.status.replace('_', ' ')}."]
        for r in evaluation.requirements:
            reasons.append(f"{r.requirement}: {r.result.reason}")
        if v.closes_on:
            reasons.append(f"Published closing date: {v.closes_on.isoformat()}.")
            if v.closes_on < date.today():
                reasons.append(
                    "The published application deadline has passed; a new round is not established."
                )
        if (v.category or o.category) in request.interests:
            reasons.append("Matches your selected category interest.")
        shared = sum(
            action_counts[(subject.key, key)] > 1 for key in action_keys(evaluation.requirements)
        )
        if shared:
            reasons.append(
                "Some missing information or evidence is shared across these opportunities."
            )
        # Known failures are a separate last bucket; unknowns never become failures.
        score = (
            bool(v.closes_on and v.closes_on < date.today()),
            evaluation.status == "not_eligible_on_known_facts",
            -(
                fts.get(o.id, 0)
                + (
                    1 / (60 + neural.candidate_ranks[(subject.key, o.id)])
                    if (subject.key, o.id) in neural.candidate_ranks
                    else 0
                )
            ),
            -(v.category in request.interests),
            -satisfied,
            -shared,
            v.closes_on if v.closes_on and v.closes_on >= date.today() else date.max,
            str(o.id),
        )
        assessment = Assessment(
            subject_key=subject.key,
            subject_kind=subject.kind,
            subject_id=subject.id,
            subject_name=subject.name,
            hypothetical=subject.hypothetical,
            evaluation=evaluation,
            reasons=reasons,
        )
        if o.id not in grouped:
            grouped[o.id] = [row, [], set(), score]
        grouped[o.id][1].append(assessment)
        grouped[o.id][2].update(annotations[(subject.key, o.id)])
        grouped[o.id][3] = min(grouped[o.id][3], score)
    ordered = sorted(grouped.values(), key=lambda g: g[3])
    items = [
        Recommendation(
            opportunity=view(row, session, reqs, evidence),
            assessments=values,
            channels=sorted(channels),
        )
        for row, values, channels, _ in ordered
    ]
    rank_ms = (perf_counter() - start) * 1000
    return SearchResponse(
        items=items,
        subjects=[
            {"key": s.key, "kind": s.kind, "id": str(s.id) if s.id else None, "name": s.name}
            for s in subjects
        ],
        catalogue_count=len(rows),
        eligible_pair_count=pair_count,
        assessed_pair_count=len(pairs),
        truncated=len(pairs) < pair_count,
        neural_status=neural.status,
        timings_ms={
            "candidate_generation": generation_ms,
            "exact_evaluation": exact_ms,
            "ranking": rank_ms,
        },
        subject_coverage=dict(Counter(s.key for s, _ in pairs)),
        category_coverage=dict(Counter(item.opportunity.category for item in items)),
    )
