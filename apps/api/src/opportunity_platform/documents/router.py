"""Small HTTP adapter: metadata intent, bounded binary stream, private authorized access."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from opportunity_platform.core.auth import current_uid
from opportunity_platform.core.config import settings
from opportunity_platform.core.errors import APIError
from opportunity_platform.db.session import get_session
from opportunity_platform.documents import service
from opportunity_platform.documents.schemas import (
    AccessRequest,
    AccessView,
    DeleteWrite,
    DocumentCapabilities,
    DocumentCreate,
    DocumentView,
    LinkWrite,
    RequirementDocumentView,
)
from opportunity_platform.subjects.service import SubjectRef

router = APIRouter(prefix="/v1/documents", tags=["private documents"])
DB = Annotated[Session, Depends(get_session)]
UID = Annotated[str, Depends(current_uid)]


@router.get("/capabilities", response_model=DocumentCapabilities)
def capabilities(uid: UID):
    return DocumentCapabilities(
        uploads_enabled=settings().document_uploads_enabled
        and settings().environment == "development",
        max_file_bytes=settings().document_max_file_bytes,
        max_count=settings().document_max_count,
    )


@router.get("/requirements", response_model=list[RequirementDocumentView])
def requirements(
    session: DB,
    uid: UID,
    kind: Literal["person", "household", "business"] = "person",
    subject_id: uuid.UUID | None = None,
):
    return service.readiness(session, uid, SubjectRef(kind=kind, id=subject_id))


@router.get("", response_model=list[DocumentView])
def listing(
    session: DB,
    uid: UID,
    kind: Literal["person", "household", "business"] = "person",
    subject_id: uuid.UUID | None = None,
):
    return service.listing(session, uid, SubjectRef(kind=kind, id=subject_id))


@router.post("", response_model=DocumentView, status_code=201)
def create(data: DocumentCreate, session: DB, uid: UID):
    return service.create(session, uid, data)


@router.get("/{identifier}", response_model=DocumentView)
def read(identifier: uuid.UUID, session: DB, uid: UID):
    user, doc = service.authorize(session, uid, identifier)
    service.audit(session, user, "document_metadata_viewed", doc)
    session.commit()
    return service.view(session, doc)


@router.put("/{identifier}/content", response_model=DocumentView)
async def upload(identifier: uuid.UUID, request: Request, session: DB, uid: UID):
    service.require_uploads()
    # Authorize before reading untrusted bytes. No multipart/temp files or external AI.
    service.authorize(session, uid, identifier, True)
    media = request.headers.get("content-type", "").split(";")[0]
    if media not in {"application/pdf", "image/jpeg", "image/png"}:
        raise APIError(422, "unsupported_document", "Choose a PDF, JPEG or PNG.")
    try:
        length = int(request.headers.get("content-length", "0"))
    except ValueError:
        raise APIError(422, "invalid_request", "Invalid file length.") from None
    if length > settings().document_max_file_bytes:
        raise APIError(413, "document_size", "The file exceeds the upload size limit.")
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > settings().document_max_file_bytes:
            raise APIError(413, "document_size", "The file exceeds the upload size limit.")
        content.extend(chunk)
    return await run_in_threadpool(service.upload, session, uid, identifier, bytes(content), media)


@router.post("/{identifier}/links", response_model=DocumentView)
def link(identifier: uuid.UUID, data: LinkWrite, session: DB, uid: UID):
    return service.link(session, uid, identifier, data)


@router.delete("/{identifier}", response_model=DocumentView)
def remove(identifier: uuid.UUID, data: DeleteWrite, session: DB, uid: UID):
    return service.remove(session, uid, identifier, data.expected_revision)


@router.post("/{identifier}/access", response_model=AccessView)
def access(identifier: uuid.UUID, data: AccessRequest, session: DB, uid: UID):
    return AccessView(token=service.access(session, uid, identifier, data.purpose))


@router.get("/{identifier}/content")
def retrieve(
    identifier: uuid.UUID,
    session: DB,
    uid: UID,
    purpose: Literal["preview", "download"],
    access_token: Annotated[str, Header(alias="X-Document-Access")],
):
    doc, content = service.retrieve(session, uid, identifier, access_token, purpose)
    extension = {"application/pdf": "pdf", "image/png": "png", "image/jpeg": "jpg"}[doc.media_type]
    disposition = "inline" if purpose == "preview" else "attachment"
    return Response(
        content,
        media_type=doc.media_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="document.{extension}"',
            "Cache-Control": "private, no-store",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox; default-src 'none'; frame-ancestors 'self'",
            "Referrer-Policy": "no-referrer",
        },
    )
