"""Read-only research guidance over public listings, never eligibility evaluation.

Jurisdiction is a discovery signal, not proof of domicile, category, income,
current funding or an application window. The approved-policy engine remains separate.
"""

import uuid
from datetime import date
from types import SimpleNamespace
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from opportunity_platform.db.models import ResearchListing
from opportunity_platform.eligibility.engine import FactRecord
from opportunity_platform.eligibility.rules import FactInput
from opportunity_platform.planning.service import ActionView
from opportunity_platform.scenarios.service import FictionalPerson
from opportunity_platform.subjects.service import SubjectRef, resolve, subject_facts

from .conditions import Comparison, compare, parent_key
from .integration import quality
from .schemas import ResearchCard

LOCATION_KEYS = {
    "domicile_state",
    "domicile_district",
    "residence_state",
    "residence_district",
    "business_registration_state",
    "business_registration_district",
}


class GuidanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: SubjectRef = Field(default_factory=SubjectRef)
    overrides: list[FactInput] = Field(default_factory=list, max_length=30)
    scenario: bool = False
    limit: int = Field(default=8, ge=1, le=24)
    offset: int = Field(default=0, ge=0, le=10000)
    q: str = Field(default="", max_length=200)
    category: str = Field(default="", max_length=80)
    member_overrides: dict[str, list[FactInput]] = Field(default_factory=dict, max_length=30)
    people: list[FictionalPerson] = Field(default_factory=list, max_length=10)
    excluded_subject_keys: list[str] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def scoped_facts(self):
        from opportunity_platform.scenarios.service import (
            BUSINESS_KEYS,
            HOUSEHOLD_KEYS,
            PERSON_KEYS,
        )

        permitted = {"person": PERSON_KEYS, "household": HOUSEHOLD_KEYS, "business": BUSINESS_KEYS}
        if (self.people or self.excluded_subject_keys) and not self.scenario:
            raise ValueError("Family composition changes require an explicit hypothetical scenario")
        if self.people and (
            self.subject.kind == "business" or len({p.key for p in self.people}) != len(self.people)
        ):
            raise ValueError("Use unique fictional people in a personal or family scenario")
        if any(f.key not in PERSON_KEYS for p in self.people for f in p.facts):
            raise ValueError("Fictional people use person facts, never verified evidence")
        if any(f.key not in permitted[self.subject.kind] for f in self.overrides):
            raise ValueError("Use scenario facts appropriate to the selected subject")
        for values in self.member_overrides.values():
            if (
                len(values) > 30
                or len({f.key for f in values}) != len(values)
                or any(f.key not in PERSON_KEYS for f in values)
            ):
                raise ValueError("Use distinct supported person facts for family scenarios")
        return self

    @field_validator("overrides")
    @classmethod
    def safe_overrides(cls, values):
        keys = [value.key for value in values]
        if len(keys) != len(set(keys)):
            raise ValueError("Scenario facts must have distinct keys")
        return values


class GuidanceItem(BaseModel):
    listing: ResearchCard
    geography_signal: Literal[
        "saved_domicile",
        "saved_business_registration",
        "saved_residence",
        "national_scope",
        "needs_location_check",
    ]
    reason: str
    next_steps: list[str]
    eligibility_verified: Literal[False] = False
    subject_id: str = ""
    subject_name: str = "Selected subject"
    subject_kind: str = "person"
    fictional: bool = False
    parent_key: str = ""
    components: list[ResearchCard] = []
    conditions: list[Comparison] = []


class GuidanceResponse(BaseModel):
    items: list[GuidanceItem]
    eligible_count: Literal[0] = 0
    candidate_count: int
    hypothetical: bool
    neural_status: str = "not_requested"
    actions: list[ActionView] = []
    supported_pair_count: int = 0
    notice: str = (
        "Provisional source-backed comparisons, not reviewed eligibility. Current "
        "applications, funding and deadlines have NOT been verified."
    )


def normalized_state(value):
    text = value.strip().casefold() if isinstance(value, str) else ""
    return {"राजस्थान": "rajasthan", "कर्नाटक": "karnataka", "दौसा": "dausa", "भारत": "india"}.get(
        text, text
    )


def location_signals(jurisdiction: str, facts: list[FactRecord], kind: str):
    """Return geographically useful discovery signals, never an eligibility verdict."""
    today = date.today()
    current = [
        f
        for f in facts
        if (f.valid_from is None or f.valid_from <= today)
        and (f.valid_until is None or f.valid_until >= today)
    ]
    # Conflicting current locations remain unknown; never let row order decide.
    grouped = {
        key: {normalized_state(f.value) for f in current if f.key == key} for key in LOCATION_KEYS
    }
    usable = {key: next(iter(values)) for key, values in grouped.items() if len(values) == 1}
    target = normalized_state(jurisdiction)
    if target in {"india", "in", "national", "all india"}:
        return 2, "national_scope", "This opportunity has a national geographic scope."
    domicile = normalized_state(usable.get("domicile_state")) if kind != "business" else ""
    registered = (
        normalized_state(usable.get("business_registration_state")) if kind == "business" else ""
    )
    residence = normalized_state(usable.get("residence_state"))
    if target and (target == domicile or target == registered):
        return (
            4,
            "saved_business_registration" if kind == "business" else "saved_domicile",
            "Location is consistent with saved domicile or business registration.",
        )
    if target and target == residence:
        return (
            3,
            "saved_residence",
            "Location matches saved residence; other rules still need checking.",
        )
    if not domicile and not registered and not residence:
        return (
            1,
            "needs_location_check",
            "Your location information is not yet available.",
        )
    return (
        0,
        "needs_location_check",
        "Programme concerns another jurisdiction; check the official geographic rules.",
    )


def with_overrides(facts: list[FactRecord], updates: list[FactInput]):
    # Never combine a saved fact with a hypothetical alternative to form a false match.
    keys = [f.key for f in updates]
    if len(keys) != len(set(keys)):
        raise ValueError("Scenario facts must have distinct keys")
    existing = [f for f in facts if f.key not in keys]
    return existing + [
        FactRecord(
            id="research-hypothesis",
            key=f.key,
            value=f.value,
            valid_from=f.valid_from,
            valid_until=f.valid_until,
            context={"income_period": f.income_period, "income_definition": f.income_definition},
        )
        for f in updates
    ]


def guidance(
    session: Session, uid: str, request: GuidanceRequest, *, exclude_parents=()
) -> GuidanceResponse:
    _, obj, _ = resolve(session, uid, request.subject, read_only=True)
    subjects = [(request.subject.kind, obj)]
    if request.subject.kind == "household":
        from opportunity_platform.subjects.service import view

        for member in view(session, uid, request.subject, read_only=True).members:
            if member.get("access") == "authorized":
                _, person, _ = resolve(session, uid, SubjectRef(id=member["id"]), read_only=True)
                subjects.append(("person", person))
    allowed = {f"{kind}:{person.id}" for kind, person in subjects}
    if set(request.excluded_subject_keys) - allowed:
        from opportunity_platform.core.errors import APIError

        raise APIError(
            404, "subject_not_found", "Only selected authorized subjects may be excluded."
        )
    if set(request.member_overrides) - allowed or any(
        len(v) > 30 for v in request.member_overrides.values()
    ):
        from opportunity_platform.core.errors import APIError

        raise APIError(
            422,
            "invalid_scenario_subject",
            "Only selected authorized family members may be simulated.",
        )
    from .router import card

    rows = list(session.scalars(select(ResearchListing).where(ResearchListing.is_public.is_(True))))
    from .search import rank

    scores, neural_status = rank(rows, request.q)
    matches = []
    grouped = {}
    subjects = [
        (kind, person)
        for kind, person in subjects
        if f"{kind}:{person.id}" not in request.excluded_subject_keys
    ]
    fictional = {uuid.uuid5(obj.id, "research-scenario:" + p.key): p for p in request.people}
    subjects += [
        ("person", SimpleNamespace(id=identifier, display_name="Hypothetical · " + p.name))
        for identifier, p in fictional.items()
    ]
    for kind, person in subjects:
        if kind == "household":
            # Current research mappings concern people or enterprises. A household
            # is a permission scope, never a substitute applicant for its members.
            continue
        baseline = [] if person.id in fictional else subject_facts(session, kind, person.id)
        updates = (
            request.overrides
            if person.id == obj.id
            else request.member_overrides.get(f"{kind}:{person.id}", [])
        )
        facts = with_overrides(baseline, updates)
        if person.id in fictional:
            facts = with_overrides([], fictional[person.id].facts)
        for row in rows:
            item = card(row)
            if parent_key(item.key) in exclude_parents:
                continue
            if (
                item.archive
                or (request.category and item.category != request.category)
                or (request.q.strip() and str(item.id) not in scores)
            ):
                continue
            # Subject *kind* is known and authorized. It is not an eligibility rule:
            # simply don't show individual scholarships as business prospects or
            # procurement tenders as personal benefits.
            if (
                (kind == "business" and item.category not in {"business", "procurement"})
                or (kind == "household" and item.category in {"business", "procurement"})
                or (kind == "person" and item.category in {"business", "procurement"})
            ):
                continue
            location_rank, signal, reason = location_signals(item.jurisdiction, facts, kind)
            # An actual geographic mismatch is not an automatic rejection; put it in
            # the public Explore catalogue instead of calling the person ineligible.
            if location_rank == 0:
                continue
            conditions = compare(session, row, facts, baseline)
            parent = parent_key(item.key)
            identity = (str(person.id), parent)
            if identity in grouped:
                grouped[identity].components.append(item)
                continue
            source_rank = {
                "substantive_document": 0,
                "source_overview": 1,
                "charter_summary": 2,
                "directory_reference": 3,
            }.get(quality(row).get("evidence_strength"), 4)
            steps = [
                "Check eligibility and exceptions in the cited official document.",
                "Confirm a currently available application round with the issuing authority.",
            ]
            if not item.apply_url:
                steps.append(
                    "Find the official application route; none is established in this record."
                )
            entry = GuidanceItem(
                listing=item,
                geography_signal=signal,
                reason=reason,
                next_steps=steps,
                conditions=conditions,
                parent_key=parent,
                subject_id=str(person.id),
                subject_kind=kind,
                fictional=person.id in fictional,
                subject_name=getattr(
                    person, "display_name", getattr(person, "name", "Selected subject")
                ),
            )
            grouped[identity] = entry
            mismatch = any(c.result.outcome == "unsatisfied" for c in conditions)
            satisfied = sum(c.result.outcome == "satisfied" for c in conditions)
            matches.append(
                (
                    (
                        not bool(conditions),
                        mismatch,
                        -scores.get(str(item.id), 0),
                        -satisfied,
                        -location_rank,
                        source_rank,
                        item.title.casefold(),
                        str(person.id),
                    ),
                    entry,
                )
            )
    matches.sort(key=lambda entry: entry[0])
    return GuidanceResponse(
        items=[entry[1] for entry in matches[request.offset : request.offset + request.limit]],
        candidate_count=len(matches),
        hypothetical=request.scenario or bool(request.overrides) or bool(request.member_overrides),
        neural_status=neural_status,
        supported_pair_count=sum(bool(entry[1].conditions) for entry in matches),
    )
