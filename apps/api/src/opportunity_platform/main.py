import json
import logging
import time
import uuid
from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from opportunity_platform.core.auth import current_uid
from opportunity_platform.core.config import settings
from opportunity_platform.core.errors import APIError, ErrorEnvelope, response
from opportunity_platform.db.session import get_session
from opportunity_platform.documents.router import router as documents_router
from opportunity_platform.ingestion.corpus_policy.library import router as government_sources_router
from opportunity_platform.opportunities import service
from opportunity_platform.opportunities.schemas import (
    Facets,
    OpportunityPage,
    OpportunityView,
    Status,
)
from opportunity_platform.profiles.service import AccountView, account
from opportunity_platform.retrieval.router import router as retrieval_router
from opportunity_platform.workflows import router

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("opportunity")
app = FastAPI(
    title="Opportunity Intelligence API",
    version="0.1.0",
    responses={
        403: {"model": ErrorEnvelope},
        409: {"model": ErrorEnvelope},
        429: {"model": ErrorEnvelope},
        401: {"model": ErrorEnvelope},
        404: {"model": ErrorEnvelope},
        422: {"model": ErrorEnvelope},
        503: {"model": ErrorEnvelope},
    },
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Document-Access"],
)
DB = Annotated[Session, Depends(get_session)]


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    start = time.monotonic()
    result = await call_next(request)
    result.headers["X-Request-ID"] = request.state.request_id
    if request.url.path.startswith("/v1/documents"):
        result.headers["Cache-Control"] = "private, no-store"
        result.headers["X-Content-Type-Options"] = "nosniff"
        result.headers["Referrer-Policy"] = "no-referrer"
    logger.info(
        json.dumps(
            {
                "event": "http_request",
                "request_id": request.state.request_id,
                "method": request.method,
                "status": result.status_code,
                "duration_ms": round((time.monotonic() - start) * 1000),
            }
        )
    )
    return result


@app.exception_handler(APIError)
async def api_error(request: Request, error: APIError):
    return response(request, error.status, error.code, error.message, issues=error.issues)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError):
    # Return allowlisted field names, never private input values or Pydantic ctx.
    from typing import get_args

    from opportunity_platform.eligibility.rules import FactKey

    issues = []
    for item in error.errors():
        fields = [str(part) for part in item["loc"]]
        if len(item["loc"]) > 2 and item["loc"][1] == "facts":
            index = item["loc"][2]
            if isinstance(index, int) and isinstance(error.body, dict):
                facts = error.body.get("facts", [])
                if (
                    isinstance(facts, list)
                    and index < len(facts)
                    and isinstance(facts[index], dict)
                ):
                    key = facts[index].get("key")
                    if key in get_args(FactKey):
                        fields = [key]
        issues.append({"fields": fields, "type": item["type"]})
    return response(
        request,
        422,
        "invalid_value"
        if request.url.path.startswith(("/v1/profile", "/v1/people", "/v1/businesses"))
        else "invalid_request",
        "A value or date is invalid. Check the identified field. Your answers are preserved.",
        issues=issues,
    )


@app.exception_handler(HTTPException)
async def http_error(request: Request, error: HTTPException):
    return response(
        request, error.status_code, "http_error", "The requested operation is unavailable."
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, error: SQLAlchemyError):
    return response(
        request, 503, "database_unavailable", "The database is temporarily unavailable."
    )


@app.exception_handler(Exception)
async def internal_error(request: Request, error: Exception):
    logger.error(
        json.dumps(
            {
                "event": "internal_error",
                "request_id": getattr(request.state, "request_id", None),
                "type": type(error).__name__,
            }
        )
    )
    return response(request, 500, "internal_error", "An unexpected error occurred.")


class Health(BaseModel):
    status: str
    database: str


@app.get("/live", response_model=Health)
def live():
    # Liveness must not restart healthy processes during a database outage.
    return Health(status="ok", database="not_checked")


@app.get("/health", response_model=Health)
def health(session: DB):
    session.execute(text("SELECT 1"))
    return Health(status="ok", database="connected")


@app.get("/v1/opportunities", response_model=OpportunityPage)
def opportunities(
    session: DB,
    q: Annotated[str | None, Query(max_length=200)] = None,
    category: Annotated[str | None, Query(max_length=80)] = None,
    state: Annotated[str | None, Query(max_length=80)] = None,
    district: Annotated[str | None, Query(max_length=80)] = None,
    issuer: Annotated[str | None, Query(max_length=200)] = None,
    status: Status | None = None,
    deadline_before: date | None = None,
    cursor: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 12,
    development: bool = False,
    include_national: bool = False,
):
    return service.browse(
        session,
        q,
        category,
        state,
        district,
        issuer,
        status,
        deadline_before,
        cursor,
        limit,
        development,
        include_national,
    )


@app.get("/v1/opportunity-facets", response_model=Facets)
def opportunity_facets(session: DB, development: bool = False):
    return service.facets(session, development)


@app.get("/v1/opportunities/{identifier}", response_model=OpportunityView)
def opportunity_detail(identifier: uuid.UUID, session: DB, development: bool = False):
    return service.detail(session, identifier, development)


@app.get("/v1/me", response_model=AccountView)
def me(session: DB, uid: Annotated[str, Depends(current_uid)]):
    user = account(session, uid)
    session.commit()
    return AccountView(uid=uid, is_admin=user.is_admin)


app.include_router(router)
app.include_router(documents_router)


app.include_router(retrieval_router)
app.include_router(government_sources_router)
