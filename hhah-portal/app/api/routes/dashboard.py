"""Dashboard — empty state and (later) active state."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.templating import render
from app.core.config import get_settings
from app.core.deps import CurrentUser, get_current_user
from app.core.permissions import P
from app.db.session import get_db
from app.models.admission import Episode

router = APIRouter()


@router.get("/")
def dashboard(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Episode count drives empty-vs-active dashboard switch
    episode_count = db.scalar(
        select(func.count(Episode.id))
        .where(Episode.org_id == user.org_id, Episode.deleted_at.is_(None))
    ) or 0

    if episode_count == 0:
        return render(request, "dashboard/empty.html",
                      {"can_view_baa": user.has(P.BAA_VIEW),
                       "app_brand": get_settings().app_brand},
                      user=user)

    # Active dashboard — placeholder counts for now; real metrics come later
    return render(request, "dashboard/active.html",
                  {"kpis": {
                      "active_patients": 0,
                      "ready_to_bill": 0,
                      "pending_signatures": 0,
                      "unread_communications": 0,
                  },
                   "app_brand": get_settings().app_brand,
                   "can_view_baa": user.has(P.BAA_VIEW)},
                  user=user)
