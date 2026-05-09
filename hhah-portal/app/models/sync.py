"""Bulk upload + sync."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, SoftDeleteMixin, gen_uuid


class BulkUpload(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "bulk_upload"
    __table_args__ = (
        Index("ix_bulk_org_time", "org_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False, index=True,
    )
    uploaded_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("app_user.id"), nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_committed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_errored: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    workflow_run_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)


class BulkUploadFile(Base, TimestampMixin):
    __tablename__ = "bulk_upload_file"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    bulk_upload_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bulk_upload.id"), nullable=False, index=True,
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(40), nullable=False)
    detected_format: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="accepted")
    rows_committed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_errored: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class UploadRowError(Base, TimestampMixin):
    __tablename__ = "upload_row_error"
    __table_args__ = (
        Index("ix_upload_err_file", "bulk_upload_file_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    bulk_upload_file_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bulk_upload_file.id"), nullable=False,
    )
    row_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    field: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    error: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_row: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
