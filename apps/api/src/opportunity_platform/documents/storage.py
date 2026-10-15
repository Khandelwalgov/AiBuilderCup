"""Opaque private objects only. Neither paths nor bucket keys leave this module."""

import os
import re
import uuid
from pathlib import Path
from typing import Protocol

from opportunity_platform.core.config import settings
from opportunity_platform.core.errors import APIError


class Storage(Protocol):
    def put(self, key: str, content: bytes, media_type: str) -> None: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...


def check_key(key):
    if not re.fullmatch(r"[a-f0-9]{32}", key):
        raise APIError(404, "document_not_found", "This document is not available.")


class LocalStorage:
    def __init__(self):
        configured = Path(settings().document_local_root)
        if configured.is_symlink():
            raise OSError("Unsafe storage root")
        self.root = configured.resolve()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.root.is_symlink():
            raise OSError("Unsafe storage root")
        self.root.chmod(0o700)

    def put(self, key, content, media_type):
        check_key(key)
        target = self.root / key
        if target.exists():
            raise FileExistsError("Object collision")
        temporary = self.root / (".pending-" + uuid.uuid4().hex)
        try:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as output:
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            # Hard-link creation is atomic and cannot overwrite another object.
            os.link(temporary, target, follow_symlinks=False)
        finally:
            temporary.unlink(missing_ok=True)

    def get(self, key):
        check_key(key)
        fd = os.open(self.root / key, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as source:
            return source.read(settings().document_max_file_bytes + 1)

    def delete(self, key):
        check_key(key)
        (self.root / key).unlink(missing_ok=True)


class GCSStorage:
    def __init__(self):
        if not settings().document_gcs_bucket:
            raise OSError("Private storage is not configured")
        from google.cloud import storage

        self.bucket = storage.Client().bucket(settings().document_gcs_bucket)

    def put(self, key, content, media_type):
        check_key(key)
        blob = self.bucket.blob("private-documents/" + key)
        blob.cache_control = "private, no-store"
        blob.upload_from_string(content, content_type=media_type, if_generation_match=0)

    def get(self, key):
        check_key(key)
        blob = self.bucket.blob("private-documents/" + key)
        blob.reload()
        if not blob.size or blob.size > settings().document_max_file_bytes:
            raise OSError("Stored file size is invalid")
        return blob.download_as_bytes(end=settings().document_max_file_bytes)

    def delete(self, key):
        from google.api_core.exceptions import NotFound

        check_key(key)
        try:
            self.bucket.blob("private-documents/" + key).delete()
        except NotFound:
            pass


def storage(backend=None):
    try:
        return (
            LocalStorage()
            if (backend or settings().document_storage_backend) == "local"
            else GCSStorage()
        )
    except Exception:
        raise APIError(
            503, "storage_unavailable", "Private storage is temporarily unavailable."
        ) from None
