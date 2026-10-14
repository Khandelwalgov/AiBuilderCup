"""Offline source-backed Post-Matric curation from an existing official capture.

Not an AI extraction or a new live source check. Never approves a version.
"""

import argparse
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from opportunity_platform.admin.service import ReviewWrite, digest, review
from opportunity_platform.db.models import (
    AuditEvent,
    IngestionRun,
    Opportunity,
    OpportunityVersion,
    Source,
    SourceSnapshot,
)
from opportunity_platform.db.session import engine
from opportunity_platform.eligibility.rules import Condition, Rule
from opportunity_platform.ingestion.schemas import (
    CandidateData,
    CandidateRequirement,
    Citation,
    DocumentEvidence,
    FieldCitation,
    validate_evidence,
)
from opportunity_platform.ingestion.service import NAMESPACE, register
from opportunity_platform.profiles.service import require_admin


def candidate_from(pages):
    def cite(year, page, start=None, end=None):
        p = next(p for p in pages if f"/{year}/" in p["source_url"] and p["page"] == page)
        text = p["text"]
        if start:
            text = text[text.index(start) :]
        if end:
            text = text[: text.index(end)]
        return Citation(
            source_url=p["source_url"],
            page=page,
            passage=text.strip(),
            language="en",
            basis="explicit",
        )

    unknown = Rule(op="condition", condition=Condition(op="unknown"))
    school = cite(2025, 2)
    common = cite(2024, 5)
    req = []

    def add(text, evidence, kind="eligibility", context="all", subject="person", rule=None):
        req.append(
            CandidateRequirement(
                description=text,
                evidence=evidence,
                rule=rule or unknown,
                kind=kind,
                application_context=context,
                subject_context=subject,
            )
        )

    add(
        "Applicants must be Indian nationals.",
        common,
        rule=Rule(op="condition", condition=Condition(op="eq", fact="nationality", value="Indian")),
    )
    add(
        "Benchmark disability must be 40% or more under the Rights of "
        "Persons with Disabilities Act, 2016.",
        school,
        rule=Rule(
            op="condition", condition=Condition(op="gte", fact="disability_percentage", value=40)
        ),
    )
    add(
        "Post-matric study must be Class XI through postgraduate "
        "degree/diploma approved by the relevant recognized body, as "
        "amended in 2025.",
        school,
    )
    add(
        "Certain training courses are excluded; compare the student's "
        "exact course with NOTE 1 before deciding.",
        cite(2024, 7, "NOTE 1", "NOTE 2"),
    )
    add(
        "Repeating the same education stage in another subject is "
        "excluded, with specified LLB/BEd/BElEd exceptions.",
        cite(2024, 8, "i. Candidates", "ii. Students"),
    )
    add(
        "Simultaneous permissible courses may receive this scholarship for only one course.",
        cite(2024, 8, "ii. Students", "iii. Students"),
    )
    add(
        "Recognized professional or technical courses after undergraduate "
        "examination are permitted if otherwise eligible; correspondence, "
        "distance and continuing education are permitted.",
        cite(2024, 8, "iii. Students", "v. Employed"),
        "interpretation",
    )
    add(
        "Annual parental-income ceiling is Rs 2.5 lakh; the assessment "
        "period and exact income definition require review.",
        cite(2024, 6),
    )
    add(
        "For employed/intern students, their income combined with "
        "parents/guardian income must not exceed the prescribed ceiling; "
        "the 2025 amendment allows all components.",
        school,
    )
    add(
        "Not more than two children with disabilities of the same parents "
        "receive benefits, subject to the second-child twin exception.",
        common,
        subject="household",
    )
    add(
        "Scholarship for a class is available only for one year; repeated "
        "class does not receive a second year.",
        common,
    )
    add("The holder cannot simultaneously receive another scholarship or stipend.", common)
    for text in [
        "Renewal requires good conduct.",
        "Renewal requires regular attendance.",
        "Renewal normally requires promotion within a continuous course; "
        "Post-Matric first failure may be renewed, but later failures are "
        "subject to promotion and own-expense provisions.",
        "Illness or unforeseen-event renewal requires institutional "
        "certification and sufficient proof.",
        "Promotion with a lower-class examination pending may retain the "
        "higher-class award if otherwise eligible.",
    ]:
        add(text, cite(2024, 11, "8. DURATION", "9. OTHER"), "renewal", "renewal")
    add(
        "Fresh cross-state applications are recommended by the State of "
        "study, under the 2025 amendment.",
        cite(2025, 3),
        "procedure",
        "fresh",
    )
    add(
        "Renewals do not require verification from the State Nodal Officer.",
        cite(2025, 3),
        "procedure",
        "renewal",
    )
    add(
        "Fresh selection uses verification, merit and available slots; "
        "satisfying conditions is not a guarantee of selection.",
        cite(2025, 4),
        "selection",
        "fresh",
    )
    docs = [
        "Unique Disability Identity card (UDID)",
        "Aadhaar Card",
        "Photograph",
        "Proof of age",
        "Disability certificate",
        "Income certificate of the parent",
        "Tuition fees receipt",
        "Last academic qualification certificate",
    ]
    documents = [
        DocumentEvidence(
            document=d,
            evidence=school
            if i < 2
            else cite(2024, 10, "b. The applicants", "c. The institutions"),
        )
        for i, d in enumerate(docs)
    ]
    c = CandidateData(
        title="Post-Matric Scholarship for Students with Disabilities",
        summary="Official DEPwD Post-Matric scholarship component, curated from "
        "the captured 2024 guidelines and 2025 amendment. Draft requiring "
        "substantive review; no current application round is asserted.",
        issuer="Department of Empowerment of Persons with Disabilities",
        category="education",
        country="India",
        required_documents=docs,
        document_evidence=documents,
        requirements=req,
        field_evidence=[
            FieldCitation(
                field=f,
                citation=school
                if f in {"title", "summary", "category"}
                else common
                if f == "country"
                else cite(2024, 10)
                if f == "required_documents"
                else cite(2025, 1),
            )
            for f in ["title", "summary", "issuer", "category", "country", "required_documents"]
        ],
        review_flags=[
            "Offline manual curation, not a new AI extraction or live freshness check.",
            "Review source completeness against the official index and any subsequent amendments.",
            "Income definition/assessment period, course exclusions and "
            "renewal exceptions remain unknown pending review.",
            "Disability certificate upload versus amended UDID identity "
            "provision requires reconciliation.",
            "Benefits deliberately omitted pending review of amounts and relevant components.",
            "Source quote presence does not establish semantic completeness.",
            "Selection/slots and administrative verification are not universal"
            " eligibility restrictions.",
        ],
        missing_fields=["opens_on", "closes_on", "apply_url", "benefits"],
    )
    validate_evidence(c, pages)
    return c


def create(session, actor):
    if not actor.is_admin:
        raise ValueError("Administrator required")
    # Reuse the exact capture associated with the original candidate, never a fresh
    # invented snapshot.
    original = session.get(OpportunityVersion, uuid.UUID("9588fed8-1f25-423d-8b5f-890636e68695"))
    snapshot = session.get(SourceSnapshot, original.snapshot_id)
    key = "depwd-post-matric"
    register(session)
    source = session.get(Source, uuid.uuid5(NAMESPACE, key))
    existing = session.scalar(
        select(Opportunity).where(Opportunity.source_id == source.id, Opportunity.source_key == key)
    )
    if existing:
        version = session.scalar(
            select(OpportunityVersion)
            .where(OpportunityVersion.opportunity_id == existing.id)
            .order_by(OpportunityVersion.version.desc())
        )
        if version.snapshot_id == snapshot.id and version.publication_state == "draft":
            copied = SourceSnapshot(
                source_id=source.id,
                content_hash=snapshot.content_hash,
                media_type=snapshot.media_type,
                source_url=snapshot.source_url,
                pages=snapshot.pages,
                byte_count=snapshot.byte_count,
                response_metadata={
                    **snapshot.response_metadata,
                    "reused_capture_id": str(snapshot.id),
                    "original_capture_created_at": snapshot.created_at.isoformat(),
                },
            )
            session.add(copied)
            session.flush()
            version.snapshot_id = copied.id
            for run in session.scalars(
                select(IngestionRun).where(
                    IngestionRun.source_id == source.id, IngestionRun.snapshot_id == snapshot.id
                )
            ):
                run.snapshot_id = copied.id
            session.add(
                AuditEvent(
                    actor_id=actor.id,
                    action="draft_snapshot_association_corrected",
                    object_id=version.id,
                    details={
                        "original_snapshot_id": str(snapshot.id),
                        "snapshot_id": str(copied.id),
                        "source_hash": snapshot.content_hash,
                    },
                )
            )
            session.commit()
        return version
    c = candidate_from(snapshot.pages)
    source.status = "needs_review"
    # Reuse original retrieval dates; do not claim a new successful fetch.
    oldsource = session.get(Source, snapshot.source_id)
    source.last_checked_at = oldsource.last_checked_at
    source.last_successful_check_at = oldsource.last_successful_check_at
    copied = SourceSnapshot(
        source_id=source.id,
        content_hash=snapshot.content_hash,
        media_type=snapshot.media_type,
        source_url=snapshot.source_url,
        pages=snapshot.pages,
        byte_count=snapshot.byte_count,
        response_metadata={
            **snapshot.response_metadata,
            "reused_capture_id": str(snapshot.id),
            "original_capture_created_at": snapshot.created_at.isoformat(),
        },
    )
    session.add(copied)
    session.flush()
    snapshot = copied
    opp = Opportunity(source_id=source.id, source_key=key, category=c.category, is_synthetic=False)
    session.add(opp)
    session.flush()
    v = OpportunityVersion(
        opportunity_id=opp.id,
        version=1,
        snapshot_id=snapshot.id,
        extraction=c.model_dump(mode="json"),
        extraction_provider="manual-curation",
        extractor_version="depwd-post-matric-curation-v1",
        title=c.title,
        summary=c.summary,
        issuer=c.issuer,
        category=c.category,
        country=c.country,
        required_documents=c.required_documents,
        source_url=snapshot.source_url,
        content_hash=snapshot.content_hash,
        publication_state="draft",
        status="needs_review",
    )
    session.add(v)
    session.flush()
    session.add(
        IngestionRun(
            source_id=source.id,
            actor_id=actor.id,
            snapshot_id=snapshot.id,
            status="candidate_curated",
            provider="manual-curation",
            extractor_version=v.extractor_version,
            source_hash=snapshot.content_hash,
            finished_at=datetime.now(timezone.utc),
            diagnostics={
                "method": "existing_official_capture",
                "live_fetch": False,
                "ai_call": False,
            },
        )
    )
    session.add(
        AuditEvent(
            actor_id=actor.id,
            action="candidate_manually_curated",
            object_id=v.id,
            details={"snapshot_id": str(snapshot.id), "content_hash": snapshot.content_hash},
        )
    )
    session.commit()
    review(
        session,
        v.id,
        actor,
        ReviewWrite(
            decision="correct",
            note="Offline source-backed Post-Matric curation. No AI call, no new "
            "live source check, no publication. Human completeness and "
            "semantic review required.",
            expected_hash=digest(v.extraction),
            candidate=c,
        ),
    )
    return v


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor-uid", required=True)
    args = parser.parse_args()
    with Session(engine) as session:
        v = create(session, require_admin(session, args.actor_uid))
        print(
            {"candidate": str(v.id), "state": v.publication_state, "method": v.extraction_provider}
        )
