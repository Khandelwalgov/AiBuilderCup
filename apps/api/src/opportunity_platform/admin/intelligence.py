"""Aggregate public-corpus/worker status. No private profile/document queries."""

from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import func, select

from opportunity_platform.db.models import (
    InferenceReservation,
    IngestionRun,
    Opportunity,
    OpportunityVersion,
    ResearchListing,
)
from opportunity_platform.ingestion.corpus_policy.contracts import VERSION
from opportunity_platform.ingestion.corpus_policy.library import catalogue_entries


class IntelligenceStatus(BaseModel):
    public_research_listings: int = 0
    draft_opportunity_identities: int = 0
    documents_with_ocr: int = 0
    text_states: dict[str, int] = {}
    review_states: dict[str, int] = {}
    captured_snapshot_rows: int
    unique_document_hashes: int
    documents_requiring_ocr: int
    processing_backlog: int
    draft_opportunities: int
    human_escalations: int
    independently_verified_candidates: int
    published_real_opportunities: int
    last_successful_collection: str | None
    reserved_inference_usd: float
    recorded_inference_usd: float
    inference_requests_reserved: int


def status(session):
    entries = catalogue_entries(session)
    snapshots = [snapshot for snapshot, _, _ in entries]
    versions = list(
        session.execute(
            select(OpportunityVersion.snapshot_id, OpportunityVersion.publication_state).where(
                OpportunityVersion.snapshot_id.in_([s.id for s in snapshots]),
            )
        )
    )
    runs = list(
        session.scalars(
            select(IngestionRun).where(
                IngestionRun.diagnostics["origin"].as_string() == VERSION,
            )
        )
    )
    independently_verified = 0
    for run in runs:
        stages = (run.diagnostics or {}).get("workflow", {}).get("stages", [])
        review = stages[-1].get("independent_review") if stages else None
        findings = (review or {}).get("findings", [])
        if (
            run.status == "draft_for_human_review"
            and findings
            and all(f["assessment"] == "supported" for f in findings)
        ):
            independently_verified += 1
    processed = {v.snapshot_id for v in versions}
    processed_hashes = {s.content_hash for s in snapshots if s.id in processed}
    published = (
        session.scalar(
            select(func.count())
            .select_from(Opportunity)
            .join(
                OpportunityVersion,
                Opportunity.published_version_id == OpportunityVersion.id,
            )
            .where(
                Opportunity.is_synthetic.is_(False),
                OpportunityVersion.publication_state == "published",
                OpportunityVersion.status == "verified",
            )
        )
        or 0
    )
    last = session.scalar(
        select(func.max(IngestionRun.finished_at)).where(
            IngestionRun.provider == "offline_collector",
            IngestionRun.status == "collection_completed",
        )
    )
    reserved, recorded, requests = session.execute(
        select(
            func.coalesce(func.sum(InferenceReservation.reserved_usd), Decimal(0)),
            func.coalesce(func.sum(InferenceReservation.recorded_usd), Decimal(0)),
            func.count(InferenceReservation.id),
        )
    ).one()
    from collections import Counter

    return IntelligenceStatus(
        public_research_listings=session.scalar(
            select(func.count())
            .select_from(ResearchListing)
            .where(ResearchListing.is_public.is_(True))
        )
        or 0,
        draft_opportunity_identities=session.scalar(
            select(func.count(func.distinct(OpportunityVersion.opportunity_id))).where(
                OpportunityVersion.publication_state == "draft",
                OpportunityVersion.snapshot_id.in_([s.id for s in snapshots]),
            )
        )
        or 0,
        documents_with_ocr=len(
            {snapshot.content_hash for snapshot, _, item in entries if item.ocr_pages}
        ),
        text_states=dict(Counter(item.text_state for _, _, item in entries)),
        review_states=dict(Counter(item.review_state for _, _, item in entries)),
        captured_snapshot_rows=len(snapshots),
        unique_document_hashes=len({s.content_hash for s in snapshots}),
        documents_requiring_ocr=len(
            {snapshot.content_hash for snapshot, _, item in entries if item.unreadable_pages}
        ),
        processing_backlog=len({s.content_hash for s in snapshots} - processed_hashes),
        draft_opportunities=sum(v.publication_state == "draft" for v in versions),
        human_escalations=sum(r.status == "human_escalation" for r in runs),
        independently_verified_candidates=independently_verified,
        published_real_opportunities=published,
        last_successful_collection=last.isoformat() if last else None,
        reserved_inference_usd=float(reserved),
        recorded_inference_usd=float(recorded),
        inference_requests_reserved=requests,
    )
