"""Documents — care coordination artifacts (485, F2F, orders, etc.) + comments."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, SoftDeleteMixin, gen_uuid


class Document(Base, TimestampMixin, SoftDeleteMixin):
    """
    Unified document table. The DDL diff kept docs as per-type tables in the
    Eonexea live schema; for the HHAH portal V1 we use this single, generic
    table. Workflow on the orchestrator side is responsible for syncing.
    """
    __tablename__ = "document"
    __table_args__ = (
        Index("ix_document_org_type", "org_id", "document_type"),
        Index("ix_document_patient", "patient_id"),
        Index("ix_document_episode", "episode_id"),
        Index("ix_document_owner_practitioner", "owner_practitioner_id"),
        Index(
            "ix_document_signature_required",
            "org_id", "signature_required",
            postgresql_where=None,  # always indexed
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False, index=True,
    )

    # Linkage
    patient_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("patient.patient_id"), nullable=True,
    )
    episode_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("episode.id"), nullable=True,
    )
    owner_practitioner_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("practitioner.person_id"), nullable=True,
    )

    # Type + content
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(80), nullable=False, default="application/pdf")
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Dates
    authored_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    document_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True,
        comment="Date written on the document (e.g., the order date) — used as the timeline anchor.",
    )

    # Lifecycle
    signature_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lifecycle_state: Mapped[str] = mapped_column(
        String(40), nullable=False, default="uploaded",
        comment="uploaded | validating | validated | pending_signature | signed | expired | voided",
    )
    is_urgent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Extracted metadata (from OCR/ML pipeline)
    extraction_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)
    extracted_fields: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


class Comment(Base, TimestampMixin, SoftDeleteMixin):
    """Polymorphic comment — attaches to documents or flags."""
    __tablename__ = "comment"
    __table_args__ = (
        Index("ix_comment_subject", "subject_type", "subject_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False, index=True,
    )
    subject_type: Mapped[str] = mapped_column(String(40), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    author_user_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("app_user.id"), nullable=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
