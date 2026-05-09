"""Notification queries + actions."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification


def list_for_user(
    db: Session, *, org_id: UUID, user_id: UUID,
    unread_only: bool = False, category: Optional[str] = None,
    limit: int = 100,
) -> list[Notification]:
    stmt = select(Notification).where(
        Notification.org_id == org_id,
        Notification.user_id == user_id,
        Notification.deleted_at.is_(None),
    )
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    if category:
        stmt = stmt.where(Notification.category == category)
    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
    return list(db.scalars(stmt))


def unread_count(db: Session, *, user_id: UUID) -> int:
    return db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
            Notification.deleted_at.is_(None),
        )
    ) or 0


def mark_read(db: Session, *, user_id: UUID, notification_id: UUID) -> None:
    n = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    if n and n.read_at is None:
        n.read_at = datetime.now(timezone.utc)


def dismiss_by_category(db: Session, *, user_id: UUID, category: str) -> int:
    rows = db.scalars(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.category == category,
            Notification.read_at.is_(None),
            Notification.deleted_at.is_(None),
        )
    ).all()
    now = datetime.now(timezone.utc)
    for n in rows:
        n.read_at = now
    return len(rows)
