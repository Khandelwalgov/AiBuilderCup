import uuid
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import Opportunity, OpportunityVersion, Source
from opportunity_platform.opportunities.schemas import (
    Facets,
    OpportunityPage,
    OpportunityView,
    SourceView,
)


def catalogue():
    latest = (
        select(
            OpportunityVersion.opportunity_id, func.max(OpportunityVersion.version).label("latest")
        )
        .group_by(OpportunityVersion.opportunity_id)
        .subquery()
    )
    return (
        select(Opportunity, OpportunityVersion, Source)
        .join(OpportunityVersion, Opportunity.id == OpportunityVersion.opportunity_id)
        .join(
            latest,
            (latest.c.opportunity_id == Opportunity.id)
            & (latest.c.latest == OpportunityVersion.version),
        )
        .join(Source, Source.id == Opportunity.source_id)
    )


def view(row) -> OpportunityView:
    opportunity, version, source = row
    fields = {
        name: getattr(version, name)
        for name in OpportunityView.model_fields
        if hasattr(version, name)
    }
    fields.update(
        id=opportunity.id,
        category=opportunity.category,
        is_synthetic=opportunity.is_synthetic,
        first_seen_at=opportunity.created_at,
        source=SourceView.model_validate(source, from_attributes=True),
    )
    return OpportunityView(**fields)


def browse(
    session: Session,
    q: str | None,
    category: str | None,
    state: str | None,
    district: str | None,
    issuer: str | None,
    status: str | None,
    deadline_before: date | None,
    cursor: uuid.UUID | None,
    limit: int,
) -> OpportunityPage:
    query = catalogue()
    if q:
        escaped = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(
            or_(
                OpportunityVersion.title.ilike(f"%{escaped}%", escape="\\"),
                OpportunityVersion.summary.ilike(f"%{escaped}%", escape="\\"),
            )
        )
    for column, value in [
        (Opportunity.category, category),
        (OpportunityVersion.state, state),
        (OpportunityVersion.district, district),
        (OpportunityVersion.issuer, issuer),
        (OpportunityVersion.status, status),
    ]:
        if value is not None:
            query = query.where(column == value)
    if deadline_before:
        query = query.where(OpportunityVersion.closes_on <= deadline_before)
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    if cursor:
        query = query.where(Opportunity.id > cursor)
    rows = session.execute(query.order_by(Opportunity.id).limit(limit + 1)).all()
    return OpportunityPage(
        items=[view(row) for row in rows[:limit]],
        total=total,
        next_cursor=str(rows[limit - 1][0].id) if len(rows) > limit else None,
    )


def detail(session: Session, identifier: uuid.UUID) -> OpportunityView:
    row = session.execute(catalogue().where(Opportunity.id == identifier)).first()
    if row is None:
        raise APIError(404, "opportunity_not_found", "This opportunity could not be found.")
    return view(row)


def facets(session: Session) -> Facets:
    rows = session.execute(catalogue()).all()
    return Facets(
        categories=sorted({o.category for o, _, _ in rows}),
        states=sorted({v.state for _, v, _ in rows if v.state}),
        districts=sorted({v.district for _, v, _ in rows if v.district}),
        total=len(rows),
        synthetic=sum(o.is_synthetic for o, _, _ in rows),
        verified=sum(v.status == "verified" and not o.is_synthetic for o, v, _ in rows),
        official_sources=len(
            {
                s.id
                for o, v, s in rows
                if not s.is_synthetic and not o.is_synthetic and v.status == "verified"
            }
        ),
    )
