"""Communication threads + messages."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, SoftDeleteMixin, gen_uuid


class CommunicationThread(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "communication_thread"
    __table_args__ = (
        Index("ix_thread_org_last_msg", "org_id", "last_message_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False, index=True,
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    counterparty: Mapped[str] = mapped_column(
        String(20), nullable=False, default="us",
        comment="V1: always 'us'. Future: can include other_hhah, practitioner.",
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")

    # Linked entities (multi-link supported per V1 bulk-action requirement)
    linked_patient_ids: Mapped[Optional[list]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)), nullable=True,
    )
    linked_document_ids: Mapped[Optional[list]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)), nullable=True,
    )

    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_message_preview: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class CommunicationMessage(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "communication_message"
    __table_args__ = (
        Index("ix_message_thread_sent", "thread_id", "sent_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False, index=True,
    )
    thread_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("communication_thread.id"), nullable=False,
    )
    sender_user_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("app_user.id"), nullable=True,
        comment="Null when sender is 'Us' (Eonexea ops).",
    )
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    attachments_meta: Mapped[Optional[list]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)), nullable=True,
    )
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
