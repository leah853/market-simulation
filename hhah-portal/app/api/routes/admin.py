"""Admin-only routes: BAA viewer + Audit activity."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.templating import render
from app.core.config import get_settings
from app.core.deps import CurrentUser, require_permissions
from app.core.permissions import P
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.organization import BAARecord
from app.models.user import User

router = APIRouter()


# ─── BAA ─────────────────────────────────────────────────────
@router.get("/admin/baa")
def baa_page(
    request: Request,
    user: CurrentUser = Depends(require_permissions(P.BAA_VIEW)),
    db: Session = Depends(get_db),
):
    current = db.scalar(
        select(BAARecord).where(
            BAARecord.org_id == user.org_id,
            BAARecord.status == "active",
            BAARecord.deleted_at.is_(None),
        ).order_by(BAARecord.created_at.desc()).limit(1)
    )
    history = list(db.scalars(
        select(BAARecord).where(
            BAARecord.org_id == user.org_id,
            BAARecord.deleted_at.is_(None),
        ).order_by(BAARecord.created_at.desc())
    ))

    signed_by_map: dict[UUID, str] = {}
    for b in history:
        if b.signed_by_user_id and b.signed_by_user_id not in signed_by_map:
            u = db.get(User, b.signed_by_user_id)
            if u:
                signed_by_map[b.signed_by_user_id] = u.display_name

    return render(request, "admin/baa.html", {
        "current": current, "history": history,
        "signed_by_map": signed_by_map,
        "app_brand": get_settings().app_brand,
    }, user=user)


# ─── Audit ───────────────────────────────────────────────────
@router.get("/admin/audit")
def audit_page(
    request: Request,
    actor:        Optional[UUID] = Query(None),
    action:       Optional[str]  = Query(None),
    subject_type: Optional[str]  = Query(None),
    user: CurrentUser = Depends(require_permissions(P.AUDIT_VIEW)),
    db: Session = Depends(get_db),
):
    stmt = select(AuditLog).where(AuditLog.org_id == user.org_id)
    if actor:        stmt = stmt.where(AuditLog.actor_user_id == actor)
    if action:       stmt = stmt.where(AuditLog.action_type == action)
    if subject_type: stmt = stmt.where(AuditLog.subject_type == subject_type)
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(200)
    entries = list(db.scalars(stmt))

    actor_names: dict[UUID, str] = {}
    for e in entries:
        if e.actor_user_id and e.actor_user_id not in actor_names:
            u = db.get(User, e.actor_user_id)
            if u:
                actor_names[e.actor_user_id] = u.display_name

    return render(request, "admin/audit.html", {
        "entries": entries, "actor_names": actor_names,
        "filter_actor": actor, "filter_action": action,
        "filter_subject_type": subject_type,
        "app_brand": get_settings().app_brand,
    }, user=user)
