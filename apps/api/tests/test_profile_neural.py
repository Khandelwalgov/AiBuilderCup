"""Opt-in real ONNX inference plus offline privacy/coverage regressions. No providers."""

import os
import resource
import time
from datetime import date
from types import SimpleNamespace

import pytest

from opportunity_platform.eligibility.engine import FactRecord
from opportunity_platform.research import search
from opportunity_platform.retrieval import neural


def facts(**values):
    return [FactRecord(id="fictional", key=key, value=value) for key, value in values.items()]


def rows():
    # Controlled fictional semantics, not a government-policy accuracy benchmark.
    return [
        SimpleNamespace(
            id=key,
            identity_key="fictional-" + key,
            payload_hash=key,
            title=title,
            summary=summary,
            payload={"benefit": summary},
            search_text=title + " " + summary,
            category=category,
            jurisdiction="India",
        )
        for key, title, summary, category in [
            (
                "pension",
                "Old age pension",
                "Social assistance for elderly retired senior citizens.",
                "welfare",
            ),
            (
                "education",
                "University scholarships",
                "Education financial aid for undergraduate students currently studying at college.",
                "education",
            ),
            (
                "business",
                "Enterprise marketing support",
                "Marketing and online commerce support for small manufacturing businesses.",
                "business",
            ),
        ]
    ]


@pytest.fixture(scope="module")
def encoder():
    directory = os.environ.get("NEURAL_TEST_MODEL_DIRECTORY")
    if not directory:
        pytest.skip("Existing pinned local weights required; no download or API fallback")
    started = time.perf_counter()
    value = neural.encoder_for(directory)
    print(
        f"real_profile_neural model_load={time.perf_counter() - started:.3f}s "
        f"process_peak_rss={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss} "
        "platform_bytes_on_macos"
    )
    return value


@pytest.fixture
def real_model(monkeypatch, encoder):
    from opportunity_platform.core.config import settings

    monkeypatch.setattr(settings(), "neural_retrieval_enabled", True)
    monkeypatch.setattr(
        settings(), "neural_model_directory", os.environ["NEURAL_TEST_MODEL_DIRECTORY"]
    )
    assert neural.neural_retriever().encoder is encoder
    return encoder


def test_profile_context_is_current_unambiguous_scoped_and_has_no_invented_goals():
    values = facts(age=22, student_status=True, current_education_level="undergraduate")
    values += [
        FactRecord(
            id="expired", key="employment_status", value="retired", valid_until=date(2020, 1, 1)
        ),
        FactRecord(
            id="future", key="beneficiary_category", value="ST", valid_from=date(2099, 1, 1)
        ),
        FactRecord(id="private", key="display_name", value="PRIVATE NEVER ENCODE"),
        *facts(business_sector="manufacturing"),
    ]
    context = search.profile_context("person", values)
    assert "Currently studying: yes" in context.intent
    assert "Current education course: undergraduate" in context.intent
    assert "retired" not in context.intent and "PRIVATE" not in context.intent
    assert "manufacturing" not in context.intent and "ST" not in context.intent
    assert "scholarship" not in context.intent  # a goal is not inferred from enrollment
    assert search.profile_context("person", list(reversed(values))) == context
    assert search.profile_context("person", values + facts(age=60)).facts == [
        f for f in context.facts if f["key"] != "age"
    ]
    assert search.profile_context("person", facts(age=None)) is None
    assert search.profile_context("person", facts(education_level="undergraduate")) is None
    assert search.profile_context("business", values).facts == [
        {"key": "business_sector", "value": "manufacturing"}
    ]


def test_unknown_profile_skips_model_and_missing_weights_keep_coverage(monkeypatch):
    from opportunity_platform.core.config import settings

    monkeypatch.setattr(settings(), "neural_model_directory", "/nonexistent/fictional-model")
    assert search.rank(rows(), "", subject=search.profile_context("person", [])) == (
        {},
        "not_requested: no usable profile context",
    )
    scores, status = search.rank(
        rows(), "", subject=search.profile_context("person", facts(age=22))
    )
    assert not scores and status.startswith("unavailable")
    # Typed-query lexical fallback still works without weights.
    scores, status = search.rank(rows(), "scholarships")
    assert "education" in scores and status.startswith("unavailable")


def test_real_empty_query_encodes_profile_changes_rank_and_never_caches_private_text(
    real_model, monkeypatch
):
    calls = []
    original = real_model.encode

    def actual_encode(text):
        calls.append(text)
        return original(text)

    monkeypatch.setattr(real_model, "encode", actual_encode)
    student = search.profile_context(
        "person", facts(age=22, student_status=True, current_education_level="undergraduate")
    )
    start = time.perf_counter()
    first, status = search.rank(rows(), "", subject=student)
    cold_seconds = time.perf_counter() - start
    assert status.startswith("local_cpu:") and calls.count(student.intent) == 1
    assert max(first, key=first.get) == "education"
    senior = search.profile_context("person", facts(age=75, employment_status="retired"))
    second, _ = search.rank(rows(), "", subject=senior)
    assert max(second, key=second.get) == "pension"
    assert first != second and calls.count(senior.intent) == 1
    business = search.profile_context(
        "business", facts(business_sector="manufacturing", business_size="small")
    )
    third, _ = search.rank(rows(), "", subject=business)
    assert max(third, key=third.get) == "business"
    # Repeated requests encode private context again, while only public documents cache.
    before = len(calls)
    start = time.perf_counter()
    again, _ = search.rank(rows(), "", subject=student)
    warm_seconds = time.perf_counter() - start
    assert first == again and len(calls) == before + 1
    assert student.intent not in str(real_model.public_vectors)
    assert all(
        set(scores) == {"education", "pension", "business"} for scores in (first, second, third)
    )
    assert cold_seconds < 15 and warm_seconds < 2  # generous CPU regression bounds
    print(f"real_profile_neural controlled cold={cold_seconds:.3f}s warm={warm_seconds:.3f}s")


def test_real_guidance_orders_full_catalogue_per_authorized_subject(real_model, monkeypatch):
    """Exercise guidance with actual encoder, no DB: full deterministic grouping + paging."""
    import sys
    import uuid

    from test_research_guidance import research_card

    from opportunity_platform.research import guidance as module
    from opportunity_platform.research.guidance import GuidanceRequest, guidance
    from opportunity_platform.subjects import service

    catalogue = rows()
    # Give business another applicable component so both contexts have meaningful ordering.
    catalogue.append(
        SimpleNamespace(
            **{
                **catalogue[0].__dict__,
                "id": "business-other",
                "identity_key": "fictional-business-other",
                "category": "business",
            }
        )
    )
    people = [
        SimpleNamespace(id=uuid.uuid4(), display_name="Fictional student"),
        SimpleNamespace(id=uuid.uuid4(), display_name="Fictional senior"),
    ]
    household = SimpleNamespace(id=uuid.uuid4())
    per_subject = {
        people[0].id: facts(age=22, student_status=True, current_education_level="undergraduate"),
        people[1].id: facts(age=75, employment_status="retired"),
    }
    monkeypatch.setattr(
        module,
        "resolve",
        lambda session, uid, ref, **kw: (
            None,
            next((p for p in people if str(p.id) == str(ref.id)), household),
            None,
        ),
    )
    monkeypatch.setattr(
        service,
        "view",
        lambda *a, **kw: SimpleNamespace(
            members=[{"id": str(p.id), "access": "authorized"} for p in people]
            + [{"id": str(uuid.uuid4()), "access": "denied"}]
        ),
    )
    accessed = []

    def subject_facts(session, kind, identifier):
        accessed.append(identifier)
        return per_subject[identifier]

    monkeypatch.setattr(module, "subject_facts", subject_facts)
    monkeypatch.setattr(
        module, "quality", lambda row: {"evidence_strength": "substantive_document"}
    )
    monkeypatch.setattr(
        module, "compare", lambda *a: []
    )  # equally unknown; similarity is not eligibility
    cards = {
        r.id: research_card(r.title, "India").model_copy(
            update={
                "id": uuid.uuid5(uuid.NAMESPACE_URL, r.id),
                "key": r.identity_key,
                "category": r.category,
            }
        )
        for r in catalogue
    }
    monkeypatch.setitem(
        sys.modules,
        "opportunity_platform.research.router",
        SimpleNamespace(card=lambda row: cards[row.id]),
    )
    session = SimpleNamespace(scalars=lambda statement: catalogue)
    request = GuidanceRequest(subject={"kind": "household", "id": household.id}, limit=24)
    result = guidance(session, "fictional-owner", request)
    assert result.neural_status.startswith("local_cpu:")
    assert set(accessed) == {p.id for p in people}  # no household/denied member facts
    for person, top in zip(people, ("fictional-education", "fictional-pension"), strict=True):
        items = [item for item in result.items if item.subject_id == str(person.id)]
        assert items[0].parent_key == top
        assert len(items) == 2 and all(i.relevance_group == "information_gaps" for i in items)
    paged = [
        guidance(
            session, "fictional-owner", request.model_copy(update={"limit": 1, "offset": offset})
        ).items[0]
        for offset in range(result.candidate_count)
    ]
    assert [(i.subject_id, i.parent_key) for i in paged] == [
        (i.subject_id, i.parent_key) for i in result.items
    ]
    assert all(not item.eligibility_verified for item in result.items)
    # The same authorized entry point must use enterprise facts, not either person's.
    business = SimpleNamespace(id=uuid.uuid4(), name="Fictional enterprise")
    per_subject[business.id] = facts(business_sector="manufacturing", business_size="small")
    monkeypatch.setattr(module, "resolve", lambda *a, **kw: (None, business, None))
    enterprise = guidance(
        session, "fictional-owner", GuidanceRequest(subject={"kind": "business", "id": business.id})
    )
    assert enterprise.neural_status.startswith("local_cpu:")
    assert enterprise.items[0].parent_key == "fictional-business"
    assert len(enterprise.items) == 2
    assert all(
        i.subject_kind == "business" and i.subject_id == str(business.id) for i in enterprise.items
    )


@pytest.fixture
def public_guidance(client, db):
    from test_research_guidance import real_guidance

    return real_guidance.__wrapped__(client, db)


def test_real_public_catalogue_ranking_preserves_mismatches_evidence_and_pages(
    real_model, public_guidance, monkeypatch
):
    from sqlalchemy import func, select
    from test_research_completion import auth, request
    from test_research_ranking import profile

    from opportunity_platform.core.config import settings
    from opportunity_platform.db.models import OpportunityVersion, PolicyEmbedding, ProfileFact

    client, db = public_guidance
    auth()
    profile(db)
    counts = [
        db.scalar(select(func.count()).select_from(table))
        for table in (ProfileFact, PolicyEmbedding, OpportunityVersion)
    ]
    monkeypatch.setattr(settings(), "neural_retrieval_enabled", False)
    baseline = request(client)
    monkeypatch.setattr(settings(), "neural_retrieval_enabled", True)
    start = time.perf_counter()
    actual = request(client)
    first_seconds = time.perf_counter() - start
    start = time.perf_counter()
    warm = request(client, limit=7)
    warm_seconds = time.perf_counter() - start
    assert actual["neural_status"].startswith("local_cpu:")
    assert actual["candidate_count"] == baseline["candidate_count"] > 24

    def identities(data):
        return [item["parent_key"] for item in data["items"]]

    assert set(identities(actual)) == set(identities(baseline))
    assert identities(actual) != identities(baseline)  # actual model changes within-group ordering
    assert identities(warm) == identities(actual)[:7]
    for item in actual["items"]:
        previous = next(i for i in baseline["items"] if i["parent_key"] == item["parent_key"])
        assert item["conditions"] == previous["conditions"]
        assert item["listing"] == previous["listing"]
        assert not item["eligibility_verified"]
    group_order = {"promising": 0, "information_gaps": 1, "known_mismatch": 2}
    order = [group_order[item["relevance_group"]] for item in actual["items"]]
    assert order == sorted(order)
    pension = next(
        i for i in actual["items"] if i["parent_key"] == "rajasthan-pension-national-old-age"
    )
    assert pension["relevance_group"] == "known_mismatch"
    assert actual["reviewed"]["catalogue_count"] == 0
    assert counts == [
        db.scalar(select(func.count()).select_from(table))
        for table in (ProfileFact, PolicyEmbedding, OpportunityVersion)
    ]
    assert first_seconds < 20 and warm_seconds < 3
    print(
        f"real_profile_neural public catalogue paginated={first_seconds:.3f}s "
        f"warm_page={warm_seconds:.3f}s pairs={actual['candidate_count']}"
    )
