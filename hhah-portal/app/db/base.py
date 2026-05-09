"""SQLAlchemy declarative base + shared mixins."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TenantMixin:
    """Multi-tenant scoping. Every domain row has org_id."""
    org_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow,
        server_default=func.now(), onupdate=utcnow,
    )


class SoftDeleteMixin:
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


def gen_uuid() -> UUID:
    return uuid4()
