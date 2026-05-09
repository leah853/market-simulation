"""Notification routes."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.templating import render
from app.core.config import get_settings
from app.core.deps import CurrentUser, require_permissions
from app.core.permissions import P
from app.db.session import get_db
from app.services import notification_service as ns

router = APIRouter()


@router.get("/notifications")
def notifications_page(
    request: Request,
    unread: bool = Query(False),
    category: Optional[str] = Query(None),
    user: CurrentUser = Depends(require_permissions(P.NOTIF_VIEW)),
    db: Session = Depends(get_db),
):
    items = ns.list_for_user(
        db, org_id=user.org_id, user_id=user.user_id,
        unread_only=unread, category=category,
    )
    return render(request, "notifications/list.html", {
        "items": items, "unread": unread, "category": category,
        "app_brand": get_settings().app_brand,
    }, user=user)


@router.post("/notifications/{notif_id}/read")
def notification_read(
    notif_id: UUID,
    user: CurrentUser = Depends(require_permissions(P.NOTIF_ACT)),
    db: Session = Depends(get_db),
):
    ns.mark_read(db, user_id=user.user_id, notification_id=notif_id)
    db.commit()
    return RedirectResponse(url="/notifications", status_code=303)


@router.post("/notifications/dismiss-by-category")
def notifications_dismiss_category(
    category: str = Form(...),
    user: CurrentUser = Depends(require_permissions(P.NOTIF_ACT)),
    db: Session = Depends(get_db),
):
    ns.dismiss_by_category(db, user_id=user.user_id, category=category)
    db.commit()
    return RedirectResponse(url="/notifications", status_code=303)
