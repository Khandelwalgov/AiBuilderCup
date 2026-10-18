import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import Date, and_, case, select
from sqlalchemy.orm import Session

from opportunity_platform.core.auth import current_uid
from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import ResearchListing
from opportunity_platform.db.session import get_session

from .discovery import DiscoveryResponse, discover
from .guidance import GuidanceRequest
from .integration import quality
from .schemas import (
    ApplicationStatus,
    Availability,
    ResearchCard,
    ResearchDetail,
    ResearchFacets,
    ResearchInput,
    ResearchResults,
)

router = APIRouter(prefix="/v1/research-opportunities", tags=["source-backed research catalogue"])
DB = Annotated[Session, Depends(get_session)]


CATEGORY_ORDER = {
    "education": 0,
    "welfare": 1,
    "healthcare": 2,
    "business": 3,
    "employment": 4,
    "procurement": 5,
}


def current_day():
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).date()


def effective_fields():
    ended = and_(
        ResearchListing.application_status == "open",
        ResearchListing.payload["closes_on"].as_string().cast(Date) < current_day(),
    )
    return (
        case((ended, "historical"), else_=ResearchListing.availability),
        case((ended, "closed"), else_=ResearchListing.application_status),
    )


def card(row):
    data = ResearchInput.model_validate(row.payload)
    values = data.model_dump(exclude={"sources", "citations", "limitations"})
    # A dated window must never stay labelled open after its cited closing date.
    if data.closes_on and data.closes_on < current_day() and data.application_status == "open":
        values.update(application_status="closed", availability="historical")
    return ResearchCard(
        id=row.id,
        source_url=data.sources[0].source_url,
        source_count=len(data.sources),
        evidence_strength=quality(row).get("evidence_strength", "unassessed"),
        archive=quality(row).get(
            "archive", data.kind == "tender" or data.availability == "historical"
        ),
        documents=[
            {
                "snapshot_id": source.snapshot_id,
                "source_url": source.source_url,
                "content_hash": source.content_hash,
                "pages": sorted(
                    {c.page for c in data.citations if c.snapshot_id == source.snapshot_id}
                ),
                "excerpt": next(
                    c.passage for c in data.citations if c.snapshot_id == source.snapshot_id
                )[:320],
                "basis": "offline_ocr"
                if any(p.basis == "offline_ocr" for p in source.pages)
                else "original_extracted_text",
            }
            for source in data.sources
        ],
        **values,
    )


@router.get("", response_model=ResearchResults)
def browse(
    session: DB,
    view: Literal["catalogue", "archive", "all"] = "catalogue",
    q: Annotated[str, Query(max_length=200)] = "",
    category: Annotated[str, Query(max_length=80)] = "",
    jurisdiction: Annotated[str, Query(max_length=80)] = "",
    availability: Availability | None = None,
    application_status: ApplicationStatus | None = None,
    cursor: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 12,
):
    query = select(ResearchListing).where(ResearchListing.is_public.is_(True))
    effective_availability, effective_application = effective_fields()
    for column, value in [
        (ResearchListing.category, category),
        (ResearchListing.jurisdiction, jurisdiction),
        (effective_availability, availability),
        (effective_application, application_status),
    ]:
        if value:
            query = query.where(column == value)
    rows = list(session.scalars(query))

    def rank(row):
        audit = quality(row)
        strength = {
            "substantive_document": 0,
            "source_overview": 1,
            "procurement_notice": 1,
            "charter_summary": 2,
            "directory_reference": 3,
        }.get(audit.get("evidence_strength"), 4)
        return (
            strength,
            row.payload.get("kind") != "scheme",
            CATEGORY_ORDER.get(row.category, 9),
            row.title,
            row.id.int,
        )

    from .search import rank as search_rank

    scores, neural_status = search_rank(rows, q)
    if q.strip():
        rows = [r for r in rows if str(r.id) in scores]
    rows.sort(key=lambda row: (-scores.get(str(row.id), 0), *rank(row)))
    if view != "all":
        rows = [r for r in rows if card(r).archive == (view == "archive")]
    total = len(rows)
    if cursor:
        index = next((i for i, row in enumerate(rows) if row.id == cursor), None)
        if index is None:
            raise APIError(422, "invalid_research_cursor", "This catalogue cursor is unavailable.")
        rows = rows[index + 1 :]
    return ResearchResults(
        items=[card(r) for r in rows[:limit]],
        neural_status=neural_status,
        total=total,
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


@router.get("/facets", response_model=ResearchFacets)
def facets(session: DB):
    rows = list(session.scalars(select(ResearchListing).where(ResearchListing.is_public.is_(True))))
    return ResearchFacets(
        total=len(rows),
        catalogue_total=sum(not card(r).archive for r in rows),
        archive_total=sum(card(r).archive for r in rows),
        evidence_strengths=dict(Counter(card(r).evidence_strength for r in rows)),
        kinds=dict(Counter(r.payload["kind"] for r in rows)),
        categories=sorted({r.category for r in rows}),
        jurisdictions=sorted({r.jurisdiction for r in rows}),
        availability=dict(Counter(card(r).availability for r in rows)),
        application_status=dict(Counter(card(r).application_status for r in rows)),
        source_documents=len({str(s["snapshot_id"]) for r in rows for s in r.payload["sources"]}),
    )


@router.post("/guidance", response_model=DiscoveryResponse)
def personalized_research(
    body: GuidanceRequest,
    session: DB,
    uid: Annotated[str, Depends(current_uid)],
    response: Response,
):
    """Private geographic research guidance, never an eligibility determination."""

    response.headers["Cache-Control"] = "private, no-store"
    result = discover(session, uid, body)
    session.rollback()
    return result


@router.post("/plan", response_model=DiscoveryResponse)
def research_plan(
    body: GuidanceRequest,
    session: DB,
    uid: Annotated[str, Depends(current_uid)],
    response: Response,
):
    from opportunity_platform.planning.service import research_actions

    response.headers["Cache-Control"] = "private, no-store"
    result = discover(session, uid, body)
    result.actions = research_actions(session, uid, body, persist=not result.hypothetical)
    return result


@router.get("/{identifier}", response_model=ResearchDetail)
def detail(identifier: uuid.UUID, session: DB):
    row = session.scalar(
        select(ResearchListing).where(
            ResearchListing.id == identifier, ResearchListing.is_public.is_(True)
        )
    )
    if row is None:
        raise APIError(404, "research_listing_not_found", "This research listing is unavailable.")
    data = ResearchInput.model_validate(row.payload)
    from .conditions import SourceCondition, compare

    return ResearchDetail(
        **card(row).model_dump(),
        limitations=data.limitations,
        sources=data.sources,
        citations=data.citations,
        provisional_conditions=[
            SourceCondition.model_validate(c.model_dump()) for c in compare(session, row, [], [])
        ],
    )
