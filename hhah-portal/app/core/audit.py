"""Audit + PHI access logging helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit import AuditLog, PHIAccessLog


def write_audit(
    db: Session,
    *,
    org_id: UUID,
    actor_user_id: Optional[UUID],
    action_type: str,
    subject_type: str,
    subject_id: Optional[UUID] = None,
    subject_label: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    workflow_run_id: Optional[UUID] = None,
) -> None:
    db.add(AuditLog(
        org_id=org_id,
        actor_user_id=actor_user_id,
        action_type=action_type,
        subject_type=subject_type,
        subject_id=subject_id,
        subject_label=subject_label,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        workflow_run_id=workflow_run_id,
    ))


def log_phi_access(
    db: Session,
    *,
    org_id: UUID,
    user_id: UUID,
    patient_id: Optional[UUID],
    access_type: str,
    access_granularity: str = "query",
    context_url: Optional[str] = None,
    fields_read: Optional[list[str]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    db.add(PHIAccessLog(
        org_id=org_id,
        user_id=user_id,
        patient_id=patient_id,
        access_type=access_type,
        access_granularity=access_granularity,
        context_url=context_url,
        fields_read=fields_read,
        ip_address=ip_address,
        user_agent=user_agent,
        accessed_at=datetime.now(timezone.utc),
    ))
