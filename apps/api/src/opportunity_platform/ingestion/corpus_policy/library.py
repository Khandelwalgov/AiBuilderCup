"""Public government snapshots only. Private user evidence is never queried here."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import Text, func, select
from sqlalchemy.orm import Session

from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import (
    IngestionRun,
    Opportunity,
    OpportunityVersion,
    Source,
    SourceSnapshot,
)
from opportunity_platform.db.session import get_session

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


class GovernmentSourcePage(BaseModel):
    items: list[GovernmentSource]
    total: int
    next_cursor: uuid.UUID | None


class GovernmentTextPage(BaseModel):
    page: int
    text: str
    source_url: str


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


def entry(snapshot, source, related, processing_status=None):
    metadata = snapshot.response_metadata
    audit = metadata.get("quality_audit", {})
    discoveries = metadata.get("discoveries", [])
    return GovernmentSource(
        id=snapshot.id,
        title=source.name,
        department=source.authority,
        source_url=snapshot.source_url,
        content_hash=snapshot.content_hash,
        format="pdf" if snapshot.media_type == "application/pdf" else "html",
        captured_at=metadata.get("captured_at"),
        document_type=audit.get("document_type", "unclassified"),
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
            if audit.get("needs_ocr")
            else "processing_pending"
        ),
        needs_ocr=bool(audit.get("needs_ocr")),
        related_opportunities=related,
        page_count=len(snapshot.pages),
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


@router.get("", response_model=GovernmentSourcePage)
def browse(
    session: DB,
    q: Annotated[str, Query(max_length=200)] = "",
    department: Annotated[str, Query(max_length=200)] = "",
    category: Annotated[str, Query(max_length=80)] = "",
    state: Annotated[str, Query(max_length=80)] = "",
    document_type: Annotated[str, Query(max_length=80)] = "",
    format: Annotated[str, Query(pattern="^(pdf|html)?$")] = "",
    review_state: Literal[
        "", "processing_pending", "needs_ocr", "human_review_pending", "reviewed_and_published"
    ] = "",
    opportunity_id: uuid.UUID | None = None,
    cursor: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 12,
):
    query = base_query()
    published = (
        select(OpportunityVersion.id)
        .join(Opportunity, Opportunity.published_version_id == OpportunityVersion.id)
        .where(
            OpportunityVersion.snapshot_id == SourceSnapshot.id,
            OpportunityVersion.publication_state == "published",
            OpportunityVersion.status == "verified",
            Opportunity.is_synthetic.is_(False),
        )
    )
    pending = (
        select(IngestionRun.id)
        .where(
            IngestionRun.snapshot_id == SourceSnapshot.id,
            IngestionRun.status.in_(["human_escalation", "draft_for_human_review"]),
        )
        .exists()
    )
    needs_ocr = (
        SourceSnapshot.response_metadata["quality_audit"]["needs_ocr"].as_boolean().is_(True)
    )
    if opportunity_id:
        query = query.where(published.where(Opportunity.id == opportunity_id).exists())
    if review_state:
        if review_state == "reviewed_and_published":
            query = query.where(published.exists())
        else:
            query = query.where(~published.exists())
            if review_state == "human_review_pending":
                query = query.where(pending)
            elif review_state == "needs_ocr":
                query = query.where(~pending, needs_ocr)
            else:
                query = query.where(~pending, ~needs_ocr)
    if q.strip():
        # Literal escaped terms; public normalized text only, never user documents.
        term = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        query = query.where(
            Source.name.ilike(term, escape="\\")
            | SourceSnapshot.pages.cast(Text).ilike(term, escape="\\")
        )
    if department:
        query = query.where(Source.authority == department)
    if document_type:
        query = query.where(
            SourceSnapshot.response_metadata["quality_audit"]["document_type"].as_string()
            == document_type
        )
    if format:
        query = query.where(
            SourceSnapshot.media_type == ("application/pdf" if format == "pdf" else "text/html")
        )
    if category or state:
        # Registry discovery metadata is captured provenance, not verified applicability.
        from sqlalchemy.dialects.postgresql import JSONB

        for key, value in [("document_category", category), ("jurisdiction", state)]:
            if value:
                query = query.where(
                    SourceSnapshot.response_metadata["discoveries"]
                    .cast(JSONB)
                    .contains([{key: value}])
                )
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    if cursor:
        query = query.where(SourceSnapshot.id > cursor)
    rows = session.execute(query.order_by(SourceSnapshot.id).limit(limit + 1)).all()
    relations = published_relations(session, [snapshot.id for snapshot, _ in rows])
    statuses = {
        run.snapshot_id: run.status
        for run in session.scalars(
            select(IngestionRun)
            .where(IngestionRun.snapshot_id.in_([snapshot.id for snapshot, _ in rows]))
            .order_by(IngestionRun.created_at)
        )
    }
    return GovernmentSourcePage(
        items=[
            entry(s, source, relations.get(s.id, []), statuses.get(s.id))
            for s, source in rows[:limit]
        ],
        total=total,
        next_cursor=rows[limit - 1][0].id if len(rows) > limit else None,
    )


@router.get("/{identifier}", response_model=GovernmentSourceDetail)
def detail(identifier: uuid.UUID, session: DB):
    row = session.execute(base_query().where(SourceSnapshot.id == identifier)).first()
    if row is None:
        raise APIError(404, "government_source_not_found", "Public government source not found.")
    snapshot, source = row
    status = session.scalar(
        select(IngestionRun.status)
        .where(IngestionRun.snapshot_id == identifier)
        .order_by(IngestionRun.created_at.desc())
        .limit(1)
    )
    value = entry(
        snapshot, source, published_relations(session, [identifier]).get(identifier, []), status
    )
    return GovernmentSourceDetail(
        **value.model_dump(),
        pages=[
            GovernmentTextPage(page=p["page"], text=p["text"], source_url=p["source_url"])
            for p in snapshot.pages
        ],
    )
