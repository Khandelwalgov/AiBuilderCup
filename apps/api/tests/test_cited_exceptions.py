"""Source-bound exceptions, income ownership and evidence fail-closed regressions."""

from datetime import date

import pytest
from sqlalchemy import select
from test_research_guidance import real_guidance as original_guidance

from opportunity_platform.db.models import ResearchListing
from opportunity_platform.eligibility.engine import FactRecord, evaluate
from opportunity_platform.eligibility.rules import Rule
from opportunity_platform.research.conditions import compare, definitions


@pytest.fixture
def real_guidance(client, db):
    return original_guidance.__wrapped__(client, db)


def record(key, value, **context):
    return FactRecord(id=key, key=key, value=value, context=context)


def clause(semantic, key=None):
    return next(
        c
        for c in definitions()
        if c["semantic"] == semantic and (not key or c["listing_key"] == key)
    )


def run(c, facts):
    return evaluate(Rule.model_validate(c["rule"]), facts, date(2026, 10, 18))


def test_st_income_exception_and_actual_admission_period():
    c = clause("st_parental_income")
    assert run(c, [record("orphan_supported_by_guardian", True)]).outcome == "satisfied"
    facts = [
        record("orphan_supported_by_guardian", False),
        record("parental_income_salary_basis", True),
    ]
    income = c["rule"]["children"][1]["children"][1]["condition"]
    amount = record(
        "annual_parental_income",
        200000,
        income_period="2025-26",
        income_definition=income["income_definition"],
    )
    assert run(c, facts + [amount]).outcome == "unknown"
    assert "education_admission_year" in run(c, facts + [amount]).missing
    facts.append(record("education_admission_year", "2026-27"))
    assert run(c, facts + [amount]).outcome == "satisfied"
    # Neither a current-year number nor arbitrary "family income" has the cited ownership/period.
    assert (
        run(
            c,
            facts
            + [
                record(
                    "annual_parental_income",
                    200000,
                    income_period="2026-27",
                    income_definition=income["income_definition"],
                )
            ],
        ).outcome
        == "unknown"
    )
    assert (
        run(
            c,
            facts
            + [
                record(
                    "annual_parental_income",
                    200000,
                    income_period="2025-26",
                    income_definition="all household members",
                )
            ],
        ).outcome
        == "unknown"
    )
    assert run(c, facts + [amount.model_copy(update={"value": 250001})]).outcome == "unsatisfied"
    assert (
        run(
            c,
            [
                record("parental_income_salary_basis", False),
                record("orphan_supported_by_guardian", False),
                amount,
            ],
        ).outcome
        == "unknown"
    )


def test_source_specific_alternatives_and_conflicting_awards():
    c = clause("odr_registration")
    assert run(c, [record("business_udyam_registered", False)]).outcome == "unknown"
    assert (
        run(
            c,
            [
                record("business_udyam_registered", False),
                record("business_udyam_assist_registered", True),
            ],
        ).outcome
        == "satisfied"
    )
    assert (
        run(
            c,
            [
                record("business_udyam_registered", False),
                record("business_udyam_assist_registered", False),
            ],
        ).outcome
        == "unsatisfied"
    )
    gst = clause("team_gst_trade_scope")
    assert (
        run(
            gst,
            [
                record("business_gst_registered", False),
                record("business_online_trade_scope", "intra_state"),
            ],
        ).outcome
        == "satisfied"
    )
    assert (
        run(
            gst,
            [
                record("business_gst_registered", False),
                record("business_online_trade_scope", "inter_state"),
            ],
        ).outcome
        == "unsatisfied"
    )
    awards = clause("scholarship_overlap", "pm-yasasvi-post-matric")
    assert (
        run(
            awards,
            [
                record("receives_other_scholarship", False),
                record("other_support_only_incidental", True),
            ],
        ).outcome
        == "satisfied"
    )
    assert (
        run(
            awards,
            [
                record("receives_other_scholarship", True),
                record("other_support_only_incidental", True),
            ],
        ).outcome
        == "unknown"
    )


@pytest.mark.parametrize(
    "op,boundary,expected",
    [
        ("lt", 18, "unsatisfied"),
        ("lt", 17, "satisfied"),
        ("gt", 18, "unsatisfied"),
        ("gt", 19, "satisfied"),
    ],
)
def test_strict_numeric_boundaries(op, boundary, expected):
    r = Rule.model_validate(
        {"op": "condition", "condition": {"op": op, "fact": "age", "value": 18}}
    )
    assert evaluate(r, [record("age", boundary)], date.today()).outcome == expected


def test_details_expose_public_evidence_without_private_evaluation(real_guidance):
    client, db = real_guidance
    row = db.scalar(select(ResearchListing).where(ResearchListing.identity_key == "post-matric-st"))
    response = client.get("/v1/research-opportunities/" + str(row.id))
    assert response.status_code == 200
    conditions = response.json()["provisional_conditions"]
    assert conditions and all(c["evidence_available"] for c in conditions)
    assert not any({"result", "baseline", "facts"} & c.keys() for c in conditions)
    # URL and snapshot identity must match as well as content hash.
    payload = {
        **row.payload,
        "sources": [
            {**s, "source_url": "https://example.gov.in/different.pdf"}
            for s in row.payload["sources"]
        ],
    }
    row.payload = payload
    assert all(
        not c.evidence_available and c.result.outcome == "unknown" for c in compare(db, row, [], [])
    )


def test_current_institution_facts_require_current_study():
    r = Rule.model_validate(
        {
            "op": "condition",
            "condition": {"op": "eq", "fact": "institution_recognized", "value": True},
        }
    )
    assert evaluate(r, [record("institution_recognized", True)], date.today()).outcome == "unknown"
    assert (
        evaluate(
            r,
            [record("institution_recognized", True), record("student_status", False)],
            date.today(),
        ).outcome
        == "unsatisfied"
    )


def test_sc_does_not_inherit_st_orphan_exemption_and_age_interval():
    sc = clause("sc_parental_income")
    assert run(sc, [record("orphan_supported_by_guardian", True)]).outcome == "unknown"
    age = clause("disability_self_employment_age")
    for years, expected in [
        (17, "unsatisfied"),
        (18, "satisfied"),
        (55, "satisfied"),
        (56, "unsatisfied"),
    ]:
        assert run(age, [record("age", years)]).outcome == expected


def test_visual_transcription_requires_the_preserved_render_hash(real_guidance, monkeypatch):
    from opportunity_platform.research import conditions

    _, db = real_guidance
    row = db.scalar(
        select(ResearchListing).where(
            ResearchListing.identity_key == "rajasthan-disability-self-employment"
        )
    )
    comparisons = compare(db, row, [record("age", 22)], [])
    age = next(c for c in comparisons if c.semantic == "disability_self_employment_age")
    assert age.evidence_available and age.result.outcome == "satisfied"
    original_pages = conditions.integrated_pages
    monkeypatch.setattr(
        conditions,
        "integrated_pages",
        lambda snapshot: [{**p, "image_sha256": "f" * 64} for p in original_pages(snapshot)],
    )
    age = next(
        c
        for c in compare(db, row, [record("age", 22)], [])
        if c.semantic == "disability_self_employment_age"
    )
    assert not age.evidence_available and age.result.outcome == "unknown"


def test_another_qualification_is_not_assumed_below_matric():
    c = clause("highest_completed_education", "post-matric-sc")
    assert run(c, [record("highest_completed_education", "other")]).outcome == "unknown"
    assert run(c, [record("highest_completed_education", "IX")]).outcome == "unsatisfied"
