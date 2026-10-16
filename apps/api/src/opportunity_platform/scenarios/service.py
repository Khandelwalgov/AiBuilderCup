"""Ephemeral subject graphs. No ORM objects are changed or created here."""

import hashlib
import json
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from opportunity_platform.core.errors import APIError
from opportunity_platform.eligibility.engine import FactRecord
from opportunity_platform.eligibility.rules import FactInput
from opportunity_platform.planning.service import ActionView, PlanView, identities
from opportunity_platform.retrieval.service import (
    SearchRequest,
    SearchResponse,
    SearchSubject,
    authorized_subjects,
    search,
)
from opportunity_platform.subjects.service import SubjectRef


class Override(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_key: str = Field(max_length=100)
    facts: list[FactInput] = Field(default_factory=list, max_length=30)


class FictionalPerson(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,30}$")
    name: str = Field(min_length=1, max_length=60)
    relationship: Literal["spouse", "child", "dependent"]
    facts: list[FactInput] = Field(default_factory=list, max_length=30)


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base: SearchRequest
    overrides: list[Override] = Field(default_factory=list, max_length=30)
    people: list[FictionalPerson] = Field(default_factory=list, max_length=10)
    excluded_subject_keys: list[str] = Field(default_factory=list, max_length=30)
    household_facts: list[FactInput] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def shape(self):
        if self.base.mode == "explore":
            raise ValueError("Select an actual authorized base context")
        if self.people and self.base.mode == "business":
            raise ValueError("Use a person or family base for fictional people")
        if len({p.key for p in self.people}) != len(self.people):
            raise ValueError("Fictional person keys must be unique")
        return self


class ScenarioResponse(BaseModel):
    actual: SearchResponse
    hypothetical: SearchResponse
    plan: PlanView
    changes: list[dict]
    graph: list[dict]
    persistence: Literal["none"] = "none"
    notice: str = (
        "Fictional relationships grant no actual access. "
        "No profiles, evidence, evaluations or actions were saved."
    )


PERSON_KEYS = {
    "age",
    "annual_personal_income",
    "annual_parental_income",
    "disability_percentage",
    "nationality",
    "domicile_state",
    "domicile_district",
    "residence_state",
    "residence_district",
    "current_education_level",
    "highest_completed_education",
    "enrollment_mode",
    "school_recognized_or_government",
    "student_status",
    "employment_status",
}
BUSINESS_KEYS = {
    "business_registered",
    "business_turnover",
    "business_registration_state",
    "business_registration_district",
    "business_operating_status",
    "residence_state",
    "residence_district",
}
HOUSEHOLD_KEYS = {
    "annual_household_income",
    "residence_state",
    "residence_district",
    "domicile_state",
    "domicile_district",
}


def apply_facts(subject, inputs, invalidate_evidence=False):
    permitted = {"person": PERSON_KEYS, "household": HOUSEHOLD_KEYS, "business": BUSINESS_KEYS}[
        subject.kind
    ]
    keys = [f.key for f in inputs]
    if len(set(keys)) != len(keys) or set(keys) - permitted:
        raise APIError(
            422,
            "invalid_scenario_facts",
            "Use distinct facts appropriate to this subject; "
            "documentary verification cannot be simulated.",
        )
    # Circumstance changes do not make old documentary facts verified for the new future.
    facts = [
        f
        for f in subject.facts
        if f.key not in keys
        and (f.origin != "verified_document" or not (inputs or invalidate_evidence))
    ]
    facts += [
        FactRecord(
            id="scenario",
            key=f.key,
            value=f.value,
            valid_from=f.valid_from,
            valid_until=f.valid_until,
            context={"income_period": f.income_period, "income_definition": f.income_definition},
        )
        for f in inputs
    ]
    if subject.kind == "person":
        from opportunity_platform.profiles.semantics import validate_person

        validate_person(facts, subject.facts)
    return SearchSubject(subject.key, subject.kind, subject.name, subject.id, facts, True)


def make_plan(response, ref):
    actions, blockers, evaluations = {}, [], []
    for item in response.items:
        for a in item.assessments:
            evaluations.append(a.evaluation)
            for r in a.evaluation.requirements:
                if r.result.outcome == "unsatisfied":
                    blockers.append(
                        {
                            "opportunity_id": str(item.opportunity.id),
                            "subject": a.subject_name,
                            "reason": r.result.reason,
                        }
                    )
                if r.result.outcome != "unknown":
                    continue
                dependencies = identities(r) or [
                    ({"requirement": str(r.requirement_id), "kind": "clarification"}, r.requirement)
                ]
                for payload, label in dependencies:
                    identity = hashlib.sha256(
                        json.dumps([a.subject_key, payload], sort_keys=True).encode()
                    ).hexdigest()
                    if identity not in actions:
                        actions[identity] = ActionView(
                            id=uuid.uuid5(uuid.NAMESPACE_URL, identity),
                            title=f"{a.subject_name}: {label}",
                            status="pending",
                            identity=identity,
                            kind=payload.get("kind", "information"),
                            fact=payload.get("fact"),
                            opportunities=[],
                            explanation=(
                                "Hypothetical next step; clarify the cited requirement. "
                                "This does not verify evidence."
                            ),
                        )
                    target = {"id": str(item.opportunity.id), "title": item.opportunity.title}
                    if target not in actions[identity].opportunities:
                        actions[identity].opportunities.append(target)
    return PlanView(
        subject=ref,
        hypothetical=True,
        evaluations=evaluations,
        actions=sorted(actions.values(), key=lambda a: (-len(a.opportunities), a.identity)),
        known_blockers=blockers,
        retrieval_truncated=response.truncated,
    )


def simulate(session, uid, request):
    subjects = authorized_subjects(session, uid, request.base)
    actual = search(session, uid, request.base, subjects)
    by_key = {s.key: s for s in subjects}
    specified = [o.subject_key for o in request.overrides]
    if (
        len(set(specified)) != len(specified)
        or (set(specified) | set(request.excluded_subject_keys)) - by_key.keys()
    ):
        raise APIError(404, "subject_not_found", "Only authorized base subjects can be changed.")
    for override in request.overrides:
        by_key[override.subject_key] = apply_facts(by_key[override.subject_key], override.facts)
    # Exclusion is scenario-only, not removal of a real membership.
    hypothetical = [
        apply_facts(
            s, [], bool(request.people or request.excluded_subject_keys) and s.kind == "household"
        )
        for key, s in by_key.items()
        if key not in request.excluded_subject_keys
    ]
    graph = [
        {"key": s.key, "kind": s.kind, "name": s.name, "fictional": False} for s in hypothetical
    ]
    for person in request.people:
        s = SearchSubject("scenario:person:" + person.key, "person", person.name, None, [], True)
        hypothetical.append(apply_facts(s, person.facts))
        graph.append(
            {
                "key": s.key,
                "kind": "person",
                "name": s.name,
                "fictional": True,
                "relationship": person.relationship,
            }
        )
    household = next((s for s in hypothetical if s.kind == "household"), None)
    if request.people and household is None:
        household = SearchSubject(
            "scenario:household", "household", "Hypothetical household", None, [], True
        )
        hypothetical.append(household)
        graph.append(
            {"key": household.key, "kind": "household", "name": household.name, "fictional": True}
        )
    if request.household_facts:
        if household is None:
            raise APIError(
                422, "household_required", "Choose a family base or add fictional members first."
            )
        hypothetical = [
            apply_facts(s, request.household_facts) if s.key == household.key else s
            for s in hypothetical
        ]
    # No income sums, synthetic permissions, age-derived kinship or verified documents.
    result = search(session, uid, request.base, hypothetical)

    def flatten(response):
        return {
            (str(i.opportunity.id), a.subject_key): (i, a)
            for i in response.items
            for a in i.assessments
        }

    before, after = flatten(actual), flatten(result)
    changes = []
    for key in sorted(before.keys() | after.keys()):
        old, new = before.get(key), after.get(key)
        if old is None:
            state = "newly_retrieved"
        elif new is None:
            state = "no_longer_retrieved"
        else:

            def outcomes(pair):
                return [
                    (str(r.requirement_id), r.result.outcome, r.result.missing, r.result.reason)
                    for r in pair[1].evaluation.requirements
                ]

            state = "changed" if outcomes(old) != outcomes(new) else "unchanged"
        item, a = new or old
        changes.append(
            {
                "opportunity_id": key[0],
                "subject_key": key[1],
                "title": item.opportunity.title,
                "subject_name": a.subject_name,
                "change": state,
                "before": old[1].evaluation.status if old else None,
                "after": new[1].evaluation.status if new else None,
                "reasons": new[1].reasons if new else old[1].reasons,
                "before_reasons": old[1].reasons if old else [],
            }
        )
    kind = {"me": "person", "member": "person", "family": "household", "business": "business"}[
        request.base.mode
    ]
    return ScenarioResponse(
        actual=actual,
        hypothetical=result,
        plan=make_plan(result, SubjectRef(kind=kind, id=request.base.subject_id)),
        changes=changes,
        graph=graph,
    )
