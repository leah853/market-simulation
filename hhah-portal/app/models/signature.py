"""Signature requests — read-only on the HHAH portal side."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, SoftDeleteMixin, gen_uuid


class SignatureRequest(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "signature_request"
    __table_args__ = (
        Index("ix_sigreq_practitioner", "requested_practitioner_id"),
        Index("ix_sigreq_status", "org_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False, index=True,
    )
    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document.id"), nullable=False,
    )
    requested_practitioner_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("practitioner.person_id"), nullable=False,
    )
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    signed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True,
        comment="Whoever physically clicked sign — could be a delegated PG admin.",
    )
    signed_on_behalf_of: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("practitioner.person_id"), nullable=True,
        comment="Always populated; equals requested_practitioner_id for direct signs.",
    )
    is_urgent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reminders_sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_reminder_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
