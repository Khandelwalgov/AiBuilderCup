from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str | None = None
    issues: list[dict] = []


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class APIError(Exception):
    def __init__(self, status: int, code: str, message: str, *, issues=None):
        self.status, self.code, self.message = status, code, message
        self.issues = issues or []


def response(request: Request, status: int, code: str, message: str, *, issues=None):
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "issues": issues or [],
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )
