"""Bulk upload service.

Responsibilities (portal side):
  - Validate file counts (max 5 per content_type) and sizes (50 MB cap)
  - Store files in StorageBackend
  - Create BulkUpload + BulkUploadFile records
  - Dispatch to the Eonexea orchestrator (stubbed for now)
  - Show status / errors back to the user

What this does NOT do:
  - Actual OCR / ML extraction (lives in the orchestrator)
  - Writing patient/episode/document rows from extracted content
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import BinaryIO, Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.models.sync import BulkUpload, BulkUploadFile, UploadRowError
from app.services.storage import get_storage, make_storage_key

# ─── Config ─────────────────────────────────────────────────────────
MAX_FILES_PER_CONTENT_TYPE = 5
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

ALLOWED_PATIENT_EXTS = {".csv", ".xlsx", ".xls", ".json"}
ALLOWED_ORDER_EXTS = {".pdf"}


# ─── Errors ─────────────────────────────────────────────────────────
class SyncError(Exception):
    pass


class TooManyFiles(SyncError):
    pass


class FileTooLarge(SyncError):
    pass


class WrongExtension(SyncError):
    pass


# ─── DTOs ───────────────────────────────────────────────────────────
@dataclass(slots=True)
class IncomingFile:
    filename: str
    content_type_label: str   # 'patient' | 'signed_orders' | 'unsigned_orders'
    size_bytes: int
    stream: BinaryIO


@dataclass(slots=True)
class UploadResult:
    upload_id: UUID
    accepted_files: int
    rejected: list[tuple[str, str]]   # (filename, reason)
    workflow_run_id: UUID | None


# ─── Validation ─────────────────────────────────────────────────────
def _ext(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename[filename.rfind("."):].lower()


def _validate_file(f: IncomingFile) -> None:
    if f.size_bytes > MAX_FILE_SIZE_BYTES:
        raise FileTooLarge(f"{f.filename} exceeds 50 MB cap")
    ext = _ext(f.filename)
    if f.content_type_label == "patient" and ext not in ALLOWED_PATIENT_EXTS:
        raise WrongExtension(
            f"{f.filename}: patient files must be CSV / XLSX / JSON"
        )
    if f.content_type_label in ("signed_orders", "unsigned_orders") and ext not in ALLOWED_ORDER_EXTS:
        raise WrongExtension(f"{f.filename}: order files must be PDF")


def _validate_counts(files: Iterable[IncomingFile]) -> None:
    counts: dict[str, int] = {}
    for f in files:
        counts[f.content_type_label] = counts.get(f.content_type_label, 0) + 1
    for label, n in counts.items():
        if n > MAX_FILES_PER_CONTENT_TYPE:
            raise TooManyFiles(
                f"{label}: {n} files exceeds the limit of {MAX_FILES_PER_CONTENT_TYPE}"
            )


# ─── Submit ─────────────────────────────────────────────────────────
def submit_bulk_upload(
    db: Session,
    *,
    org_id: UUID,
    user_id: UUID,
    files: list[IncomingFile],
) -> UploadResult:
    """Validate, store, and create the BulkUpload + per-file records.

    Returns synchronously; the orchestrator picks up async via
    workflow event 'bulk_upload.received'.
    """
    if not files:
        raise SyncError("no files provided")

    _validate_counts(files)

    storage = get_storage()
    bulk = BulkUpload(
        org_id=org_id,
        uploaded_by_user_id=user_id,
        status="queued",
        file_count=len(files),
    )
    db.add(bulk)
    db.flush()

    rejected: list[tuple[str, str]] = []
    accepted = 0

    for f in files:
        try:
            _validate_file(f)
        except SyncError as e:
            rejected.append((f.filename, str(e)))
            continue

        kind_dir = {
            "patient": "patient_files",
            "signed_orders": "signed_orders",
            "unsigned_orders": "unsigned_orders",
        }[f.content_type_label]
        key = make_storage_key(org_id=org_id, kind=kind_dir, filename=f.filename)
        storage.put(key, f.stream, content_type=_guess_mime(f.filename))

        db.add(BulkUploadFile(
            bulk_upload_id=bulk.id,
            filename=f.filename,
            content_type=f.content_type_label,
            detected_format=_ext(f.filename).lstrip("."),
            storage_key=key,
            size_bytes=f.size_bytes,
            status="accepted",
        ))
        accepted += 1

    bulk.status = "processing" if accepted > 0 else "failed"
    bulk.started_at = datetime.now(timezone.utc)

    write_audit(
        db,
        org_id=org_id,
        actor_user_id=user_id,
        action_type="bulk_upload.submitted",
        subject_type="bulk_upload",
        subject_id=bulk.id,
        details={
            "file_count": len(files),
            "accepted": accepted,
            "rejected": [{"filename": fn, "reason": r} for fn, r in rejected],
        },
    )

    # In production this would emit `bulk_upload.received` to the orchestrator
    # event bus. For the scaffold, we just stamp a placeholder workflow_run_id.
    bulk.workflow_run_id = bulk.id  # placeholder

    return UploadResult(
        upload_id=bulk.id,
        accepted_files=accepted,
        rejected=rejected,
        workflow_run_id=bulk.workflow_run_id,
    )


def _guess_mime(filename: str) -> str:
    ext = _ext(filename)
    return {
        ".pdf":  "application/pdf",
        ".csv":  "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls":  "application/vnd.ms-excel",
        ".json": "application/json",
    }.get(ext, "application/octet-stream")


# ─── Listing ────────────────────────────────────────────────────────
def list_uploads(
    db: Session,
    *,
    org_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[BulkUpload]:
    return list(db.scalars(
        select(BulkUpload)
        .where(BulkUpload.org_id == org_id, BulkUpload.deleted_at.is_(None))
        .order_by(BulkUpload.created_at.desc())
        .limit(limit)
        .offset(offset)
    ))


def get_upload(db: Session, *, org_id: UUID, upload_id: UUID) -> BulkUpload | None:
    return db.scalar(
        select(BulkUpload).where(
            BulkUpload.id == upload_id,
            BulkUpload.org_id == org_id,
            BulkUpload.deleted_at.is_(None),
        )
    )


def get_upload_files(db: Session, *, upload_id: UUID) -> list[BulkUploadFile]:
    return list(db.scalars(
        select(BulkUploadFile)
        .where(BulkUploadFile.bulk_upload_id == upload_id)
        .order_by(BulkUploadFile.created_at.asc())
    ))


def get_file_errors(db: Session, *, file_id: UUID) -> list[UploadRowError]:
    return list(db.scalars(
        select(UploadRowError)
        .where(UploadRowError.bulk_upload_file_id == file_id)
        .order_by(UploadRowError.row_number.asc().nullslast())
    ))


def upload_summary(db: Session, *, org_id: UUID) -> dict:
    """Counts for the sync overview tile."""
    from sqlalchemy import func
    last7 = db.scalar(
        select(func.count(BulkUpload.id))
        .where(BulkUpload.org_id == org_id, BulkUpload.deleted_at.is_(None))
    ) or 0
    return {"recent_count": last7}
