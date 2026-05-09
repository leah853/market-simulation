"""Patient — clinical record with PG ↔ Practitioner attribution."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, SoftDeleteMixin, gen_uuid


class Patient(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "patient"
    __table_args__ = (
        UniqueConstraint("org_id", "mrn", name="uq_patient_org_mrn"),
        Index("ix_patient_primary_practitioner", "primary_practitioner_id"),
        Index("ix_patient_primary_pg", "primary_practice_org_id"),
    )

    patient_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False, index=True,
    )

    # Identity (PHI — should be column-encrypted in production)
    mrn: Mapped[str] = mapped_column(String(64), nullable=False)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    medicare_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    flags_meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Attribution (denormalized from latest signed 485)
    primary_practitioner_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("practitioner.person_id"), nullable=True,
    )
    primary_practice_org_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("practice_org.practice_org_id"), nullable=True,
    )
    attribution_source_485_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True,
    )
    attribution_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    @property
    def display_name(self) -> str:
        return f"{self.last_name}, {self.first_name}"
