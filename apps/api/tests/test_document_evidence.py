import pytest
from test_pipeline import TEXT, URL, candidate, pipeline, version  # noqa: F401

from opportunity_platform.admin import service as admin
from opportunity_platform.core.errors import APIError
from opportunity_platform.ingestion import service as ingestion
from opportunity_platform.ingestion.schemas import (
    DocumentEvidence,
    FieldCitation,
    validate_evidence,
)


def test_legacy_document_draft_readable_but_not_publishable(db, pipeline):  # noqa: F811
    actor, _ = pipeline
    ingestion.ingest(db, "depwd-pre-matric", actor)
    v = version(db)
    data = candidate()
    data.required_documents = ["Income certificate"]
    citation = data.requirements[1].evidence
    data.field_evidence.append(FieldCitation(field="required_documents", citation=citation))
    corrected = admin.review(
        db,
        v.id,
        actor,
        admin.ReviewWrite(
            decision="correct",
            note="Document review",
            expected_hash=admin.digest(v.extraction),
            candidate=data,
        ),
    )
    with pytest.raises(APIError) as caught:
        admin.review(
            db,
            v.id,
            actor,
            admin.ReviewWrite(
                decision="approve",
                note="Review",
                expected_hash=corrected.candidate_hash,
                acknowledge_flags=True,
                source_completeness_confirmed=True,
            ),
        )
    assert caught.value.code == "document_evidence_required"
    data.document_evidence = [DocumentEvidence(document="Income certificate", evidence=citation)]
    validate_evidence(data, [{"page": 1, "source_url": URL, "text": TEXT}])
    data.document_evidence[0].evidence = citation.model_copy(
        update={"passage": "Forged document passage"}
    )
    with pytest.raises(ValueError):
        validate_evidence(data, [{"page": 1, "source_url": URL, "text": TEXT}])


def test_shallow_extraction_preserves_policy_category_and_application_context():
    from opportunity_platform.ingestion.schemas import Extraction

    data = candidate().model_dump(mode="json", exclude={"requirements"})
    data["requirements"] = [
        {
            "description": "Fictional renewal-only procedure",
            "kind": "procedure",
            "application_context": "renewal",
            "combine": "all",
            "conditions": [{"op": "unknown"}],
            "subject_context": "person",
            "evidence": candidate().requirements[0].evidence.model_dump(mode="json"),
        }
    ]
    result = Extraction.model_validate(data).candidate()
    assert result.requirements[0].kind == "procedure"
    assert result.requirements[0].application_context == "renewal"
