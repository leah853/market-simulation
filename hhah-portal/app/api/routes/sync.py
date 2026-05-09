"""Sync routes — overview, upload, history, detail, errors."""
from __future__ import annotations

from io import BytesIO
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.templating import render
from app.core.config import get_settings
from app.core.deps import CurrentUser, require_permissions
from app.core.permissions import P
from app.db.session import get_db
from app.services import sync_service as sync
from app.services.sync_service import IncomingFile

router = APIRouter()


# ─── Overview ───────────────────────────────────────────────────────
@router.get("/sync")
def sync_overview(
    request: Request,
    user: CurrentUser = Depends(require_permissions(P.SYNC_VIEW)),
    db: Session = Depends(get_db),
):
    uploads = sync.list_uploads(db, org_id=user.org_id, limit=10)
    summary = sync.upload_summary(db, org_id=user.org_id)
    return render(request, "sync/overview.html", {
        "uploads": uploads, "summary": summary,
        "app_brand": get_settings().app_brand,
    }, user=user)


# ─── Upload page ────────────────────────────────────────────────────
@router.get("/sync/upload")
def sync_upload_page(
    request: Request,
    user: CurrentUser = Depends(require_permissions(P.SYNC_UPLOAD)),
):
    return render(request, "sync/upload.html", {
        "app_brand": get_settings().app_brand,
        "max_per_type": sync.MAX_FILES_PER_CONTENT_TYPE,
        "max_size_mb": sync.MAX_FILE_SIZE_BYTES // (1024 * 1024),
    }, user=user)


@router.post("/sync/upload")
async def sync_upload_submit(
    request: Request,
    patient_files:        Annotated[list[UploadFile], File()] = [],
    signed_order_files:   Annotated[list[UploadFile], File()] = [],
    unsigned_order_files: Annotated[list[UploadFile], File()] = [],
    user: CurrentUser = Depends(require_permissions(P.SYNC_UPLOAD)),
    db: Session = Depends(get_db),
):
    incoming: list[IncomingFile] = []

    async def _attach(uf: UploadFile, label: str):
        if not uf or not uf.filename:
            return
        body = await uf.read()
        incoming.append(IncomingFile(
            filename=uf.filename,
            content_type_label=label,
            size_bytes=len(body),
            stream=BytesIO(body),
        ))

    for uf in patient_files or []:
        await _attach(uf, "patient")
    for uf in signed_order_files or []:
        await _attach(uf, "signed_orders")
    for uf in unsigned_order_files or []:
        await _attach(uf, "unsigned_orders")

    if not incoming:
        return render(request, "sync/upload.html", {
            "error": "No files selected.",
            "app_brand": get_settings().app_brand,
            "max_per_type": sync.MAX_FILES_PER_CONTENT_TYPE,
            "max_size_mb": sync.MAX_FILE_SIZE_BYTES // (1024 * 1024),
        }, user=user, status_code=400)

    try:
        result = sync.submit_bulk_upload(
            db, org_id=user.org_id, user_id=user.user_id, files=incoming,
        )
        db.commit()
    except sync.TooManyFiles as e:
        db.rollback()
        return render(request, "sync/upload.html", {
            "error": str(e),
            "app_brand": get_settings().app_brand,
            "max_per_type": sync.MAX_FILES_PER_CONTENT_TYPE,
            "max_size_mb": sync.MAX_FILE_SIZE_BYTES // (1024 * 1024),
        }, user=user, status_code=400)

    return RedirectResponse(
        url=f"/sync/uploads/{result.upload_id}", status_code=status.HTTP_303_SEE_OTHER,
    )


# ─── Upload history (list + detail + errors) ───────────────────────
@router.get("/sync/uploads")
def sync_history(
    request: Request,
    user: CurrentUser = Depends(require_permissions(P.SYNC_VIEW)),
    db: Session = Depends(get_db),
):
    uploads = sync.list_uploads(db, org_id=user.org_id, limit=50)
    return render(request, "sync/history.html", {
        "uploads": uploads,
        "app_brand": get_settings().app_brand,
    }, user=user)


@router.get("/sync/uploads/{upload_id}")
def sync_upload_detail(
    upload_id: UUID,
    request: Request,
    user: CurrentUser = Depends(require_permissions(P.SYNC_VIEW)),
    db: Session = Depends(get_db),
):
    upload = sync.get_upload(db, org_id=user.org_id, upload_id=upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="upload not found")
    files = sync.get_upload_files(db, upload_id=upload_id)
    return render(request, "sync/upload_detail.html", {
        "upload": upload, "files": files,
        "app_brand": get_settings().app_brand,
    }, user=user)


@router.get("/sync/files/{file_id}/errors")
def sync_file_errors(
    file_id: UUID,
    request: Request,
    user: CurrentUser = Depends(require_permissions(P.SYNC_VIEW)),
    db: Session = Depends(get_db),
):
    errors = sync.get_file_errors(db, file_id=file_id)
    return render(request, "sync/errors.html", {
        "errors": errors, "file_id": file_id,
        "app_brand": get_settings().app_brand,
    }, user=user)
