import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Date, and_, case, func, or_, select
from sqlalchemy.orm import Session

from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import ResearchListing
from opportunity_platform.db.session import get_session

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
        id=row.id, source_url=data.sources[0].source_url, source_count=len(data.sources), **values
    )


@router.get("", response_model=ResearchResults)
def browse(
    session: DB,
    q: Annotated[str, Query(max_length=200)] = "",
    category: Annotated[str, Query(max_length=80)] = "",
    jurisdiction: Annotated[str, Query(max_length=80)] = "",
    availability: Availability | None = None,
    application_status: ApplicationStatus | None = None,
    cursor: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 12,
):
    query = select(ResearchListing).where(ResearchListing.is_public.is_(True))
    if q.strip():
        term = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        query = query.where(
            or_(
                *(
                    field.ilike(term, escape="\\")
                    for field in [
                        ResearchListing.title,
                        ResearchListing.summary,
                        ResearchListing.search_text,
                        ResearchListing.authority,
                    ]
                )
            )
        )
    effective_availability, effective_application = effective_fields()
    category_rank = case(CATEGORY_ORDER, value=ResearchListing.category, else_=9)
    for column, value in [
        (ResearchListing.category, category),
        (ResearchListing.jurisdiction, jurisdiction),
        (effective_availability, availability),
        (effective_application, application_status),
    ]:
        if value:
            query = query.where(column == value)
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    if cursor:
        previous = session.scalar(
            select(ResearchListing).where(
                ResearchListing.id == cursor, ResearchListing.is_public.is_(True)
            )
        )
        if previous is None:
            raise APIError(422, "invalid_research_cursor", "This catalogue cursor is unavailable.")
        rank = CATEGORY_ORDER.get(previous.category, 9)
        query = query.where(
            or_(
                category_rank > rank,
                and_(category_rank == rank, ResearchListing.title > previous.title),
                and_(
                    category_rank == rank,
                    ResearchListing.title == previous.title,
                    ResearchListing.id > cursor,
                ),
            )
        )
    rows = list(
        session.scalars(
            query.order_by(category_rank, ResearchListing.title, ResearchListing.id).limit(
                limit + 1
            )
        )
    )
    return ResearchResults(
        items=[card(row) for row in rows[:limit]],
        total=total,
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


@router.get("/facets", response_model=ResearchFacets)
def facets(session: DB):
    rows = list(session.scalars(select(ResearchListing).where(ResearchListing.is_public.is_(True))))
    return ResearchFacets(
        total=len(rows),
        categories=sorted({r.category for r in rows}),
        jurisdictions=sorted({r.jurisdiction for r in rows}),
        availability=dict(Counter(card(r).availability for r in rows)),
        application_status=dict(Counter(card(r).application_status for r in rows)),
        source_documents=len({str(s["snapshot_id"]) for r in rows for s in r.payload["sources"]}),
    )


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
    return ResearchDetail(
        **card(row).model_dump(),
        limitations=data.limitations,
        sources=data.sources,
        citations=data.citations,
    )
