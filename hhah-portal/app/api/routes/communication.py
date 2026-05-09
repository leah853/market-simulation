"""Communication routes."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.templating import render
from app.core.config import get_settings
from app.core.deps import CurrentUser, require_permissions
from app.core.permissions import P
from app.db.session import get_db
from app.services import communication_service as cs

router = APIRouter()


@router.get("/communication")
def thread_list(
    request: Request,
    user: CurrentUser = Depends(require_permissions(P.COMM_VIEW)),
    db: Session = Depends(get_db),
):
    threads = cs.list_threads(db, org_id=user.org_id, user_id=user.user_id)
    return render(request, "communication/list.html", {
        "threads": threads, "app_brand": get_settings().app_brand,
    }, user=user)


@router.get("/communication/new")
def thread_new_page(
    request: Request,
    patient_id: Optional[UUID] = Query(None),
    document_id: Optional[UUID] = Query(None),
    user: CurrentUser = Depends(require_permissions(P.COMM_CREATE)),
):
    return render(request, "communication/new.html", {
        "linked_patient_id": patient_id,
        "linked_document_id": document_id,
        "app_brand": get_settings().app_brand,
    }, user=user)


@router.post("/communication/new")
def thread_create_submit(
    request: Request,
    subject: str = Form(...),
    body:    str = Form(...),
    linked_patient_id:  Optional[UUID] = Form(None),
    linked_document_id: Optional[UUID] = Form(None),
    user: CurrentUser = Depends(require_permissions(P.COMM_CREATE)),
    db: Session = Depends(get_db),
):
    th = cs.create_thread(
        db, org_id=user.org_id, user_id=user.user_id,
        subject=subject, body=body,
        linked_patient_ids=[linked_patient_id] if linked_patient_id else None,
        linked_document_ids=[linked_document_id] if linked_document_id else None,
    )
    db.commit()
    return RedirectResponse(url=f"/communication/{th.id}", status_code=303)


@router.get("/communication/{thread_id}")
def thread_detail(
    thread_id: UUID,
    request: Request,
    user: CurrentUser = Depends(require_permissions(P.COMM_VIEW)),
    db: Session = Depends(get_db),
):
    th = cs.get_thread(db, org_id=user.org_id, thread_id=thread_id)
    if not th:
        raise HTTPException(status_code=404)
    msgs = cs.list_messages(db, thread_id=thread_id)
    return render(request, "communication/detail.html", {
        "thread": th, "messages": msgs,
        "app_brand": get_settings().app_brand,
    }, user=user)


@router.post("/communication/{thread_id}/reply")
def thread_reply(
    thread_id: UUID,
    request: Request,
    body: str = Form(...),
    user: CurrentUser = Depends(require_permissions(P.COMM_SEND)),
    db: Session = Depends(get_db),
):
    try:
        cs.reply(db, org_id=user.org_id, user_id=user.user_id,
                 thread_id=thread_id, body=body)
    except LookupError:
        raise HTTPException(status_code=404)
    db.commit()
    return RedirectResponse(url=f"/communication/{thread_id}", status_code=303)
