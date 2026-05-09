"""Audit log + PHI access log — append-only."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, gen_uuid


class AuditLog(Base, TimestampMixin):
    """Every privileged action — append-only."""
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_org_time", "org_id", "created_at"),
        Index("ix_audit_actor", "actor_user_id"),
        Index("ix_audit_subject", "subject_type", "subject_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False,
    )
    actor_user_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("app_user.id"), nullable=True,
    )
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(40), nullable=False)
    subject_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    subject_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    workflow_run_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)


class PHIAccessLog(Base):
    """Every PHI access — async write, partitioned monthly in production."""
    __tablename__ = "phi_access_log"
    __table_args__ = (
        Index("ix_phi_org_user_time", "org_id", "user_id", "accessed_at"),
        Index("ix_phi_patient", "patient_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    patient_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    access_type: Mapped[str] = mapped_column(String(40), nullable=False)
    access_granularity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="query",
        comment="query | row_expand | export | bulk_action",
    )
    context_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fields_read: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    workflow_run_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
