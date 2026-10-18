"""Source-backed ranking and scenario totals, with fictional people/local PostgreSQL only."""

import pytest
from sqlalchemy import select
from test_research_completion import OWNER, auth, request
from test_research_guidance import real_guidance as original_guidance

from opportunity_platform.db.models import ResearchListing
from opportunity_platform.eligibility.rules import FactInput
from opportunity_platform.profiles.service import ProfileWrite, save_profile


@pytest.fixture
def real_guidance(client, db):
    return original_guidance.__wrapped__(client, db)


def profile(db, *, age=22, student=True):
    save_profile(
        db,
        OWNER,
        ProfileWrite(
            display_name="Fictional ranking test",
            facts=[
                FactInput(key="domicile_state", value="Rajasthan"),
                FactInput(key="student_status", value=student),
                FactInput(key="highest_completed_education", value="X"),
                *([FactInput(key="age", value=age)] if age is not None else []),
            ],
        ),
    )
    db.commit()


def pages(client, **kwargs):
    first = request(client, limit=7, **kwargs)
    items = list(first["items"])
    for offset in range(7, first["candidate_count"], 7):
        items += request(client, limit=7, offset=offset, **kwargs)["items"]
    return first, items


def test_age_22_pension_is_after_scholarships_and_unknowns_without_pagination_loss(real_guidance):
    client, db = real_guidance
    auth()
    profile(db)
    data, items = pages(client)
    pension = next(i for i in items if i["parent_key"] == "rajasthan-pension-national-old-age")
    scholarship = next(i for i in items if i["parent_key"] == "post-matric-st")
    assert pension["relevance_group"] == "known_mismatch"
    assert scholarship["relevance_group"] == "promising"
    assert items.index(scholarship) < items.index(pension)
    groups = {"promising": 0, "information_gaps": 1, "known_mismatch": 2}
    order = [groups[i["relevance_group"]] for i in items]
    assert order == sorted(order)
    identities = {(i["subject_id"], i["parent_key"]) for i in items}
    assert len(identities) == len(items) == data["candidate_count"]
    assert sum(data["relevance_counts"].values()) == len(items)
    assert data["neural_status"].startswith(("unavailable", "local_cpu:"))
    assert all(not i["eligibility_verified"] for i in items)


def test_unknown_age_stays_information_gap_not_known_pension_mismatch(real_guidance):
    client, db = real_guidance
    auth()
    profile(db, age=None, student=False)
    _, items = pages(client)
    pension = next(i for i in items if i["parent_key"] == "rajasthan-pension-national-old-age")
    age = next(
        c for c in pension["conditions"] if c["rule"].get("condition", {}).get("fact") == "age"
    )
    assert age["result"]["outcome"] == "unknown"
    assert pension["relevance_group"] == "information_gaps"


def test_semantic_score_cannot_promote_known_mismatch_above_scholarship(real_guidance, monkeypatch):
    from opportunity_platform.research import search

    client, db = real_guidance
    auth()
    profile(db)
    rows = {r.identity_key: r for r in db.scalars(select(ResearchListing))}
    monkeypatch.setattr(
        search,
        "rank",
        lambda rows_, query: (
            {
                str(rows["rajasthan-pension-national-old-age"].id): 1000,
                str(rows["post-matric-st"].id): 0.01,
            },
            "mocked-semantic-results",
        ),
    )
    data = request(client, q="fictional mixed search")
    assert [i["parent_key"] for i in data["items"]] == [
        "post-matric-st",
        "rajasthan-pension-national-old-age",
    ]


def test_provisional_scenario_totals_cover_all_pages_without_approved_assessments(real_guidance):
    client, db = real_guidance
    auth()
    profile(db, student=False)
    body = {"scenario": True, "overrides": [{"key": "student_status", "value": True}]}
    first, items = pages(client, **body)
    one = request(client, limit=1, **body)
    assert one["research_changes"] == first["research_changes"]
    unique = {
        (
            i["subject_id"],
            i["parent_key"],
            c["semantic"],
            c["source_hash"],
            c["page"],
            str(c["rule"]),
        ): c
        for i in items
        for c in i["conditions"]
    }
    summary = one["research_changes"]
    assert summary["changed_conditions"] == sum(c["changed"] for c in unique.values()) > 0
    assert summary["total_conditions"] == len(unique)
    assert (
        summary["total_conditions"]
        == summary["changed_conditions"] + summary["unchanged_conditions"]
    )
    assert summary["changed_programme_subject_pairs"] == sum(
        any(c["changed"] for c in i["conditions"]) for i in items
    )
    assert one["reviewed"]["catalogue_count"] == 0
    assert one["reviewed"]["items"] == [] and one["eligible_count"] == 0


def test_empty_query_without_profile_context_does_not_invoke_neural_retrieval(monkeypatch):
    from opportunity_platform.research import search

    def forbidden():
        raise AssertionError("Unknown profile must not invent a semantic query")

    monkeypatch.setattr(search, "neural_retriever", forbidden)
    assert search.rank([], "  ") == ({}, "not_requested: no usable profile context")


def test_repeated_condition_mapping_counts_once_per_programme_subject():
    from types import SimpleNamespace

    from opportunity_platform.eligibility.rules import Rule
    from opportunity_platform.research.guidance import summarize_changes

    condition = SimpleNamespace(
        semantic="fictional-minimum-age",
        source_hash="a" * 64,
        page=1,
        rule=Rule.model_validate(
            {"op": "condition", "condition": {"op": "gte", "fact": "age", "value": 60}}
        ),
        changed=True,
        result=SimpleNamespace(outcome="satisfied"),
    )
    one_subject = SimpleNamespace(conditions=[condition, condition])
    summary = summarize_changes([one_subject])
    assert summary.total_conditions == summary.changed_conditions == 1
    assert summary.changed_programme_subject_pairs == 1
    family = summarize_changes([one_subject, SimpleNamespace(conditions=[condition])])
    assert family.changed_conditions == 2 and family.changed_programme_subject_pairs == 2
