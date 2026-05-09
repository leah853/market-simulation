"""Admission + Episode — single-table-with-status pattern.

DB invariants enforced via partial unique indexes:
  - 1 current admission per patient
  - 1 current episode per admission
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, SoftDeleteMixin, gen_uuid


class Admission(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "admission"
    __table_args__ = (
        # Postgres partial unique index — only one current admission per patient
        Index(
            "uq_admission_one_current_per_patient",
            "patient_id",
            unique=True,
            postgresql_where=text("status = 'current'"),
        ),
        Index("ix_admission_patient_status", "patient_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False, index=True,
    )
    patient_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("patient.patient_id"), nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="current")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    admission_source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    referring_practitioner_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("practitioner.person_id"), nullable=True,
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    discharge_summary_document_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True,
    )


class Episode(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "episode"
    __table_args__ = (
        Index(
            "uq_episode_one_current_per_admission",
            "admission_id",
            unique=True,
            postgresql_where=text("status = 'current'"),
        ),
        Index("ix_episode_admission_status", "admission_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False, index=True,
    )
    admission_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("admission.id"), nullable=False,
    )
    patient_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("patient.patient_id"), nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="current")
    episode_number: Mapped[int] = mapped_column(nullable=False, default=1)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    certification_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="provisional",
    )
    billability_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="not_ready",
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    attending_practitioner_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("practitioner.person_id"), nullable=True,
    )
