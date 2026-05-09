"""Organization (tenant root) + BAA records."""
from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, SoftDeleteMixin, gen_uuid


class Organization(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "organization"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    tenancy_mode: Mapped[str] = mapped_column(
        String(40), nullable=False, default="single_tenant_multi_hhah"
    )
    branding_config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    settings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


class BAARecord(Base, TimestampMixin, SoftDeleteMixin):
    """BAA on file for an Organization."""
    __tablename__ = "baa_record"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False, index=True,
    )
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    signed_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("app_user.id"), nullable=True,
    )
    signed_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    document_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    storage_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
