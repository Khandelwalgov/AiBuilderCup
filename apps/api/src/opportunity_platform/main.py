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
from opportunity_platform.opportunities import service
from opportunity_platform.opportunities.schemas import (
    Facets,
    OpportunityPage,
    OpportunityView,
    Status,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("opportunity")
app = FastAPI(
    title="Opportunity Intelligence API",
    version="0.1.0",
    responses={
        401: {"model": ErrorEnvelope},
        404: {"model": ErrorEnvelope},
        422: {"model": ErrorEnvelope},
        503: {"model": ErrorEnvelope},
    },
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().cors_origins,
    allow_methods=["GET"],
    allow_headers=["Authorization", "Content-Type"],
)
DB = Annotated[Session, Depends(get_session)]


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    start = time.monotonic()
    result = await call_next(request)
    result.headers["X-Request-ID"] = request.state.request_id
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
    return response(request, error.status, error.code, error.message)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError):
    return response(request, 422, "invalid_request", "Check the request parameters and try again.")


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
):
    return service.browse(
        session, q, category, state, district, issuer, status, deadline_before, cursor, limit
    )


@app.get("/v1/opportunity-facets", response_model=Facets)
def opportunity_facets(session: DB):
    return service.facets(session)


@app.get("/v1/opportunities/{identifier}", response_model=OpportunityView)
def opportunity_detail(identifier: uuid.UUID, session: DB):
    return service.detail(session, identifier)


class Account(BaseModel):
    uid: str


@app.get("/v1/me", response_model=Account)
def me(uid: Annotated[str, Depends(current_uid)]):
    # Only the verified caller identity; no client-supplied object identifier.
    return Account(uid=uid)
