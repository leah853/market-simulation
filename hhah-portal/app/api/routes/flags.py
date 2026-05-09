"""Flag routes — list, create, acknowledge/resolve."""
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
from app.services import flag_service as fs

router = APIRouter()


@router.get("/flags")
def flags_list(
    request: Request,
    source:   Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status:   Optional[str] = Query(None),
    mine:     bool = Query(False),
    user: CurrentUser = Depends(require_permissions(P.FLAG_VIEW)),
    db: Session = Depends(get_db),
):
    flags = fs.list_flags(
        db, org_id=user.org_id,
        source=source, severity=severity, status=status,
        mine_user_id=user.user_id if mine else None,
    )
    summary = fs.summarize(db, org_id=user.org_id)
    return render(request, "flags/list.html", {
        "flags": flags, "summary": summary,
        "filter_source": source, "filter_severity": severity,
        "filter_status": status, "mine": mine,
        "app_brand": get_settings().app_brand,
    }, user=user)


@router.get("/flags/new")
def flags_new_page(
    request: Request,
    subject_type: str = Query(...),
    subject_id:   UUID = Query(...),
    user: CurrentUser = Depends(require_permissions(P.FLAG_CREATE)),
):
    return render(request, "flags/new.html", {
        "subject_type": subject_type, "subject_id": subject_id,
        "app_brand": get_settings().app_brand,
    }, user=user)


@router.post("/flags/new")
def flags_create_submit(
    request: Request,
    subject_type: str = Form(...),
    subject_id:   UUID = Form(...),
    category:     str = Form(...),
    severity:     str = Form("medium"),
    reason:       str = Form(...),
    notes:        Optional[str] = Form(None),
    user: CurrentUser = Depends(require_permissions(P.FLAG_CREATE)),
    db: Session = Depends(get_db),
):
    fs.create_flag(
        db, org_id=user.org_id, user_id=user.user_id,
        subject_type=subject_type, subject_id=subject_id,
        category=category, severity=severity, reason=reason, notes=notes,
    )
    db.commit()
    return RedirectResponse(url="/flags", status_code=303)


@router.post("/flags/{flag_id}/acknowledge")
def flag_acknowledge(
    flag_id: UUID,
    request: Request,
    user: CurrentUser = Depends(require_permissions(P.FLAG_ACT)),
    db: Session = Depends(get_db),
):
    try:
        fs.acknowledge(db, org_id=user.org_id, user_id=user.user_id, flag_id=flag_id)
    except LookupError:
        raise HTTPException(status_code=404)
    db.commit()
    return RedirectResponse(url="/flags", status_code=303)


@router.post("/flags/{flag_id}/resolve")
def flag_resolve(
    flag_id: UUID,
    request: Request,
    notes: Optional[str] = Form(None),
    user: CurrentUser = Depends(require_permissions(P.FLAG_ACT)),
    db: Session = Depends(get_db),
):
    try:
        fs.resolve(db, org_id=user.org_id, user_id=user.user_id,
                   flag_id=flag_id, notes=notes)
    except LookupError:
        raise HTTPException(status_code=404)
    db.commit()
    return RedirectResponse(url="/flags", status_code=303)
