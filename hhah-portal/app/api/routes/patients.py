"""Patient routes — list + detail + timeline."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.templating import render
from app.core.audit import log_phi_access
from app.core.config import get_settings
from app.core.deps import CurrentUser, require_permissions
from app.core.permissions import P
from app.db.session import get_db
from app.services import patient_service as ps

router = APIRouter()


@router.get("/patients")
def patient_list(
    request: Request,
    q: Optional[str] = Query(None),
    flagged: bool = Query(False),
    user: CurrentUser = Depends(require_permissions(P.PATIENT_VIEW)),
    db: Session = Depends(get_db),
):
    rows = ps.list_patients(
        db, org_id=user.org_id, q=q, flagged_only=flagged, limit=100,
    )

    # PHI access log — list view
    log_phi_access(
        db, org_id=user.org_id, user_id=user.user_id, patient_id=None,
        access_type="api_read", access_granularity="query",
        context_url=str(request.url),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()

    return render(request, "patients/list.html", {
        "rows": rows, "q": q or "", "flagged": flagged,
        "app_brand": get_settings().app_brand,
    }, user=user)


@router.get("/patients/{patient_id}")
def patient_detail(
    patient_id: UUID,
    request: Request,
    user: CurrentUser = Depends(require_permissions(P.PATIENT_VIEW)),
    db: Session = Depends(get_db),
):
    view = ps.get_patient_detail(db, org_id=user.org_id, patient_id=patient_id)
    if not view:
        raise HTTPException(status_code=404, detail="patient not found")

    # PHI access log — detail view
    log_phi_access(
        db, org_id=user.org_id, user_id=user.user_id, patient_id=patient_id,
        access_type="detail_view", access_granularity="row_expand",
        context_url=str(request.url),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    # Build timeline data
    current_episodes = ps.get_episodes_for_admission(
        db, admission_id=view.current_admission.id
    ) if view.current_admission else []

    db.commit()

    return render(request, "patients/detail.html", {
        "view": view,
        "current_episodes": current_episodes,
        "app_brand": get_settings().app_brand,
    }, user=user)
