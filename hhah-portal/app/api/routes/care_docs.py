"""Care Coordination Documents — 2-tab hub + document detail."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.templating import render
from app.core.audit import log_phi_access, write_audit
from app.core.config import get_settings
from app.core.deps import CurrentUser, require_permissions
from app.core.permissions import P
from app.db.session import get_db
from app.services import document_service as ds

router = APIRouter()


@router.get("/care-docs")
def care_docs_default(
    user: CurrentUser = Depends(require_permissions(P.DOCUMENT_VIEW)),
):
    return RedirectResponse(url="/care-docs/signature-required", status_code=303)


@router.get("/care-docs/signature-required")
def care_docs_signature(
    request: Request,
    flagged: bool = Query(False),
    user: CurrentUser = Depends(require_permissions(P.DOCUMENT_VIEW)),
    db: Session = Depends(get_db),
):
    rows = ds.list_documents(db, org_id=user.org_id, tab="signature_required", flagged_only=flagged)
    counts = ds.tab_counts(db, org_id=user.org_id)
    return render(request, "documents/hub.html", {
        "tab": "signature_required",
        "rows": rows,
        "counts": counts,
        "flagged": flagged,
        "app_brand": get_settings().app_brand,
    }, user=user)


@router.get("/care-docs/other")
def care_docs_other(
    request: Request,
    flagged: bool = Query(False),
    user: CurrentUser = Depends(require_permissions(P.DOCUMENT_VIEW)),
    db: Session = Depends(get_db),
):
    rows = ds.list_documents(db, org_id=user.org_id, tab="other", flagged_only=flagged)
    counts = ds.tab_counts(db, org_id=user.org_id)
    return render(request, "documents/hub.html", {
        "tab": "other",
        "rows": rows,
        "counts": counts,
        "flagged": flagged,
        "app_brand": get_settings().app_brand,
    }, user=user)


@router.get("/care-docs/{document_id}")
def document_detail(
    document_id: UUID,
    request: Request,
    user: CurrentUser = Depends(require_permissions(P.DOCUMENT_VIEW)),
    db: Session = Depends(get_db),
):
    doc = ds.get_document(db, org_id=user.org_id, document_id=document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")

    log_phi_access(
        db, org_id=user.org_id, user_id=user.user_id, patient_id=doc.patient_id,
        access_type="detail_view", access_granularity="row_expand",
        context_url=str(request.url),
    )
    db.commit()

    comments = ds.list_comments(db, document_id=document_id)
    return render(request, "documents/detail.html", {
        "doc": doc, "comments": comments,
        "app_brand": get_settings().app_brand,
    }, user=user)


@router.post("/care-docs/{document_id}/comment")
def document_comment_submit(
    document_id: UUID,
    request: Request,
    body: str = Form(...),
    user: CurrentUser = Depends(require_permissions(P.DOCUMENT_COMMENT)),
    db: Session = Depends(get_db),
):
    doc = ds.get_document(db, org_id=user.org_id, document_id=document_id)
    if not doc:
        raise HTTPException(status_code=404)
    ds.add_comment(db, org_id=user.org_id, user_id=user.user_id,
                   document_id=document_id, body=body)
    write_audit(db, org_id=user.org_id, actor_user_id=user.user_id,
                action_type="document.comment.added", subject_type="document",
                subject_id=document_id)
    db.commit()
    return RedirectResponse(url=f"/care-docs/{document_id}", status_code=303)
