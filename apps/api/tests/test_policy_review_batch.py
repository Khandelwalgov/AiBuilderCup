import copy
from pathlib import Path

import pytest
from sqlalchemy import func, select

from opportunity_platform.admin.service import ReviewWrite, review
from opportunity_platform.db.models import (
    CandidateReview,
    Opportunity,
    OpportunityVersion,
    Requirement,
    Source,
    SourceSnapshot,
    User,
)
from opportunity_platform.ingestion.corpus_policy.review_batch import draft_id, load, plan, stage
from opportunity_platform.ingestion.corpus_policy.validation import digest, validate
from opportunity_platform.ingestion.schemas import CandidateData

BATCH = Path(__file__).resolve().parents[3] / "data/policy-review/2026-10-17/batch.json"


def test_archived_policy_batch_exact_evidence_and_holds():
    records = load(BATCH)
    result = plan(records)
    assert {r["key"] for r in result if r["draft_id"]} == {"team", "st-post-matric"}
    assert {r["key"] for r in result if not r["draft_id"]} == {"lean", "pms"}
    assert all(r["publication"] == "none" for r in result)
    for r in records:
        assert r["candidate_hash"] != r["approval_hash"]
        assert r["independent_review"]["status"] == "unavailable"


def test_changed_artifact_rejected(tmp_path):
    for source in BATCH.parent.glob("*.json"):
        (tmp_path / source.name).write_bytes(source.read_bytes())
    with (tmp_path / "team.json").open("a") as f:
        f.write(" ")
    with pytest.raises(ValueError, match="file hash"):
        load(tmp_path / "batch.json")


@pytest.fixture
def baseline(db):
    import uuid

    records = copy.deepcopy(load(BATCH))
    actor = User(firebase_uid="policy-review-operator", is_admin=True)
    db.add(actor)
    db.flush()
    for r in records:
        b = r["baseline"]
        db.add(
            Source(
                id=uuid.UUID(b["source_id"]), name=r["key"], url=b["source_url"], is_synthetic=False
            )
        )
        db.flush()
        db.add(
            SourceSnapshot(
                id=uuid.UUID(b["snapshot_id"]),
                source_id=uuid.UUID(b["source_id"]),
                content_hash=b["content_hash"],
                source_url=b["source_url"],
                pages=r["pages"],
                media_type="application/pdf",
                byte_count=100,
                response_metadata={},
            )
        )
        db.add(
            Opportunity(
                id=uuid.UUID(b["opportunity_id"]),
                source_id=uuid.UUID(b["source_id"]),
                source_key=r["key"],
                category=r["candidate"]["category"],
                is_synthetic=False,
            )
        )
        db.flush()
        original = copy.deepcopy(r["candidate"])
        original["summary"] = "Original private draft preserved"
        b["stored_candidate_hash"] = digest(original)
        db.add(
            OpportunityVersion(
                id=uuid.UUID(b["version_id"]),
                opportunity_id=uuid.UUID(b["opportunity_id"]),
                version=1,
                publication_state="draft",
                snapshot_id=uuid.UUID(b["snapshot_id"]),
                title=original["title"],
                summary=original["summary"],
                country="IN",
                extraction=original,
            )
        )
    db.commit()
    return records, actor


def test_append_idempotency_history_preservation_and_business_documents(db, baseline):
    records, actor = baseline
    before_reviews = db.scalar(select(func.count()).select_from(CandidateReview))
    before_versions = db.scalar(select(func.count()).select_from(OpportunityVersion))
    stage(db, records, actor)
    db.commit()
    stage(db, records, actor)
    db.commit()
    assert db.scalar(select(func.count()).select_from(OpportunityVersion)) == before_versions + 2
    assert db.scalar(select(func.count()).select_from(CandidateReview)) == before_reviews
    team = next(r for r in records if r["key"] == "team")
    new = db.get(OpportunityVersion, draft_id(team))
    opp = db.get(Opportunity, new.opportunity_id)
    assert opp.published_version_id is None and new.publication_state == "draft"
    assert (
        db.get(OpportunityVersion, __import__("uuid").UUID(team["baseline"]["version_id"])).summary
        == "Original private draft preserved"
    )
    # Only an explicit human-style admin approval creates public requirements.
    review(
        db,
        new.id,
        actor,
        ReviewWrite(
            decision="approve",
            note="Synthetic test approval",
            expected_hash=team["approval_hash"],
            acknowledge_flags=True,
            source_completeness_confirmed=True,
        ),
    )
    documents = list(
        db.scalars(
            select(Requirement).where(
                Requirement.version_id == new.id, Requirement.kind == "document"
            )
        )
    )
    assert len(documents) == 1 and documents[0].subject_context == "business"


@pytest.mark.parametrize("change", ["candidate", "pages", "publication", "role"])
def test_staging_fails_closed_before_insert(db, baseline, change):
    import uuid

    records, actor = baseline
    r = next(r for r in records if r["key"] == "team")
    if change == "candidate":
        old = db.get(OpportunityVersion, uuid.UUID(r["baseline"]["version_id"]))
        old.extraction = {**old.extraction, "summary": "Changed elsewhere"}
    elif change == "pages":
        snap = db.get(SourceSnapshot, uuid.UUID(r["baseline"]["snapshot_id"]))
        snap.pages = []
    elif change == "publication":
        db.get(
            OpportunityVersion, uuid.UUID(r["baseline"]["version_id"])
        ).publication_state = "rejected"
    else:
        actor.is_admin = False
    db.commit()
    before = db.scalar(select(func.count()).select_from(OpportunityVersion))
    with pytest.raises(Exception):
        stage(db, records, actor)
    db.rollback()
    assert db.scalar(select(func.count()).select_from(OpportunityVersion)) == before


def test_amounts_across_exact_pages_and_invented_amount_rejected():
    from types import SimpleNamespace

    r = next(r for r in load(BATCH) if r["key"] == "st-post-matric")
    audited = SimpleNamespace(
        pages=r["pages"],
        clauses=[],
        document_type="guidelines",
        needs_ocr=False,
        technically_ingestible=True,
    )
    raw = {"candidate": r["candidate"], "coverage": []}
    _, issues = validate(raw, audited)
    assert not [i for i in issues if i.code == "metadata_amount_not_in_clause"]
    bad = copy.deepcopy(raw)
    bad["candidate"]["benefits"] += " An extra Rs. 987654321 is paid."
    _, issues = validate(bad, audited)
    assert any(i.code == "metadata_amount_not_in_clause" for i in issues)
    assert CandidateData.model_validate(r["candidate"]).requirements[1].rule.op == "all"


def test_in_memory_tampering_cannot_stage(db, baseline):
    records, actor = baseline
    records[0]["candidate"]["benefits"] = "Changed after file validation"
    with pytest.raises(ValueError, match="In-memory"):
        stage(db, records, actor)


def test_consequential_publication_still_needs_human_confirmations(db, baseline):
    from opportunity_platform.core.errors import APIError

    records, actor = baseline
    stage(db, records, actor)
    db.commit()
    team = next(r for r in records if r["key"] == "team")
    with pytest.raises(APIError) as error:
        review(
            db,
            draft_id(team),
            actor,
            ReviewWrite(
                decision="approve",
                note="Incomplete confirmation",
                expected_hash=team["approval_hash"],
            ),
        )
    assert error.value.code == "review_confirmation_required"
    db.rollback()
    assert db.get(OpportunityVersion, draft_id(team)).publication_state == "draft"
