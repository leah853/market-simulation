"""Storage abstraction — local filesystem for dev, S3 for prod.

The portal stores uploaded files temporarily; the orchestrator OCR pipeline
later reads them and processes asynchronously. The portal does NOT do OCR.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO
from uuid import UUID, uuid4

from app.core.config import get_settings


class StorageBackend:
    def put(self, key: str, data: BinaryIO, content_type: str = "application/octet-stream") -> str:
        raise NotImplementedError

    def url_for(self, key: str, ttl_seconds: int = 300) -> str:
        raise NotImplementedError


class LocalFilesystemStorage(StorageBackend):
    """Dev backend — writes to ./.storage/<key>."""

    def __init__(self, root: Path | None = None):
        self.root = root or (Path.cwd() / ".storage")
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, data: BinaryIO, content_type: str = "application/octet-stream") -> str:
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as f:
            for chunk in iter(lambda: data.read(1 << 16), b""):
                f.write(chunk)
        return key

    def url_for(self, key: str, ttl_seconds: int = 300) -> str:
        return f"/static-storage/{key}"


_backend: StorageBackend | None = None


def get_storage() -> StorageBackend:
    global _backend
    if _backend is None:
        s = get_settings()
        # Always local in this scaffold; swap to S3Storage when ready
        _backend = LocalFilesystemStorage()
    return _backend


def make_storage_key(*, org_id: UUID, kind: str, filename: str) -> str:
    """Deterministic, tenant-partitioned key:
       <org_id>/<kind>/<yyyy-mm>/<uuid>__<safe_filename>"""
    safe = "".join(c if c.isalnum() or c in (".", "-", "_") else "_" for c in filename)
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"{org_id}/{kind}/{month}/{uuid4().hex}__{safe}"
