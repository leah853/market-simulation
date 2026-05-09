"""Notifications — in-app at V1, schema ready for email/SMS later."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, SoftDeleteMixin, gen_uuid


class Notification(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "notification"
    __table_args__ = (
        Index("ix_notif_user_read", "user_id", "read_at"),
        Index("ix_notif_user_created", "user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False, index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("app_user.id"), nullable=False,
    )
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="info")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
