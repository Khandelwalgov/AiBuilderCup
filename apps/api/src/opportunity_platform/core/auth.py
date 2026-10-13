from typing import Annotated

import firebase_admin
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth
from firebase_admin.exceptions import FirebaseError
from google.auth.exceptions import GoogleAuthError

from opportunity_platform.core.config import settings
from opportunity_platform.core.errors import APIError

bearer = HTTPBearer(auto_error=False)


def current_uid(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    if credentials is None:
        raise APIError(401, "authentication_required", "Sign in to access your account.")
    if not settings().firebase_project_id:
        raise APIError(503, "auth_not_configured", "Firebase authentication is not configured.")
    try:
        try:
            app = firebase_admin.get_app()
        except ValueError:
            app = firebase_admin.initialize_app(
                options={"projectId": settings().firebase_project_id}
            )
        if app.project_id != settings().firebase_project_id:
            raise APIError(503, "auth_project_mismatch", "Firebase project configuration differs.")
        token = auth.verify_id_token(credentials.credentials, app=app, check_revoked=True)
        return token["uid"]
    except (
        auth.InvalidIdTokenError,
        auth.RevokedIdTokenError,
        auth.UserDisabledError,
        ValueError,
        KeyError,
    ):
        raise APIError(401, "invalid_token", "Your session is invalid or expired.") from None
    except (FirebaseError, GoogleAuthError, OSError):
        raise APIError(
            503, "auth_unavailable", "Authentication is temporarily unavailable."
        ) from None
