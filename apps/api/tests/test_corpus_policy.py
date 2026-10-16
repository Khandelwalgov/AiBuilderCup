"""Offline pipeline tests; real archive cases never invoke a model or publish."""

import copy
import hashlib
import io
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pypdf import PdfWriter
from sqlalchemy import func, select

from opportunity_platform.core.errors import APIError
from opportunity_platform.corpus.schemas import ManifestRecord, SourceSpec
from opportunity_platform.db.models import (
    AuditEvent,
    CandidateReview,
    Opportunity,
    OpportunityVersion,
    Requirement,
    User,
)
from opportunity_platform.ingestion.corpus_policy.archive import (
    Audited,
    audit_record,
    clauses_for,
    extract_pages,
    load_manifest,
    registry_from,
)
from opportunity_platform.ingestion.corpus_policy.contracts import AIReview
from opportunity_platform.ingestion.corpus_policy.service import extract_candidate, import_archive
from opportunity_platform.ingestion.corpus_policy.validation import digest, validate
from opportunity_platform.ingestion.corpus_policy.workflow import run_pipeline

TEXT = (
    "Learner scholarship guidelines. Applicants must be at least 18 years old. "
    "Annual income of parents must not exceed Rs 2.5 lakh. "
    "Application closes on 31 October 2026."
)
URL = "https://test.gov.in/guidelines.pdf"


def record(raw, fmt="pdf", url=URL):
    sha = hashlib.sha256(raw).hexdigest()
    return ManifestRecord(
        snapshot_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid5(uuid.NAMESPACE_URL, url)),
        previous_snapshot_id=None,
        canonical_source_url=url,
        originating_domain="test.gov.in",
        final_url=url,
        downloaded_at=datetime.now(UTC),
        sha256=sha,
        size_bytes=len(raw),
        format=fmt,
        blob_path=f"blobs/{sha[:2]}/{sha}.{fmt}",
        http_metadata={},
        validation={},
        discoveries=[
            {
                "source_key": "test",
                "discovery_url": "https://test.gov.in/index",
                "title": "Learner scholarship guidelines",
                "issuing_authority": "Index owner",
            }
        ],
    )


def audited(text=TEXT):
    r = record(text.encode())
    pages = [{"page": 1, "source_url": URL, "text": text, "quality": "readable_text_unverified"}]
    return Audited(
        r,
        "Learner scholarship guidelines",
        "policy_guideline",
        pages,
        clauses_for(pages),
        technically_ingestible=True,
        suitable_for_extraction=True,
    )


def envelope(a, value=18):
    page = next(p for p in a.pages if len(p["text"].strip()) >= 10)
    citation = {
        "source_url": page["source_url"],
        "page": page["page"],
        "passage": page["text"][:1000],
        "language": "original",
        "basis": "explicit",
    }
    return {
        "candidate": {
            "title": page["text"].strip()[:80],
            "summary": page["text"].strip()[:200],
            "category": "education",
            "field_evidence": [
                {"field": field, "citation": citation} for field in ["title", "summary", "category"]
            ],
            "requirements": [
                {
                    "description": "Applicants must be at least 18 years old.",
                    "rule": {
                        "op": "condition",
                        "condition": {"op": "gte", "fact": "age", "value": value},
                    },
                    "evidence": citation,
                }
            ],
        },
        "coverage": [
            {
                "clause_id": c.id,
                "disposition": "represented",
                "requirement_indexes": [0],
                "reason": "The cited rule represents this exact material source block.",
            }
            for c in a.clauses
        ],
    }


class Extractor:
    identity = "mock:extractor:test-only"
    model = "mock-no-paid-calls"

    def __init__(self, outputs):
        self.outputs, self.feedback, self.calls = outputs, [], 0

    def extract(self, a, focus, feedback=None, previous=None):
        self.feedback.append(feedback)
        index = min(self.calls, len(self.outputs) - 1)
        self.calls += 1
        return copy.deepcopy(self.outputs[index]), {"mock": True}


class Reviewer:
    identity = "mock:independent-reviewer:test-only"

    def __init__(self, issues=None, fail=False):
        self.calls, self.issues, self.fail = 0, issues or [], fail

    def review(self, a, candidate):
        self.calls += 1
        if self.fail:
            raise ValueError("Mock invalid reviewer")
        return {
            "assessment": "issues_found" if self.issues else "no_issues_detected",
            "candidate_hash": digest(candidate),
            "source_hash": a.record.sha256,
            "examined_clause_ids": [c.id for c in a.clauses],
            "issues": self.issues,
        }, {"mock": True}


def test_numeric_feedback_repairs_at_most_twice():
    a = audited()
    extractor, reviewer = Extractor([envelope(a, 19), envelope(a, 20), envelope(a)]), Reviewer()
    out = run_pipeline(a, "Learner scholarship", extractor, reviewer)
    assert out.status == "draft_for_human_review"
    assert out.repair_cycles == 2 and out.model_calls == 6
    assert extractor.feedback[1][0]["code"] == "numerical_value_not_in_clause"
    assert out.human_required
    assert "human" in out.candidate.candidate.review_flags[0]


def test_persistent_failure_escalates_and_never_mutates_source():
    a = audited()
    before = copy.deepcopy(a.pages)
    out = run_pipeline(a, "Learner scholarship", Extractor([envelope(a, 99)]), Reviewer())
    assert out.status == "human_escalation" and out.candidate is None
    assert out.model_calls == 6 and out.repair_cycles == 2
    assert a.pages == before
    with pytest.raises(ValueError, match="At most two"):
        run_pipeline(a, "Focus", Extractor([]), Reviewer(), max_repairs=3)


def test_independent_review_failure_and_critical_issue_stop_repairs():
    a = audited()
    out = run_pipeline(a, "Learner scholarship", Extractor([envelope(a)]), Reviewer(fail=True))
    assert out.status == "human_escalation" and out.model_calls == 2
    citation = envelope(a)["candidate"]["requirements"][0]["evidence"]
    problem = {
        "code": "wrong_interpretation",
        "severity": "critical",
        "field": "requirements",
        "message": "The interpretation reverses a substantive source condition.",
        "evidence": citation,
        "suggested_correction": "Request an authorized human decision.",
        "human_required": True,
    }
    out = run_pipeline(a, "Learner scholarship", Extractor([envelope(a)]), Reviewer([problem]))
    assert out.status == "human_escalation" and out.repair_cycles == 0


@pytest.mark.parametrize(
    "mutation,code",
    [
        (
            lambda x: x["candidate"]["requirements"][0]["evidence"].update(
                passage="Fabricated clause"
            ),
            "citation_or_field_evidence_invalid",
        ),
        (lambda x: x.update(coverage=[]), "clause_unaccounted"),
        (
            lambda x: x["candidate"].update(
                benefits="Benefit of Rs 999999",
                field_evidence=[
                    *x["candidate"]["field_evidence"],
                    {
                        "field": "benefits",
                        "citation": x["candidate"]["requirements"][0]["evidence"],
                    },
                ],
            ),
            "metadata_amount_not_in_clause",
        ),
        (
            lambda x: x["candidate"]["requirements"][0]["rule"]["condition"].update(op="execute"),
            "schema_invalid",
        ),
    ],
)
def test_deterministic_rejections(mutation, code):
    a = audited()
    value = envelope(a)
    mutation(value)
    _, problems = validate(value, a)
    assert code in {p.code for p in problems}


def test_income_period_definition_and_deadline():
    a = audited()
    value = envelope(a)
    condition = {
        "op": "lte",
        "fact": "annual_parental_income",
        "value": 250000,
        "income_period": "annual",
        "income_definition": "parents",
    }
    value["candidate"]["requirements"][0]["rule"]["condition"] = condition
    _, issues = validate(value, a)
    assert not [i for i in issues if i.severity == "error"]
    condition["income_period"] = "2025-26"
    _, issues = validate(value, a)
    assert "income_period_not_cited" in {i.code for i in issues}
    condition["income_period"] = "annual"
    condition["income_definition"] = "household sum"
    _, issues = validate(value, a)
    assert "income_definition_not_cited" in {i.code for i in issues}
    condition["income_definition"] = "parents"
    value["candidate"]["closes_on"] = "2026-10-31"
    value["candidate"]["field_evidence"].append(
        {"field": "closes_on", "citation": value["candidate"]["requirements"][0]["evidence"]}
    )
    assert not [i for i in validate(value, a)[1] if i.code == "deadline_not_explicit"]
    a.pages[0]["text"] = a.pages[0]["text"].replace("Application closes on", "Published on")
    value["candidate"]["field_evidence"][-1]["citation"] = {
        **value["candidate"]["field_evidence"][-1]["citation"],
        "passage": a.pages[0]["text"],
    }
    assert "deadline_not_explicit" in {i.code for i in validate(value, a)[1]}


def test_amendment_or_ocr_sources_get_no_model_calls():
    a = audited()
    a.suitable_for_extraction = False
    a.needs_ocr = True
    extractor, reviewer = Extractor([]), Reviewer()
    out = run_pipeline(a, "Focus", extractor, reviewer)
    assert out.status == "human_escalation" and out.model_calls == 0
    a.needs_ocr = False
    a.document_type = "amendment"
    a.suitable_for_extraction = True
    _, issues = validate(envelope(a), a)
    assert "amendment_context_unresolved" in {i.code for i in issues}


def test_archive_integrity_path_and_pdf_html_provenance(tmp_path):
    writer = PdfWriter()
    writer.add_blank_page(100, 100)
    output = io.BytesIO()
    writer.write(output)
    raw = output.getvalue()
    r = record(raw)
    path = tmp_path / r.blob_path
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    source = SourceSpec(
        key="test",
        authority="Index owner",
        jurisdiction="India",
        category="education",
        seeds=["https://test.gov.in/index"],
        allowed_hosts=["test.gov.in"],
        access="public",
        access_note="Synthetic offline test",
    )
    result = audit_record(r, tmp_path, {"test": source})
    assert result.technically_ingestible and result.needs_ocr
    assert result.pages[0]["page"] == 1 and result.document_issuer is None
    path.write_bytes(b"bad")
    assert not audit_record(r, tmp_path, {"test": source}).technically_ingestible
    r.blob_path = "../outside.pdf"
    assert not audit_record(r, tmp_path, {"test": source}).technically_ingestible
    html = (
        b"<main><h2>Eligibility</h2><p>Applicants must be eighteen years old.</p>"
        b"<script>send_secrets()</script><h2>Benefits</h2><p>Grant support.</p></main>"
    )
    pages = extract_pages(html, record(html, "html"))
    assert [p["section"] for p in pages] == ["Eligibility", "Benefits"]
    assert all("send_secrets" not in p["text"] for p in pages)


def test_reviewer_forged_citation_hash_or_approval_rejected():
    a = audited()

    class Forged(Reviewer):
        def review(self, a, c):
            raw, usage = super().review(a, c)
            raw["candidate_hash"] = "0" * 64
            return raw, usage

    assert run_pipeline(a, "Focus", Extractor([envelope(a)]), Forged()).status == "human_escalation"
    with pytest.raises(ValueError):
        AIReview.model_validate({"approve": True})


def test_import_draft_idempotency_versions_permissions_and_no_publication(db):
    actor = User(firebase_uid="corpus-test-admin", is_admin=True)
    other = User(firebase_uid="corpus-test-other", is_admin=False)
    db.add_all([actor, other])
    db.commit()
    # Fingerprint every pre-existing version/review; this includes fixture history.
    before = [
        (v.id, copy.deepcopy(v.extraction), v.publication_state)
        for v in db.scalars(select(OpportunityVersion))
    ]
    review_count = db.scalar(select(func.count()).select_from(CandidateReview))
    requirement_count = db.scalar(select(func.count()).select_from(Requirement))
    a = audited()
    with pytest.raises(APIError):
        import_archive(db, a, other)
    snapshot, imported = import_archive(db, a, actor)
    assert import_archive(db, a, actor)[0].id == snapshot.id
    assert imported.status == "archive_imported"
    assert snapshot.response_metadata["offline_import_not_new_source_check"]
    extractor, reviewer = Extractor([envelope(a)]), Reviewer()
    result = extract_candidate(db, a, actor, "Learner scholarship", extractor, reviewer)
    assert result.status == "draft_for_human_review"
    assert (
        extract_candidate(db, a, actor, "Learner scholarship", extractor, reviewer).id == result.id
    )
    assert extractor.calls == 1 and reviewer.calls == 1
    draft = db.get(OpportunityVersion, uuid.UUID(result.diagnostics["draft_id"]))
    assert draft.publication_state == "draft" and draft.status == "needs_review"
    assert db.get(Opportunity, draft.opportunity_id).published_version_id is None
    assert db.scalar(select(func.count()).select_from(Requirement)) == requirement_count
    assert db.scalar(select(func.count()).select_from(CandidateReview)) == review_count
    assert [
        (
            db.get(OpportunityVersion, ident).extraction,
            db.get(OpportunityVersion, ident).publication_state,
        )
        for ident, _, _ in before
    ] == [(data, state) for _, data, state in before]
    newer = copy.deepcopy(a)
    newer.record.sha256 = hashlib.sha256(b"changed").hexdigest()
    newer.record.snapshot_id = str(uuid.uuid4())
    newer.record.previous_snapshot_id = a.record.snapshot_id
    second, _ = import_archive(db, newer, actor)
    assert second.id != snapshot.id
    assert second.response_metadata["previous_imported_snapshot_id"] == str(snapshot.id)
    duplicate = copy.deepcopy(a)
    duplicate.record.document_id = str(uuid.uuid4())
    duplicate.record.canonical_source_url = "https://test.gov.in/duplicate.pdf"
    third, _ = import_archive(db, duplicate, actor)
    assert third.id != snapshot.id
    assert third.response_metadata["duplicate_content_snapshot_id"] == str(snapshot.id)
    assert db.scalar(select(func.count()).select_from(AuditEvent)) > 0


ARCHIVE = Path(os.environ.get("CORPUS_ARCHIVE_ROOT", "/nonexistent-corpus"))
ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    "group", ["rajasthan-scholarships", "rajasthan-welfare", "msme-ramp", "rajasthan-tenders"]
)
@pytest.mark.skipif(
    not ARCHIVE.exists(), reason="Set CORPUS_ARCHIVE_ROOT to the real local archive"
)
def test_real_archived_sources_with_mocked_pipeline(db, group):
    registry = registry_from(ROOT / "data/corpus/sources.json")
    records = [
        r
        for r in load_manifest(ROOT / "data/corpus/acquired-manifest.jsonl")
        if r.discoveries[0]["source_key"] == group
    ]
    choices = []
    for record_ in records:
        a = audit_record(record_, ARCHIVE, registry)
        choices.append(a)
        if a.suitable_for_extraction:
            break
    a = next((a for a in choices if a.suitable_for_extraction), choices[0])
    assert a.technically_ingestible
    actor = User(firebase_uid="real-corpus-test-" + group, is_admin=True)
    db.add(actor)
    db.commit()
    if not a.suitable_for_extraction:
        extractor, reviewer = Extractor([]), Reviewer()
        result = extract_candidate(
            db, a, actor, "Explicit test scope for human review only", extractor, reviewer
        )
        assert result.status == "human_escalation" and extractor.calls == 0
        return
    # Mock unknown rules preserve exact real excerpts; this does not measure extraction accuracy.
    raw = envelope(a)
    raw["candidate"]["requirements"] = []
    raw["coverage"] = []
    for clause in a.clauses:
        i = len(raw["candidate"]["requirements"])
        if i >= 50:
            raw["coverage"].append(
                {
                    "clause_id": clause.id,
                    "disposition": "needs_review",
                    "reason": "More clauses than this bounded mock can represent.",
                }
            )
            continue
        raw["candidate"]["requirements"].append(
            {
                "description": clause.passage[:2000],
                "rule": {"op": "condition", "condition": {"op": "unknown"}},
                "evidence": {
                    "source_url": clause.source_url,
                    "page": clause.page,
                    "passage": clause.passage[:6000],
                    "language": "original",
                    "basis": "explicit",
                },
            }
        )
        raw["coverage"].append(
            {
                "clause_id": clause.id,
                "disposition": "represented",
                "requirement_indexes": [i],
                "reason": "Explicit unknown mock rule.",
            }
        )
    # Avoid copying multi-page numerical claims into source metadata in this mock.
    raw["candidate"]["summary"] = "Source content awaiting authorized human interpretation."
    result = extract_candidate(
        db,
        a,
        actor,
        "Explicit test scope for human review only",
        Extractor([raw]),
        Reviewer(),
        max_repairs=0,
    )
    assert result.status in {"draft_for_human_review", "human_escalation"}
    assert result.diagnostics["workflow"]["human_required"] is True
    assert all(
        o.published_version_id is None
        for o in db.scalars(select(Opportunity).where(Opportunity.source_key.like("corpus:%")))
    )
