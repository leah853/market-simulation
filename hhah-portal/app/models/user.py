"""User, Session, Invite — auth core."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, SoftDeleteMixin, gen_uuid, utcnow


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "app_user"
    __table_args__ = (Index("ix_user_email_lower", "email"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False, index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(String(40), nullable=False, default="hhah_user")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # MFA
    mfa_totp_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mfa_totp_enrolled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mfa_webauthn_enrolled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mfa_recovery_codes_hashed: Mapped[Optional[list[str]]] = mapped_column(Text, nullable=True)

    # Onboarding
    accepted_terms_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Session(Base, TimestampMixin):
    """Active auth session — tracks idle + absolute timeouts and concurrent caps."""
    __tablename__ = "app_session"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("app_user.id"), nullable=False, index=True,
    )
    device_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    mfa_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Invite(Base, TimestampMixin):
    """Single-use, 24-hour invite link issued by Eonexea ops."""
    __tablename__ = "invite"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False, index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(40), nullable=False, default="hhah_user")
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("app_user.id"), nullable=True,
    )

    @staticmethod
    def default_expiry() -> datetime:
        return datetime.now(timezone.utc) + timedelta(hours=24)
