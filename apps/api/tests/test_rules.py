from datetime import date

import pytest
from pydantic import ValidationError

from opportunity_platform.eligibility.engine import FactRecord, blocker, evaluate
from opportunity_platform.eligibility.rules import Condition, FactInput, Rule

TODAY = date(2026, 10, 13)


def leaf(fact, op, value=None, **kw):
    return Rule(op="condition", condition=Condition(fact=fact, op=op, value=value, **kw))


def fact(key, value, **kw):
    return FactRecord(id="synthetic-fact", key=key, value=value, **kw)


def test_three_values_nested_boolean_logic():
    age = leaf("age", "gte", 18)
    assert evaluate(age, [fact("age", 20)], TODAY).outcome == "satisfied"
    assert evaluate(age, [fact("age", 16)], TODAY).outcome == "unsatisfied"
    assert evaluate(age, [], TODAY).outcome == "unknown"
    tree = Rule(
        op="all",
        children=[
            age,
            Rule(
                op="any",
                children=[
                    leaf("student_status", "eq", True),
                    leaf("employment_status", "eq", "employed"),
                ],
            ),
        ],
    )
    assert (
        evaluate(tree, [fact("age", 20), fact("student_status", True)], TODAY).outcome
        == "satisfied"
    )
    assert evaluate(tree, [fact("age", 20)], TODAY).outcome == "unknown"
    assert evaluate(tree, [fact("age", 16)], TODAY).outcome == "unsatisfied"
    assert (
        evaluate(
            Rule(op="any", children=[age, leaf("student_status", "eq", True)]),
            [fact("age", 20)],
            TODAY,
        ).blockers
        == []
    )


def test_conflicts_stale_future_and_inference_are_unknown():
    rule = leaf("age", "gte", 18)
    assert evaluate(rule, [fact("age", 20), fact("age", 16)], TODAY).outcome == "unknown"
    assert (
        evaluate(rule, [fact("age", 20, valid_until=date(2025, 1, 1))], TODAY).outcome == "unknown"
    )
    assert (
        evaluate(rule, [fact("age", 20, valid_from=date(2027, 1, 1))], TODAY).outcome == "unknown"
    )
    assert evaluate(rule, [fact("age", 20, origin="ai_inference")], TODAY).outcome == "unknown"
    historical = leaf("age", "gte", 18, as_of=date(2025, 1, 1))
    assert (
        evaluate(
            historical,
            [fact("age", 20, valid_from=date(2024, 1, 1), valid_until=date(2025, 2, 1))],
            TODAY,
        ).outcome
        == "satisfied"
    )


def test_documents_are_gaps_not_disqualifiers():
    rule = leaf("has_income_certificate", "document")
    for records in [
        [],
        [fact("has_income_certificate", False)],
        [fact("has_income_certificate", True)],
    ]:
        result = evaluate(rule, records, TODAY)
        assert result.outcome == "unknown" and result.kind == "evidence_gap"
    assert (
        evaluate(
            rule,
            [
                fact(
                    "has_income_certificate",
                    True,
                    origin="verified_document",
                    verification="verified",
                )
            ],
            TODAY,
        ).outcome
        == "satisfied"
    )
    assert (
        evaluate(
            Rule(op="all", children=[leaf("age", "gte", 18), rule]),
            [
                fact("age", 16),
                fact(
                    "has_income_certificate",
                    True,
                    origin="verified_document",
                    verification="verified",
                ),
            ],
            TODAY,
        ).outcome
        == "unsatisfied"
    )


def test_geography_income_definition_and_shared_blocker():
    domicile = leaf("domicile_state", "eq", "Rajasthan")
    residence = leaf("residence_district", "eq", "Dausa")
    national = leaf("nationality", "eq", "IN")
    records = [
        fact("domicile_state", "Rajasthan"),
        fact("residence_district", "Jaipur"),
        fact("nationality", "IN"),
    ]
    assert evaluate(domicile, records, TODAY).outcome == "satisfied"
    assert evaluate(residence, records, TODAY).outcome == "unsatisfied"
    assert evaluate(national, records, TODAY).outcome == "satisfied"
    income = leaf(
        "annual_parental_income",
        "lte",
        250000,
        income_period="annual",
        income_definition="parents_all_sources",
    )
    assert evaluate(income, [fact("annual_personal_income", 200000)], TODAY).outcome == "unknown"
    assert (
        evaluate(
            income,
            [
                fact(
                    "annual_parental_income",
                    200000,
                    context={
                        "income_period": "2025-26",
                        "income_definition": "household_all_members",
                    },
                )
            ],
            TODAY,
        ).outcome
        == "unknown"
    )
    assert (
        evaluate(
            income,
            [
                fact(
                    "annual_parental_income",
                    200000,
                    context={"income_period": "annual", "income_definition": "parents_all_sources"},
                )
            ],
            TODAY,
        ).outcome
        == "satisfied"
    )
    assert blocker(income) == blocker(Rule.model_validate(income.model_dump()))


@pytest.mark.parametrize(
    "data",
    [
        {"op": "python", "expression": "__import__('os')"},
        {"op": "all", "children": []},
        {"op": "condition", "condition": {"op": "eq", "fact": "aadhaar", "value": "secret"}},
        {
            "op": "condition",
            "condition": {"op": "lte", "fact": "annual_parental_income", "value": 300000},
        },
    ],
)
def test_rule_language_rejects_untrusted_or_ambiguous_input(data):
    with pytest.raises(ValidationError):
        Rule.model_validate(data)


def test_profile_input_rejects_type_spoofing():
    with pytest.raises(ValidationError):
        FactInput(key="age", value=True)
    with pytest.raises(ValidationError):
        FactInput(key="disability_percentage", value=101)
    assert FactInput(key="annual_parental_income", value=None).value is None


@pytest.mark.parametrize(
    "condition",
    [
        {"op": "eq", "fact": "age", "value": True},
        {"op": "eq", "fact": "has_income_certificate", "value": True},
        {"op": "eq", "fact": "age", "value": None},
        {"op": "in", "fact": "nationality", "value": []},
        {"op": "gte", "fact": "residence_state", "value": 5},
        {"op": "gte", "fact": "age", "value": float("inf")},
    ],
)
def test_invalid_comparisons_are_not_publishable_rules(condition):
    with pytest.raises(ValueError):
        Condition.model_validate(condition)
