import hashlib
import json
from datetime import date
from typing import Literal

from pydantic import BaseModel

from opportunity_platform.eligibility.rules import Rule


class FactRecord(BaseModel):
    id: str
    key: str
    value: str | int | float | bool | None
    origin: str = "user_supplied"
    verification: str = "unverified"
    valid_from: date | None = None
    valid_until: date | None = None
    context: dict = {}


class Result(BaseModel):
    outcome: Literal["satisfied", "unsatisfied", "unknown"]
    reason: str
    facts: list[FactRecord] = []
    missing: list[str] = []
    blockers: list[str] = []
    kind: Literal["condition", "evidence_gap"] = "condition"
    children: list["Result"] = []


def blocker(rule: Rule) -> str:
    return (
        "requirement:"
        + hashlib.sha256(
            json.dumps(rule.model_dump(mode="json"), sort_keys=True).encode()
        ).hexdigest()[:20]
    )


def evaluate(rule: Rule, facts: list[FactRecord], today: date) -> Result:
    if rule.op in {"all", "any"}:
        children = [evaluate(child, facts, today) for child in rule.children]
        outcomes = [child.outcome for child in children]
        if rule.op == "all":
            outcome = (
                "unsatisfied"
                if "unsatisfied" in outcomes
                else "unknown"
                if "unknown" in outcomes
                else "satisfied"
            )
        else:
            outcome = (
                "satisfied"
                if "satisfied" in outcomes
                else "unknown"
                if "unknown" in outcomes
                else "unsatisfied"
            )
        unresolved = (
            [child for child in children if child.outcome != "satisfied"]
            if outcome != "satisfied"
            else []
        )
        return Result(
            outcome=outcome,
            reason="All conditions are required."
            if rule.op == "all"
            else "At least one condition is required.",
            facts=[f for child in children for f in child.facts],
            missing=sorted({key for child in unresolved for key in child.missing}),
            blockers=sorted({key for child in unresolved for key in child.blockers}),
            kind="evidence_gap"
            if unresolved and all(child.kind == "evidence_gap" for child in unresolved)
            else "condition",
            children=children,
        )
    c = rule.condition
    identity = blocker(rule)
    if c.op == "unknown":
        return Result(
            outcome="unknown",
            reason="The source condition cannot yet be evaluated. Human clarification is required.",
            blockers=[identity],
        )
    when = c.as_of or today
    records = [
        f
        for f in facts
        if f.key == c.fact
        and (f.valid_from is None or f.valid_from <= when)
        and (f.valid_until is None or f.valid_until >= when)
    ]
    known = [f for f in records if f.value is not None and f.origin != "ai_inference"]

    def unknown(reason, kind="condition"):
        return Result(
            outcome="unknown",
            reason=reason,
            facts=records,
            missing=[c.fact],
            blockers=[identity],
            kind=kind,
        )

    if c.op == "document":
        verified = [
            f
            for f in known
            if f.value is True and f.origin == "verified_document" and f.verification == "verified"
        ]
        contradictory = [
            f
            for f in known
            if f.origin == "verified_document" and f.verification == "verified" and f.value is False
        ]
        if verified and contradictory:
            return unknown("Conflicting verified evidence requires clarification.", "evidence_gap")
        if not verified:
            return unknown(
                (
                    "Verified documentary evidence is missing. This is an evidence gap, not a "
                    "finding of ineligibility."
                ),
                "evidence_gap",
            )
        return Result(
            outcome="satisfied",
            reason="Verified documentary evidence is available.",
            facts=verified,
        )
    if not known:
        return unknown("No applicable known fact is available for this condition.")
    if len({json.dumps(f.value, sort_keys=True) for f in known}) != 1:
        return unknown(
            "Conflicting facts require clarification; no value has been chosen automatically."
        )
    if c.fact in {"annual_personal_income", "annual_parental_income", "business_turnover"} and any(
        f.context.get("income_period") != c.income_period
        or f.context.get("income_definition") != c.income_definition
        for f in known
    ):
        return unknown(
            (
                "Income period or definition does not match this requirement. Clarify the "
                "scheme-specific income basis."
            )
        )
    value = known[0].value
    try:

        def same(a, b):
            if type(a) in (int, float) and type(b) in (int, float):
                return a == b
            if (
                isinstance(a, str)
                and isinstance(b, str)
                and c.fact
                in {
                    "nationality",
                    "domicile_state",
                    "domicile_district",
                    "residence_state",
                    "residence_district",
                }
            ):
                return a.strip().casefold() == b.strip().casefold()
            return type(a) is type(b) and a == b

        if c.op == "eq":
            satisfied = same(value, c.value)
        elif c.op == "in":
            satisfied = any(same(value, item) for item in c.value)
        else:
            if type(value) not in (int, float):
                return unknown("This fact has the wrong type for a numeric requirement.")
            satisfied = value >= c.value if c.op == "gte" else value <= c.value
    except (TypeError, ValueError):
        return unknown("The stored fact cannot be compared safely.")
    return Result(
        outcome="satisfied" if satisfied else "unsatisfied",
        reason=(
            "The supplied fact satisfies this condition; it is not an official "
            "eligibility decision."
        )
        if satisfied
        else "The supplied fact does not satisfy this condition.",
        facts=known,
        blockers=[] if satisfied else [identity],
    )
