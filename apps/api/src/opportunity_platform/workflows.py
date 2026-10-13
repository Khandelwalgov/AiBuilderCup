"""HTTP adapter only; all persistence and evaluation stay in domain services."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from opportunity_platform.admin import service as admin
from opportunity_platform.core.auth import current_uid
from opportunity_platform.core.errors import APIError
from opportunity_platform.db.models import IngestionRun, OpportunityVersion, Source, User
from opportunity_platform.db.session import get_session
from opportunity_platform.eligibility import service as eligibility
from opportunity_platform.ingestion import service as ingestion
from opportunity_platform.ingestion.adapters import ADAPTERS
from opportunity_platform.profiles import service as profiles

router = APIRouter(prefix="/v1")
DB = Annotated[Session, Depends(get_session)]
UID = Annotated[str, Depends(current_uid)]


def administrator(session: DB, uid: UID):
    return profiles.require_admin(session, uid)


ADMIN = Annotated[User, Depends(administrator)]


@router.get("/profile/me", response_model=profiles.ProfileView)
def get_profile(session: DB, uid: UID):
    return profiles.get_profile(session, uid)


@router.put("/profile/me", response_model=profiles.ProfileView)
def save_profile(data: profiles.ProfileWrite, session: DB, uid: UID):
    return profiles.save_profile(session, uid, data)


@router.get("/people/{identifier}", response_model=profiles.ProfileView)
def get_person(identifier: uuid.UUID, session: DB, uid: UID):
    profile = profiles.get_profile(session, uid)
    if profile.id != identifier:
        raise APIError(404, "profile_not_found", "This profile could not be found.")
    return profile


@router.post("/opportunities/{identifier}/evaluate", response_model=eligibility.EvaluationView)
def evaluate(identifier: uuid.UUID, session: DB, uid: UID):
    return eligibility.check(session, uid, identifier)


@router.get("/admin/reviews", response_model=list[admin.ReviewSummary])
def reviews(session: DB, actor: ADMIN, limit: Annotated[int, Query(ge=1, le=100)] = 50):
    return [
        admin.summary(v)
        for v in session.scalars(
            select(OpportunityVersion)
            .where(
                OpportunityVersion.publication_state == "draft",
                OpportunityVersion.extraction.is_not(None),
            )
            .order_by(OpportunityVersion.created_at)
            .limit(limit)
        )
    ]


@router.get("/admin/reviews/{identifier}", response_model=admin.ReviewView)
def get_review(identifier: uuid.UUID, session: DB, actor: ADMIN):
    return admin.read(session, identifier)


@router.post("/admin/reviews/{identifier}", response_model=admin.ReviewView)
def review(identifier: uuid.UUID, data: admin.ReviewWrite, session: DB, actor: ADMIN):
    return admin.review(session, identifier, actor, data)


class SourceItem(BaseModel):
    key: str
    name: str
    url: str
    context_url: str
    last_checked_at: str | None
    status: str


@router.get("/admin/sources", response_model=list[SourceItem])
def sources(session: DB, actor: ADMIN):
    result = []
    for key, adapter in ADAPTERS.items():
        source = session.get(Source, uuid.uuid5(ingestion.NAMESPACE, key))
        result.append(
            SourceItem(
                key=key,
                name=adapter.name,
                url=adapter.url,
                context_url=adapter.context_url,
                last_checked_at=source.last_checked_at.isoformat()
                if source and source.last_checked_at
                else None,
                status=source.status if source else "not_registered",
            )
        )
    return result


class RunView(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    snapshot_id: uuid.UUID | None
    status: str
    diagnostic_code: str | None
    model: str | None
    changed: bool | None
    created_at: str
    finished_at: str | None
    http_status: int | None


def run_view(run):
    fields = {key: getattr(run, key) for key in RunView.model_fields}
    fields.update(
        created_at=run.created_at.isoformat(),
        finished_at=run.finished_at.isoformat() if run.finished_at else None,
    )
    return RunView(**fields)


@router.post("/admin/sources/{key}/ingest", response_model=RunView)
def ingest(key: str, session: DB, actor: ADMIN):
    return run_view(ingestion.ingest(session, key, actor))


@router.get("/admin/ingestion-runs", response_model=list[RunView])
def runs(session: DB, actor: ADMIN, limit: Annotated[int, Query(ge=1, le=100)] = 30):
    return [
        run_view(run)
        for run in session.scalars(
            select(IngestionRun).order_by(IngestionRun.created_at.desc()).limit(limit)
        )
    ]
