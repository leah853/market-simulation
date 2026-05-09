"""Flag — polymorphic, HHAH-creatable, multi-source resolution."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, SoftDeleteMixin, gen_uuid


class Flag(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "flag"
    __table_args__ = (
        CheckConstraint(
            "(status = 'resolved') = (resolved_at IS NOT NULL)",
            name="chk_flag_resolution_consistency",
        ),
        Index("ix_flag_org_status_severity", "org_id", "status", "severity"),
        Index("ix_flag_subject", "subject_type", "subject_id"),
        Index("ix_flag_open_age", "created_at"),
        Index("ix_flag_source", "org_id", "source"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False, index=True,
    )

    # Polymorphic subject — patient | document | episode | admission | order
    subject_type: Mapped[str] = mapped_column(String(40), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)

    # Source
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    source_user_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("app_user.id"), nullable=True,
    )
    source_practitioner_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("practitioner.person_id"), nullable=True,
    )
    source_external_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Content
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Lifecycle
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("app_user.id"), nullable=True,
    )
    escalated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("app_user.id"), nullable=True,
    )
    resolution_method: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    resolution_event_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    resolution_event_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    workflow_run_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
