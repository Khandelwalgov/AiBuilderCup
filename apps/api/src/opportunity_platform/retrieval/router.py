from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from opportunity_platform.core.auth import current_uid
from opportunity_platform.db.session import get_session
from opportunity_platform.retrieval.service import SearchRequest, SearchResponse, search
from opportunity_platform.scenarios.service import ScenarioRequest, ScenarioResponse, simulate

router = APIRouter()
DB = Annotated[Session, Depends(get_session)]
UID = Annotated[str, Depends(current_uid)]


@router.post("/v1/search", response_model=SearchResponse)
def recommendations(body: SearchRequest, session: DB, uid: UID, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    result = search(session, uid, body)
    session.rollback()
    return result


@router.post("/v1/scenarios/evaluate", response_model=ScenarioResponse)
def scenario(body: ScenarioRequest, session: DB, uid: UID, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    result = simulate(session, uid, body)
    session.rollback()
    return result
