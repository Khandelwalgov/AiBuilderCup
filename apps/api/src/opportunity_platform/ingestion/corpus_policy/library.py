"""Public government snapshots only. Private user evidence is never queried here."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import (
    IngestionRun,
    Opportunity,
    OpportunityVersion,
    ResearchListing,
    Source,
    SourceSnapshot,
)
from opportunity_platform.db.session import get_session
from opportunity_platform.research.integration import integrated_pages, source_overlays

from .contracts import VERSION

router = APIRouter(prefix="/v1/government-sources", tags=["public government sources"])
DB = Annotated[Session, Depends(get_session)]


class GovernmentSource(BaseModel):
    id: uuid.UUID
    title: str
    department: str | None
    source_url: str
    content_hash: str
    format: str
    captured_at: str | None
    document_type: str
    categories: list[str]
    jurisdictions: list[str]
    review_state: str
    needs_ocr: bool
    related_opportunities: list[uuid.UUID]
    page_count: int
    ocr_pages: int = 0
    unreadable_pages: list[int] = []
    review_required_pages: list[int] = []
    text_state: str = "text_available"
    related_research: list[uuid.UUID] = []
    attribution_evidence: dict | None = None
    title_evidence: dict | None = None


class GovernmentSourcePage(BaseModel):
    all_capture_records: int = 0
    all_unique_document_hashes: int = 0
    public_research_listings: int = 0
    unpublished_eligibility_versions: int = 0
    published_eligibility_policies: int = 0
    items: list[GovernmentSource]
    total: int
    next_cursor: uuid.UUID | None


class GovernmentTextPage(BaseModel):
    page: int
    text: str
    source_url: str
    basis: str = "original_extracted_text"
    readability: str = "readable"
    text_sha256: str | None = None
    image_sha256: str | None = None
    mean_word_confidence: float | None = None
    acquisition_snapshot_id: str | None = None
    original_text: str | None = None


class GovernmentSourceDetail(GovernmentSource):
    pages: list[GovernmentTextPage]
    notice: str = "Captured public source, not an approved opportunity or entitlement."


def base_query():
    return (
        select(SourceSnapshot, Source)
        .join(Source)
        .where(
            Source.is_synthetic.is_(False),
            SourceSnapshot.response_metadata["origin"]
            .as_string()
            .in_([VERSION, "research-catalogue-v1"]),
        )
    )


def entry(snapshot, source, related, processing_status=None, research=None):
    metadata = snapshot.response_metadata
    audit = metadata.get("quality_audit", {})
    discoveries = metadata.get("discoveries", [])
    overlay = source_overlays().get(snapshot.content_hash, {})
    pages = integrated_pages(snapshot)
    unreadable = [p["page"] for p in pages if p["readability"] == "unreadable"]
    flagged = [p["page"] for p in pages if p["readability"] == "needs_review"]
    text_state = (
        "unreadable"
        if len(unreadable) == len(pages)
        else "partial_text"
        if unreadable or flagged
        else "text_available"
    )
    issuer = overlay.get("issuer")
    title = overlay.get("title")
    return GovernmentSource(
        id=snapshot.id,
        title=title["value"] if title else source.name,
        department=issuer["value"] if issuer else source.authority,
        source_url=snapshot.source_url,
        content_hash=snapshot.content_hash,
        format="pdf" if snapshot.media_type == "application/pdf" else "html",
        captured_at=metadata.get("captured_at"),
        document_type=overlay.get("document_type", audit.get("document_type", "unclassified")),
        categories=sorted(
            {d["document_category"] for d in discoveries if d.get("document_category")}
        ),
        jurisdictions=sorted(
            {d["jurisdiction"] for d in discoveries if isinstance(d.get("jurisdiction"), str)}
        ),
        review_state="reviewed_and_published"
        if related
        else (
            "human_review_pending"
            if processing_status in {"human_escalation", "draft_for_human_review"}
            else "needs_ocr"
            if unreadable
            else "processing_pending"
        ),
        needs_ocr=bool(unreadable),
        related_opportunities=related,
        page_count=len(snapshot.pages),
        ocr_pages=sum(p["basis"] == "offline_ocr" for p in pages),
        unreadable_pages=unreadable,
        review_required_pages=flagged,
        text_state=text_state,
        related_research=research or [],
        attribution_evidence=issuer,
        title_evidence=title,
    )


def published_relations(session, ids):
    result = {}
    for snapshot_id, opportunity_id in session.execute(
        select(
            OpportunityVersion.snapshot_id,
            Opportunity.id,
        )
        .join(Opportunity, Opportunity.published_version_id == OpportunityVersion.id)
        .where(
            OpportunityVersion.snapshot_id.in_(ids),
            OpportunityVersion.publication_state == "published",
            OpportunityVersion.status == "verified",
            Opportunity.is_synthetic.is_(False),
        )
    ):
        result.setdefault(snapshot_id, []).append(opportunity_id)
    return result


def catalogue_entries(session):
    rows = session.execute(base_query().order_by(SourceSnapshot.id)).all()
    ids = [row[0].id for row in rows]
    relations = published_relations(session, ids)
    statuses = {
        run.snapshot_id: run.status
        for run in session.scalars(
            select(IngestionRun)
            .where(IngestionRun.snapshot_id.in_(ids))
            .order_by(IngestionRun.created_at, IngestionRun.id)
        )
    }
    for snapshot_id in session.scalars(
        select(OpportunityVersion.snapshot_id).where(
            OpportunityVersion.snapshot_id.in_(ids),
            OpportunityVersion.publication_state == "draft",
        )
    ):
        statuses[snapshot_id] = "draft_for_human_review"
    research = {}
    for row in session.scalars(select(ResearchListing).where(ResearchListing.is_public.is_(True))):
        for source in row.payload["sources"]:
            research.setdefault(uuid.UUID(source["snapshot_id"]), []).append(row.id)
    return [
        (
            snapshot,
            source,
            entry(
                snapshot,
                source,
                relations.get(snapshot.id, []),
                statuses.get(snapshot.id),
                research.get(snapshot.id, []),
            ),
        )
        for snapshot, source in rows
    ]


@router.get("", response_model=GovernmentSourcePage)
def browse(
    session: DB,
    q: Annotated[str, Query(max_length=200)] = "",
    department: Annotated[str, Query(max_length=200)] = "",
    category: Annotated[str, Query(max_length=80)] = "",
    state: Annotated[str, Query(max_length=80)] = "",
    document_type: Annotated[str, Query(max_length=80)] = "",
    format: Literal["", "pdf", "html"] = "",
    review_state: Literal[
        "", "processing_pending", "needs_ocr", "human_review_pending", "reviewed_and_published"
    ] = "",
    text_state: Literal["", "text_available", "partial_text", "unreadable"] = "",
    opportunity_id: uuid.UUID | None = None,
    cursor: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 12,
):
    # This small captured corpus uses exactly the same display values for filters and cards.
    values = []
    entries = catalogue_entries(session)
    for snapshot, source, item in entries:
        if department and department.casefold() not in (item.department or "").casefold():
            continue
        if any(
            value and actual != value
            for actual, value in [
                (item.document_type, document_type),
                (item.format, format),
                (item.review_state, review_state),
                (item.text_state, text_state),
            ]
        ):
            continue
        if (
            category
            and category not in item.categories
            or state
            and state not in item.jurisdictions
        ):
            continue
        if opportunity_id and opportunity_id not in item.related_opportunities:
            continue
        if q.strip():
            haystack = "\n".join(
                [
                    item.title,
                    item.department or "",
                    *(p["text"] for p in integrated_pages(snapshot)),
                ]
            )
            if q.strip().casefold() not in haystack.casefold():
                continue
        values.append(item)
    total = len(values)
    if cursor:
        values = [item for item in values if item.id.int > cursor.int]
    return GovernmentSourcePage(
        all_capture_records=len(entries),
        all_unique_document_hashes=len({snapshot.content_hash for snapshot, _, _ in entries}),
        public_research_listings=len(
            {identifier for _, _, item in entries for identifier in item.related_research}
        ),
        unpublished_eligibility_versions=session.scalar(
            select(func.count())
            .select_from(OpportunityVersion)
            .where(
                OpportunityVersion.snapshot_id.in_([snapshot.id for snapshot, _, _ in entries]),
                OpportunityVersion.publication_state == "draft",
            )
        )
        or 0,
        published_eligibility_policies=len(
            {identifier for _, _, item in entries for identifier in item.related_opportunities}
        ),
        items=values[:limit],
        total=total,
        next_cursor=values[limit - 1].id if len(values) > limit else None,
    )


@router.get("/{identifier}", response_model=GovernmentSourceDetail)
def detail(identifier: uuid.UUID, session: DB):
    row = session.execute(base_query().where(SourceSnapshot.id == identifier)).first()
    if row is None:
        raise APIError(404, "government_source_not_found", "Public government source not found.")
    snapshot, source = row
    value = next(item for _, _, item in catalogue_entries(session) if item.id == identifier)
    return GovernmentSourceDetail(
        **value.model_dump(),
        pages=[GovernmentTextPage(**p) for p in integrated_pages(snapshot)],
    )
