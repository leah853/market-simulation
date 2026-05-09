"""Profile + Settings."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.templating import render
from app.core.audit import write_audit
from app.core.config import get_settings
from app.core.deps import CurrentUser, get_current_user, require_permissions
from app.core.permissions import P
from app.db.session import get_db
from app.models.user import Session as UserSession, User

router = APIRouter()


@router.get("/profile")
def profile_page(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_user = db.get(User, user.user_id)
    sessions = list(db.scalars(
        select(UserSession)
        .where(UserSession.user_id == user.user_id, UserSession.revoked_at.is_(None))
        .order_by(UserSession.last_seen_at.desc())
    ))
    return render(request, "profile/profile.html", {
        "u": db_user, "sessions": sessions,
        "app_brand": get_settings().app_brand,
    }, user=user)


@router.post("/profile")
def profile_update(
    request: Request,
    display_name: str = Form(...),
    timezone: str = Form("UTC"),
    user: CurrentUser = Depends(require_permissions(P.PROFILE_UPDATE)),
    db: Session = Depends(get_db),
):
    db_user = db.get(User, user.user_id)
    db_user.display_name = display_name
    db_user.timezone = timezone
    write_audit(db, org_id=user.org_id, actor_user_id=user.user_id,
                action_type="profile.updated", subject_type="user",
                subject_id=user.user_id)
    db.commit()
    return RedirectResponse(url="/profile", status_code=303)


@router.post("/profile/sessions/{sid}/revoke")
def revoke_session(
    sid: UUID,
    user: CurrentUser = Depends(require_permissions(P.SESSION_REVOKE)),
    db: Session = Depends(get_db),
):
    sess = db.get(UserSession, sid)
    from datetime import datetime, timezone as tz
    if sess and sess.user_id == user.user_id:
        sess.revoked_at = datetime.now(tz.utc)
        write_audit(db, org_id=user.org_id, actor_user_id=user.user_id,
                    action_type="session.revoked", subject_type="session",
                    subject_id=sid)
        db.commit()
    return RedirectResponse(url="/profile", status_code=303)


@router.get("/settings")
def settings_page(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    return render(request, "profile/settings.html", {
        "app_brand": get_settings().app_brand,
    }, user=user)
