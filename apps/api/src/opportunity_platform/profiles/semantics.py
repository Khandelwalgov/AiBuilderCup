"""Shared deterministic meaning rules; generated JSON is also used by the web editor."""

import json
from datetime import date
from pathlib import Path

from opportunity_platform.core.errors import APIError

SPEC = json.loads(Path(__file__).with_name("semantics.json").read_text())


def active(fact, today):
    return (not fact.valid_from or fact.valid_from <= today) and (
        not fact.valid_until or fact.valid_until >= today
    )


def signature(fact):
    return fact.value, fact.valid_from, fact.valid_until


def issues(facts, before=(), today=None):
    today = today or date.today()
    current = {f.key: f for f in facts if active(f, today)}
    old = {f.key: f for f in before}
    found = []
    for rule in SPEC["rules"]:

        def matches(test):
            value = current[test["key"]].value if test["key"] in current else None
            return (
                (not test.get("known") or value is not None)
                and ("eq" not in test or value == test["eq"])
                and ("one_of" not in test or value in test["one_of"])
            )

        if not all(matches(test) for test in rule["when"]):
            continue
        retained = all(
            key in old and key in current and signature(old[key]) == signature(current[key])
            for key in rule["fields"]
        )
        found.append(
            {
                **rule,
                "severity": "warning" if retained else rule["severity"],
                "values": {key: current[key].value for key in rule["fields"] if key in current},
                "same_active_period": True,
                "retained": retained,
            }
        )
    return found


def validate(facts, before=()):
    errors = [issue for issue in issues(facts, before) if issue["severity"] == "error"]
    if errors:
        raise APIError(422, "semantic_conflict", errors[0]["message"][0], issues=errors)


def validate_person(facts, before=()):
    prior = {f.key: f for f in before}
    wrong = [
        f.key
        for f in facts
        if f.key.startswith("business_")
        and (f.key not in prior or signature(f) != signature(prior[f.key]))
    ]
    if wrong:
        raise APIError(
            422,
            "subject_fact_mismatch",
            "Business facts belong in an authorized business profile. "
            "Your personal answers are preserved.",
            issues=[{"fields": wrong}],
        )
    validate(facts, before)
