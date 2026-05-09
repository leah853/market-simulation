"""Flag service — list, create, acknowledge, resolve, comment."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.models.flag import Flag


@dataclass(slots=True)
class FlagSummary:
    open: int
    acknowledged: int
    resolved_last_7d: int
    escalated: int


def list_flags(
    db: Session,
    *,
    org_id: UUID,
    source: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    mine_user_id: Optional[UUID] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Flag]:
    stmt = select(Flag).where(Flag.org_id == org_id, Flag.deleted_at.is_(None))
    if source:
        stmt = stmt.where(Flag.source == source)
    if severity:
        stmt = stmt.where(Flag.severity == severity)
    if status:
        stmt = stmt.where(Flag.status == status)
    if mine_user_id:
        stmt = stmt.where(Flag.source_user_id == mine_user_id)
    stmt = stmt.order_by(Flag.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def get_flag(db: Session, *, org_id: UUID, flag_id: UUID) -> Optional[Flag]:
    return db.scalar(
        select(Flag).where(
            Flag.id == flag_id,
            Flag.org_id == org_id,
            Flag.deleted_at.is_(None),
        )
    )


def summarize(db: Session, *, org_id: UUID) -> FlagSummary:
    base = select(func.count(Flag.id)).where(
        Flag.org_id == org_id, Flag.deleted_at.is_(None),
    )
    open_count = db.scalar(base.where(Flag.status == "open")) or 0
    ack_count = db.scalar(base.where(Flag.status == "acknowledged")) or 0
    esc_count = db.scalar(base.where(Flag.status == "escalated")) or 0

    from datetime import timedelta
    seven_days = datetime.now(timezone.utc) - timedelta(days=7)
    resolved = db.scalar(
        base.where(Flag.status == "resolved", Flag.resolved_at >= seven_days)
    ) or 0
    return FlagSummary(
        open=open_count, acknowledged=ack_count,
        resolved_last_7d=resolved, escalated=esc_count,
    )


def create_flag(
    db: Session,
    *,
    org_id: UUID,
    user_id: UUID,
    subject_type: str,
    subject_id: UUID,
    category: str,
    severity: str,
    reason: str,
    notes: Optional[str] = None,
) -> Flag:
    f = Flag(
        org_id=org_id,
        subject_type=subject_type,
        subject_id=subject_id,
        source="hhah_user",
        source_user_id=user_id,
        category=category,
        severity=severity,
        reason=reason,
        notes=notes,
        status="open",
    )
    db.add(f)
    db.flush()

    write_audit(
        db, org_id=org_id, actor_user_id=user_id,
        action_type="flag.created", subject_type="flag", subject_id=f.id,
        details={"subject_type": subject_type, "subject_id": str(subject_id),
                 "severity": severity, "category": category},
    )
    return f


def acknowledge(db: Session, *, org_id: UUID, user_id: UUID, flag_id: UUID) -> Flag:
    f = get_flag(db, org_id=org_id, flag_id=flag_id)
    if not f:
        raise LookupError("flag not found")
    if f.status == "open":
        f.status = "acknowledged"
        f.acknowledged_at = datetime.now(timezone.utc)
        f.acknowledged_by_user_id = user_id
        write_audit(db, org_id=org_id, actor_user_id=user_id,
                    action_type="flag.acknowledged", subject_type="flag", subject_id=flag_id)
    return f


def resolve(
    db: Session, *, org_id: UUID, user_id: UUID, flag_id: UUID,
    resolution_method: str = "marked_resolved", notes: Optional[str] = None,
) -> Flag:
    f = get_flag(db, org_id=org_id, flag_id=flag_id)
    if not f:
        raise LookupError("flag not found")
    f.status = "resolved"
    f.resolved_at = datetime.now(timezone.utc)
    f.resolved_by_user_id = user_id
    f.resolution_method = resolution_method
    if notes:
        f.notes = (f.notes + "\n" if f.notes else "") + notes
    write_audit(db, org_id=org_id, actor_user_id=user_id,
                action_type="flag.resolved", subject_type="flag", subject_id=flag_id,
                details={"method": resolution_method})
    return f
