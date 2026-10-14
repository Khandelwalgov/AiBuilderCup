"""Release correctness with saved public candidate copies; no application schema writes."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from test_pipeline import approve, pipeline, version  # noqa: F401
from test_workspaces import publish_two, setup_person

from opportunity_platform.db.models import (
    ActionItem,
    MatchEvaluation,
    Opportunity,
    OpportunityVersion,
    SourceSnapshot,
)
from opportunity_platform.eligibility import service as eligibility
from opportunity_platform.eligibility.rules import FactInput
from opportunity_platform.ingestion import service as ingestion
from opportunity_platform.ingestion.schemas import CandidateData, Citation, validate_evidence
from opportunity_platform.planning import service as planning
from opportunity_platform.planning.documents import dependency
from opportunity_platform.profiles.service import ProfileWrite, save_profile
from opportunity_platform.subjects import service as subjects


def count(db, model=MatchEvaluation):
    return db.scalar(select(func.count()).select_from(model))


def test_actual_depwd_copy_documents_merge_only_explicit_equivalents(db, pipeline):  # noqa: F811
    actor, _ = pipeline
    data = json.loads(
        (
            Path(__file__).resolve().parents[3] / "data/fixtures/depwd-saved-candidates.json"
        ).read_text()
    )
    ingestion.ingest(db, "depwd-pre-matric", actor)
    v = version(db)
    first = db.get(Opportunity, v.opportunity_id)
    for index, item in enumerate(data["records"]):
        validate_evidence(CandidateData.model_validate(item["candidate"]), item["pages"])
        if index:
            op = Opportunity(
                source_id=first.source_id,
                source_key="isolated-saved-post-copy",
                category="education",
                is_synthetic=False,
            )
            db.add(op)
            db.flush()
            v = OpportunityVersion(
                opportunity_id=op.id,
                version=1,
                snapshot_id=v.snapshot_id,
                title=item["candidate"]["title"],
                summary="Isolated public candidate copy only",
                content_hash=item["hash"],
                source_url=v.source_url,
            )
            db.add(v)
            db.flush()
        v.extraction = item["candidate"]
        db.get(SourceSnapshot, v.snapshot_id).pages = item["pages"]
        db.commit()
        approve(db, actor, v)  # Isolated schema ONLY; genuine drafts untouched.
    setup_person(db)
    plan = planning.build(db, "fictional-owner", subjects.SubjectRef())
    documentary = [a for a in plan.actions if a.kind == "document"]
    shared = [a for a in documentary if len({o["id"] for o in a.opportunities}) == 2]
    assert len(shared) == 8
    assert len(documentary) == 8
    assert all(len({o["version_id"] for o in a.opportunities}) == 2 for a in shared)
    other = [a for a in plan.actions if "Other requisite documents" in a.title]
    assert len(other) == 1 and len(other[0].opportunities) == 1
    c = Citation(
        source_url="https://example.gov.in/policy",
        passage="public",
        page=1,
        language="en",
        basis="explicit",
    )
    assert dependency("Income certificate of the parent", c) != dependency(
        "Income certificate of the parent", c.model_copy(update={"page": 2})
    )
    assert dependency("Income certificate for prior financial year", c) is None
    assert dependency("Disability certificate unless exempt", c) is None


def test_evaluation_fingerprint_relevant_changes_and_context(db, pipeline):  # noqa: F811
    first, _ = publish_two(db, pipeline)
    setup_person(db)
    one = planning.build(db, "fictional-owner", subjects.SubjectRef())
    assert count(db) == 2
    for _ in range(3):
        again = planning.build(db, "fictional-owner", subjects.SubjectRef())
        assert {e.id for e in again.evaluations} == {e.id for e in one.evaluations}
    assert count(db) == 2
    save_profile(
        db,
        "fictional-owner",
        ProfileWrite(
            display_name="Fictional",
            facts=[FactInput(key="age", value=30), FactInput(key="nationality", value="Indian")],
        ),
    )
    planning.build(db, "fictional-owner", subjects.SubjectRef())
    assert count(db) == 2  # recreated fact IDs and irrelevant nationality do not matter
    save_profile(
        db,
        "fictional-owner",
        ProfileWrite(display_name="Fictional", facts=[FactInput(key="age", value=12)]),
    )
    assert count(db) == 4
    plan = planning.build(db, "fictional-owner", subjects.SubjectRef())
    assert count(db) == 4 and all(
        e.status == "not_eligible_on_known_facts" for e in plan.evaluations
    )
    fresh = eligibility.check(db, "fictional-owner", first.id, application_type="fresh")
    renewal = eligibility.check(db, "fictional-owner", first.id, application_type="renewal")
    assert fresh.id != renewal.id
    assert (
        eligibility.check(db, "fictional-owner", first.id, application_type="renewal").id
        == renewal.id
    )
    before = (count(db), count(db, ActionItem))
    planning.build(db, "fictional-owner", subjects.SubjectRef(), [FactInput(key="age", value=30)])
    assert (count(db), count(db, ActionItem)) == before


def test_parallel_plans_and_separate_subjects(db, pipeline):  # noqa: F811
    publish_two(db, pipeline)
    setup_person(db)
    schema = db.scalar(text("select current_schema()"))
    db.commit()

    def run():
        with Session(db.bind) as separate:
            return planning.build(separate, "fictional-owner", subjects.SubjectRef())

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda _: run(), range(3)))
    assert count(db) == 2
    assert len({tuple(e.id for e in p.evaluations) for p in results}) == 1
    assert schema.startswith("test_")
    household = subjects.create_household(
        db, "fictional-owner", subjects.HouseholdWrite(name="Fictional household")
    )
    business = subjects.save_business(
        db,
        "fictional-owner",
        subjects.BusinessWrite(name="Fictional business", legal_status="unregistered", facts=[]),
    )
    for kind, obj in [("household", household), ("business", business)]:
        ref = subjects.SubjectRef(kind=kind, id=obj.id)
        first = planning.build(db, "fictional-owner", ref)
        assert [e.id for e in planning.build(db, "fictional-owner", ref).evaluations] == [
            e.id for e in first.evaluations
        ]
        with pytest.raises(Exception) as denied:
            planning.build(db, "fictional-stranger", ref)
        assert getattr(denied.value, "status_code", getattr(denied.value, "status", 404)) in (
            403,
            404,
        )
