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
    SourceSnapshot,
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


def test_numeric_feedback_repairs_at_most_once():
    a = audited()
    extractor, reviewer = Extractor([envelope(a, 19), envelope(a)]), Reviewer()
    out = run_pipeline(a, "Learner scholarship", extractor, reviewer)
    assert out.status == "draft_for_human_review"
    assert out.repair_cycles == 1 and out.model_calls == 4
    assert extractor.feedback[1][0]["code"] == "numerical_value_not_in_clause"
    assert out.human_required
    assert "human" in out.candidate.candidate.review_flags[0]


def test_persistent_failure_escalates_and_never_mutates_source():
    a = audited()
    before = copy.deepcopy(a.pages)
    out = run_pipeline(a, "Learner scholarship", Extractor([envelope(a, 99)]), Reviewer())
    assert out.status == "human_escalation" and out.candidate is None
    assert out.model_calls == 4 and out.repair_cycles == 1
    assert a.pages == before
    with pytest.raises(ValueError, match="At most one"):
        run_pipeline(a, "Focus", Extractor([]), Reviewer(), max_repairs=3)


def test_independent_review_failure_and_critical_issue_stop_repairs():
    a = audited()
    out = run_pipeline(a, "Learner scholarship", Extractor([envelope(a)]), Reviewer(fail=True))
    assert out.status == "human_escalation" and out.model_calls == 2
    assert out.candidate is not None  # cited draft remains reviewable, never self-approved
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


def test_prepared_interactive_draft_is_not_independently_verified(db):
    from opportunity_platform.ingestion.corpus_policy.prepared import (
        PendingIndependentReview,
        PreparedExtractor,
    )

    a = audited()
    actor = User(firebase_uid="interactive-stage-admin", is_admin=True)
    db.add(actor)
    db.commit()
    extractor = PreparedExtractor(
        {"source_hash": a.record.sha256, "candidate": envelope(a)}, a.record.sha256
    )
    run = extract_candidate(
        db, a, actor, "Learner scholarship", extractor, PendingIndependentReview(), max_repairs=0
    )
    db.commit()
    assert run.status == "human_escalation"
    assert run.usage["calls"] == 0
    draft = db.get(OpportunityVersion, uuid.UUID(run.diagnostics["draft_id"]))
    assert draft.publication_state == "draft" and draft.status == "needs_review"
    assert draft.extraction_provider.startswith("codex:interactive")
    assert db.get(Opportunity, draft.opportunity_id).published_version_id is None
    assert "Independent semantic" in str(draft.extraction["review_flags"])
    repeated = extract_candidate(
        db, a, actor, "Learner scholarship", extractor, PendingIndependentReview(), max_repairs=0
    )
    assert repeated.id == run.id


def test_real_semantic_reviewer_must_cover_claims_and_cannot_soften_contradictions():
    class SemanticReviewer(Reviewer):
        semantic_findings_required = True

        def review(self, source, candidate):
            raw, usage = super().review(source, candidate)
            data = candidate.candidate
            fields = {f"requirements.{i}" for i in range(len(data.requirements))}
            fields |= {
                name
                for name in [
                    "title",
                    "summary",
                    "issuer",
                    "category",
                    "country",
                    "state",
                    "district",
                    "benefits",
                    "restrictions",
                    "required_documents",
                    "opens_on",
                    "closes_on",
                    "apply_url",
                ]
                if getattr(data, name)
            }
            citation = data.requirements[0].evidence.model_dump(mode="json")
            raw["findings"] = [
                {
                    "field": name,
                    "assessment": "supported",
                    "explanation": "Synthetic test claim is supported by the fixture.",
                    "evidence": citation,
                    "human_required": True,
                }
                for name in sorted(fields)
            ]
            raw["findings"][0]["assessment"] = "contradicted"
            raw["assessment"] = "issues_found"
            raw["issues"] = [
                {
                    "code": "contradiction",
                    "severity": "warning",
                    "field": raw["findings"][0]["field"],
                    "message": "Synthetic substantive contradiction for verification test.",
                    "evidence": citation,
                    "suggested_correction": "Correct the claim against the original source.",
                    "human_required": True,
                }
            ]
            return raw, usage

    source = audited()
    out = run_pipeline(
        source, "Learner scholarship", Extractor([envelope(source)]), SemanticReviewer()
    )
    assert out.status == "human_escalation" and out.repair_cycles == 0
    assert any(
        issue.code == "semantic_claim_disputed" and issue.severity == "critical"
        for issue in out.stages[0].issues
    )


def test_public_government_library_never_reads_private_documents(client, db):
    actor = User(firebase_uid="library-admin", is_admin=True)
    db.add(actor)
    db.commit()
    a = audited()
    a.record.discoveries[0]["document_category"] = "scholarships"
    a.record.discoveries[0]["jurisdiction"] = "India"
    snapshot, _ = import_archive(db, a, actor)
    db.commit()
    page = client.get(
        "/v1/government-sources",
        params={"category": "scholarships", "state": "India", "q": "parents"},
    )
    assert page.status_code == 200 and page.json()["total"] == 1
    assert "blob_path" not in page.text and "actor_id" not in page.text
    detail = client.get("/v1/government-sources/" + str(snapshot.id))
    assert detail.status_code == 200
    assert detail.json()["pages"][0]["text"] == a.pages[0]["text"]
    assert client.get("/v1/government-sources/" + str(uuid.uuid4())).status_code == 404
    assert client.get("/v1/government-sources", params={"format": "pdf"}).json()["total"] == 1


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
    from opportunity_platform.opportunities.service import catalogue

    public_before = list(db.execute(catalogue()))
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
    assert list(db.execute(catalogue())) == public_before
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
    a = next(
        (a for a in choices if a.suitable_for_extraction),
        next(
            (a for a in choices if a.document_type in {"policy_guideline", "tender_notice"}),
            choices[0],
        ),
    )
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
    assert result.status == "draft_for_human_review"
    assert result.diagnostics["workflow"]["stages"][0]["independent_review"] is not None
    assert result.diagnostics["workflow"]["human_required"] is True
    assert all(
        o.published_version_id is None
        for o in db.scalars(select(Opportunity).where(Opportunity.source_key.like("corpus:%")))
    )


def test_independent_interpretation_issue_drives_repair():
    a = audited()
    wrong = envelope(a)
    wrong["candidate"]["requirements"][0]["rule"]["condition"]["op"] = "lte"
    evidence = wrong["candidate"]["requirements"][0]["evidence"]
    problem = {
        "code": "comparison_direction_wrong",
        "severity": "error",
        "field": "requirements.0",
        "message": "At least eighteen is a lower bound rather than an upper bound.",
        "evidence": evidence,
        "suggested_correction": "Use gte for the explicit lower bound.",
        "human_required": True,
    }

    class FeedbackReviewer(Reviewer):
        def review(self, a, candidate):
            self.issues = [problem] if self.calls == 0 else []
            return super().review(a, candidate)

    extractor = Extractor([wrong, envelope(a)])
    out = run_pipeline(a, "Learner scholarship", extractor, FeedbackReviewer())
    assert out.status == "draft_for_human_review" and out.repair_cycles == 1
    assert "comparison_direction_wrong" in {i["code"] for i in extractor.feedback[1]}
    assert out.stages[0].candidate_hash == out.stages[0].independent_review.candidate_hash


def test_pipeline_failure_saves_diagnostics_without_draft(db):
    actor = User(firebase_uid="corpus-escalation-admin", is_admin=True)
    db.add(actor)
    db.commit()
    a = audited()
    before = db.scalar(select(func.count()).select_from(OpportunityVersion))
    result = extract_candidate(
        db, a, actor, "Learner scholarship", Extractor([envelope(a, 99)]), Reviewer()
    )
    assert result.status == "human_escalation"
    assert len(result.diagnostics["workflow"]["stages"]) == 2
    assert db.scalar(select(func.count()).select_from(OpportunityVersion)) == before


def test_live_provider_disabled_does_not_construct_client(monkeypatch):
    from opportunity_platform.core.config import settings
    from opportunity_platform.ingestion.corpus_policy import live

    monkeypatch.setattr(settings(), "ai_ingestion_live_enabled", False)
    monkeypatch.setattr(live.genai, "Client", lambda **kw: pytest.fail("Model calls prohibited"))
    role = live.GeminiRole("extractor", "operator-selected-model")
    with pytest.raises(ValueError, match="disabled"):
        role.extract(audited(), "Future operator focus")


def test_explicitly_unknown_income_keeps_unknown_instead_of_requiring_guessed_period():
    a = audited()
    value = envelope(a)
    value["candidate"]["requirements"][0]["rule"]["condition"] = {
        "op": "unknown",
        "fact": "annual_parental_income",
    }
    _, issues = validate(value, a)
    assert "unsupported_or_unknown_rule" in {i.code for i in issues}
    assert not {i.code for i in issues} & {"income_period_not_cited", "income_definition_not_cited"}


def test_document_index_titles_are_not_policy_rules(tmp_path):
    raw = (
        b'<html><form><h2>Hostel scheme</h2><a href="/a.pdf">Eligibility guidelines</a>'
        b'<a href="/b.pdf">Grant assistance</a>'
        b'<a href="/c.pdf">Required documents</a></form></html>'
    )
    r = record(raw, "html", "https://test.gov.in/index")
    path = tmp_path / r.blob_path
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    source = SourceSpec(
        key="test",
        authority="Index owner",
        jurisdiction="India",
        category="welfare",
        seeds=["https://test.gov.in/index"],
        allowed_hosts=["test.gov.in"],
        access="public",
        access_note="Synthetic offline test",
    )
    result = audit_record(r, tmp_path, {"test": source})
    assert result.technically_ingestible
    assert result.document_type == "document_index" and not result.suitable_for_extraction
    assert run_pipeline(result, "Hostel scheme", Extractor([]), Reviewer()).model_calls == 0


def test_html_policy_prose_retains_sections_and_is_not_a_link_index(tmp_path):
    raw = (
        b"<html><form><h2>Eligibility</h2><p>Applicants must be at least 18 years old.</p>"
        b'<a href="/a.pdf">Annex A</a><a href="/b.pdf">Annex B</a>'
        b'<a href="/c.pdf">Annex C</a></form></html>'
    )
    r = record(raw, "html", "https://test.gov.in/policy")
    path = tmp_path / r.blob_path
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    source = SourceSpec(
        key="test",
        authority="Index owner",
        jurisdiction="India",
        category="welfare",
        seeds=["https://test.gov.in/index"],
        allowed_hosts=["test.gov.in"],
        access="public",
        access_note="Synthetic offline test",
    )
    result = audit_record(r, tmp_path, {"test": source})
    assert result.suitable_for_extraction
    assert result.pages[0]["section"] == "Eligibility"


def test_source_reversion_retains_occurrence_and_refuses_text_overwrite(db):
    actor = User(firebase_uid="corpus-version-admin", is_admin=True)
    db.add(actor)
    db.commit()
    a = audited()
    original, first = import_archive(db, a, actor)
    b = copy.deepcopy(a)
    b.record.sha256 = hashlib.sha256(b"changed source bytes").hexdigest()
    b.record.snapshot_id = str(uuid.uuid4())
    b.record.previous_snapshot_id = a.record.snapshot_id
    changed, second = import_archive(db, b, actor)
    reverted = copy.deepcopy(a)
    reverted.record.snapshot_id = str(uuid.uuid4())
    reverted.record.previous_snapshot_id = b.record.snapshot_id
    reused, third = import_archive(db, reverted, actor)
    assert original.id == reused.id and changed.id != reused.id
    assert len({first.id, second.id, third.id}) == 3
    assert third.diagnostics["acquisition_previous_snapshot_id"] == b.record.snapshot_id
    tampered = copy.deepcopy(a)
    tampered.pages[0]["text"] = "An unrelated derivative must not overwrite the captured source."
    with pytest.raises(APIError) as exc:
        import_archive(db, tampered, actor)
    assert exc.value.code == "corpus_text_derivative_conflict"
    assert db.get(SourceSnapshot, original.id).pages == a.pages


def test_live_cli_preflight_stops_before_manifest_or_database(monkeypatch):
    from opportunity_platform.core.config import settings
    from opportunity_platform.ingestion.corpus_policy import cli

    monkeypatch.setattr(settings(), "ai_ingestion_live_enabled", False)
    monkeypatch.setattr(cli, "load_manifest", lambda _: pytest.fail("Preflight must run first"))
    monkeypatch.setattr(
        "sys.argv",
        [
            "corpus-policy",
            "live-test",
            "--execute",
            "--authorize-paid",
            "--actor-uid",
            "existing-operator",
            "--snapshot-id",
            "selected-snapshot",
            "--limit",
            "1",
            "--provider",
            "gemini",
            "--model",
            "selected-extractor",
            "--review-model",
            "selected-reviewer",
            "--focus",
            "Explicit scope",
            "--corpus-root",
            "/unused",
        ],
    )
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
