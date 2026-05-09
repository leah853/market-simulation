"""Practitioner (Physician + NPP), PracticeOrg, and PG ↔ Practitioner Membership."""
from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, SoftDeleteMixin, gen_uuid


class PracticeOrg(Base, TimestampMixin, SoftDeleteMixin):
    """Physician Group / Practice."""
    __tablename__ = "practice_org"

    practice_org_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    group_npi: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)
    ehr_system: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")


class Practitioner(Base, TimestampMixin, SoftDeleteMixin):
    """Individual practitioner — physician or NPP."""
    __tablename__ = "practitioner"
    __table_args__ = (
        Index("ix_practitioner_type", "practitioner_type"),
    )

    person_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    npi: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    practitioner_type: Mapped[str] = mapped_column(String(20), nullable=False, default="physician")
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    credentials: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    primary_specialty: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    license_state: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    license_numbers: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    dea_number_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    supervising_practitioner_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("practitioner.person_id"), nullable=True,
    )
    verification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="verified",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PGPractitionerMembership(Base, TimestampMixin, SoftDeleteMixin):
    """N:M between PracticeOrg and Practitioner with time bounds (append-only)."""
    __tablename__ = "pg_practitioner_membership"
    __table_args__ = (
        UniqueConstraint("practitioner_id", "practice_org_id", "start_date",
                         name="uq_pgpm_unique"),
        CheckConstraint("end_date IS NULL OR end_date >= start_date",
                        name="chk_pgpm_dates"),
        Index("ix_pgpm_pg_active", "practice_org_id"),
        Index("ix_pgpm_practitioner_active", "practitioner_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False, index=True,
    )
    practice_org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("practice_org.practice_org_id"), nullable=False,
    )
    practitioner_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("practitioner.person_id"), nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="employed")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
